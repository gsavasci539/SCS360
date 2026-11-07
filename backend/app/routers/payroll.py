"""
Personel Bordro & Puantaj Module API
Handles staff timesheets, additional course hours, and payroll records
"""
from __future__ import annotations
from datetime import UTC, datetime, date
from typing import Optional, List
from uuid import UUID
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AwareDatetime, BaseModel, Field, field_validator, model_validator
from sqlalchemy import select, and_, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response
from app.core.permissions import PermissionChecker
from app.core.tenant import TenantContext
from app.domain.entities import User
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.tenant_guard import scope_filters, staff_scope
from app.application.services.consent_service import utc_iso

router = APIRouter(prefix="/api/payroll", tags=["Payroll"])


async def lock_staff(db, tenant, staff_id):
    table = User.__table__
    allowed = select(table.c.id).where(table.c.id == staff_id)
    if not tenant.is_super_admin:
        branches, _, _, users = scope_filters(tenant, db.info.get("accessible_student_ids"))
        allowed = staff_scope(tenant, branches, users).where(table.c.id == staff_id)
    identifier = (await db.execute(allowed)).scalar_one_or_none()
    if identifier is None:
        raise NotFoundException("Bu kapsamda personel bulunamadı")
    # Serialize first writes as well as edits/approvals without altering users.
    await db.execute(update(table).where(table.c.id == identifier).values(updated_at=table.c.updated_at))


# ==================== Schemas ====================

class StaffTimesheetCreate(BaseModel):
    staff_id: UUID
    timesheet_date: date = Field(..., description="Timesheet date")
    check_in_time: Optional[AwareDatetime] = None
    check_out_time: Optional[AwareDatetime] = None
    work_hours: Decimal = Field(default=0, ge=0, le=24, max_digits=4, decimal_places=2)
    status: str = Field(default="PRESENT", min_length=1, max_length=20, description="PRESENT, ABSENT, LEAVE, SICK")
    notes: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("check_in_time", "check_out_time")
    @classmethod
    def utc_timestamps(cls, value):
        return value.astimezone(UTC) if value else None

    @model_validator(mode="after")
    def checkout(self):
        if self.check_in_time and self.check_out_time:
            try:
                valid = self.check_out_time >= self.check_in_time
            except TypeError as error:
                raise ValueError("Giriş ve çıkış saatleri aynı saat dilimi biçiminde olmalıdır") from error
            if not valid:
                raise ValueError("Çıkış saati girişten önce olamaz")
        return self

class AdditionalCourseHoursCreate(BaseModel):
    staff_id: UUID
    period: str = Field(..., min_length=1, max_length=20, description="MONTHLY, QUARTERLY")
    year: int = Field(..., ge=2020, le=2100)
    month: Optional[int] = Field(None, ge=1, le=12)
    total_hours: Decimal = Field(default=0, ge=0, max_digits=5, decimal_places=2)
    hourly_rate: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    notes: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def period_month(self):
        self.period = self.period.strip().upper()
        if self.period not in {"MONTHLY", "QUARTERLY"} or self.month is None:
            raise ValueError("Aylık veya üç aylık dönem ve dönem ayı seçilmelidir")
        return self

class PayrollRecordCreate(BaseModel):
    staff_id: UUID
    period: str = Field(..., min_length=1, max_length=20, description="MONTHLY, QUARTERLY")
    year: int = Field(..., ge=2020, le=2100)
    month: Optional[int] = Field(None, ge=1, le=12)
    base_salary: Decimal = Field(default=0, ge=0, max_digits=15, decimal_places=2)
    additional_course_payment: Decimal = Field(default=0, ge=0, max_digits=15, decimal_places=2)
    bonus: Decimal = Field(default=0, ge=0, max_digits=15, decimal_places=2)
    advance_payment: Decimal = Field(default=0, ge=0, max_digits=15, decimal_places=2)
    deductions: Decimal = Field(default=0, ge=0, max_digits=15, decimal_places=2)
    payment_date: Optional[date] = None
    payment_method: Optional[str] = Field(default=None, max_length=50)
    bank_account: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def period_month(self):
        self.period = self.period.strip().upper()
        if self.period not in {"MONTHLY", "QUARTERLY"} or self.month is None:
            raise ValueError("Aylık veya üç aylık dönem ve dönem ayı seçilmelidir")
        return self


@router.get("/options")
async def payroll_options(search: str = Query("", max_length=100), staff_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db, scope="function"),
                           tenant: TenantContext = Depends(PermissionChecker("payroll.read", "payroll.write"))):
    from app.application.services.payroll_service import options
    return success_response(await options(db, tenant, search, staff_id))


@router.get("/summary")
async def payroll_summary(year: Optional[int] = Query(None, ge=2020, le=2100), month: Optional[int] = Query(None, ge=1, le=12),
                           period: Optional[str] = None, staff_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db, scope="function"),
                           tenant: TenantContext = Depends(PermissionChecker("payroll.read"))):
    from app.application.services.payroll_service import summary
    return success_response(await summary(db, year, month, period.upper() if period else None, staff_id))


# ==================== Staff Timesheets Endpoints ====================

@router.get("/timesheets")
async def get_staff_timesheets(
    staff_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("payroll.read"))
):
    """Get staff timesheets with filtering"""
    from app.domain.entities.payroll import StaffTimesheet
    
    query = select(StaffTimesheet)
    
    conditions = []
    if staff_id:
        conditions.append(StaffTimesheet.staff_id == staff_id)
    if start_date:
        conditions.append(StaffTimesheet.date >= start_date)
    if end_date:
        conditions.append(StaffTimesheet.date <= end_date)
    if status:
        conditions.append(StaffTimesheet.status == status.upper())
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(StaffTimesheet.date.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    timesheets = result.scalars().all()
    
    enriched_timesheets = []
    for ts in timesheets:
        # Get staff name
        staff_name = None
        if ts.staff_id:
            user_result = await db.execute(
                select(User).where(User.id == ts.staff_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                staff_name = f"{user.first_name} {user.last_name}"
        
        enriched_timesheets.append({
            "id": str(ts.id),
            "staff_id": str(ts.staff_id),
            "staff_name": staff_name,
            "date": ts.date.isoformat(),
            "check_in_time": utc_iso(ts.check_in_time),
            "check_out_time": utc_iso(ts.check_out_time),
            "work_hours": float(ts.work_hours) if ts.work_hours else 0,
            "status": ts.status,
            "notes": ts.notes,
            "created_at": utc_iso(ts.created_at)
        })
    
    return success_response(enriched_timesheets)


@router.post("/timesheets")
async def create_staff_timesheet(
    timesheet: StaffTimesheetCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("payroll.write"))
):
    """Create or update a staff timesheet"""
    from app.domain.entities.payroll import StaffTimesheet
    await lock_staff(db, tenant, timesheet.staff_id)
    
    # Check if timesheet already exists for this staff and date
    existing_result = await db.execute(
        select(StaffTimesheet).where(
            and_(
                StaffTimesheet.staff_id == timesheet.staff_id,
                StaffTimesheet.date == timesheet.timesheet_date
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        existing.check_in_time = timesheet.check_in_time
        existing.check_out_time = timesheet.check_out_time
        existing.work_hours = timesheet.work_hours
        existing.status = timesheet.status.upper()
        existing.notes = timesheet.notes
    else:
        new_timesheet = StaffTimesheet(
            staff_id=timesheet.staff_id,
            date=timesheet.timesheet_date,
            check_in_time=timesheet.check_in_time,
            check_out_time=timesheet.check_out_time,
            work_hours=timesheet.work_hours,
            status=timesheet.status.upper(),
            notes=timesheet.notes
        )
        db.add(new_timesheet)
    
    await db.commit()
    
    return success_response({
        "message": "Timesheet saved successfully",
        "staff_id": str(timesheet.staff_id),
        "date": timesheet.timesheet_date.isoformat(),
        "status": timesheet.status.upper()
    })


@router.get("/timesheets/monthly-summary")
async def get_monthly_timesheet_summary(
    year: int = Query(..., description="Year"),
    month: int = Query(..., ge=1, le=12, description="Month"),
    staff_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("payroll.read"))
):
    """Get monthly timesheet summary"""
    from app.domain.entities.payroll import StaffTimesheet
    
    query = select(StaffTimesheet).where(
        and_(
            StaffTimesheet.date >= date(year, month, 1),
            StaffTimesheet.date <= date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)
        )
    )
    
    if staff_id:
        query = query.where(StaffTimesheet.staff_id == staff_id)
    
    result = await db.execute(query)
    timesheets = result.scalars().all()
    
    # Calculate summary
    total_days = len(timesheets)
    present_days = sum(1 for ts in timesheets if ts.status == "PRESENT")
    absent_days = sum(1 for ts in timesheets if ts.status == "ABSENT")
    leave_days = sum(1 for ts in timesheets if ts.status == "LEAVE")
    sick_days = sum(1 for ts in timesheets if ts.status == "SICK")
    total_work_hours = sum(ts.work_hours or 0 for ts in timesheets)
    
    return success_response({
        "year": year,
        "month": month,
        "total_days": total_days,
        "present_days": present_days,
        "absent_days": absent_days,
        "leave_days": leave_days,
        "sick_days": sick_days,
        "total_work_hours": float(total_work_hours),
        "attendance_rate": (present_days / total_days * 100) if total_days > 0 else 0
    })


# ==================== Additional Course Hours Endpoints ====================

@router.get("/additional-hours")
async def get_additional_course_hours(
    staff_id: Optional[UUID] = Query(None),
    period: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("payroll.read"))
):
    """Get additional course hours with filtering"""
    from app.domain.entities.payroll import AdditionalCourseHours
    
    query = select(AdditionalCourseHours)
    
    conditions = []
    if staff_id:
        conditions.append(AdditionalCourseHours.staff_id == staff_id)
    if period:
        conditions.append(AdditionalCourseHours.period == period.upper())
    if year:
        conditions.append(AdditionalCourseHours.year == year)
    if month:
        conditions.append(AdditionalCourseHours.month == month)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(AdditionalCourseHours.year.desc(), AdditionalCourseHours.month.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    hours = result.scalars().all()
    
    enriched_hours = []
    for hour in hours:
        # Get staff name
        staff_name = None
        if hour.staff_id:
            user_result = await db.execute(
                select(User).where(User.id == hour.staff_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                staff_name = f"{user.first_name} {user.last_name}"
        
        # Get approved by name
        approved_by_name = None
        if hour.approved_by:
            user_result = await db.execute(
                select(User).where(User.id == hour.approved_by)
            )
            user = user_result.scalar_one_or_none()
            if user:
                approved_by_name = f"{user.first_name} {user.last_name}"
        
        enriched_hours.append({
            "id": str(hour.id),
            "staff_id": str(hour.staff_id),
            "staff_name": staff_name,
            "period": hour.period,
            "year": hour.year,
            "month": hour.month,
            "total_hours": float(hour.total_hours),
            "hourly_rate": float(hour.hourly_rate) if hour.hourly_rate else None,
            "total_amount": float(hour.total_amount),
            "approved_by": str(hour.approved_by) if hour.approved_by else None,
            "approved_by_name": approved_by_name,
            "approved_at": utc_iso(hour.approved_at),
            "notes": hour.notes,
            "created_at": utc_iso(hour.created_at)
        })
    
    return success_response(enriched_hours)


@router.post("/additional-hours")
async def create_additional_course_hours(
    hours: AdditionalCourseHoursCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("payroll.write"))
):
    """Create or update additional course hours"""
    from app.domain.entities.payroll import AdditionalCourseHours
    await lock_staff(db, tenant, hours.staff_id)
    
    # Calculate total amount
    total_amount = ((hours.total_hours * hours.hourly_rate) if hours.hourly_rate else Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    # Check if record already exists
    existing_result = await db.execute(
        select(AdditionalCourseHours).where(
            and_(
                AdditionalCourseHours.staff_id == hours.staff_id,
                AdditionalCourseHours.period == hours.period.upper(),
                AdditionalCourseHours.year == hours.year,
                AdditionalCourseHours.month == hours.month
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        if existing.approved_at is not None:
            raise ConflictException("Onaylanmış ek ders kaydı değiştirilemez")
        existing.total_hours = hours.total_hours
        existing.hourly_rate = hours.hourly_rate
        existing.total_amount = total_amount
        existing.notes = hours.notes
    else:
        new_hours = AdditionalCourseHours(
            staff_id=hours.staff_id,
            period=hours.period.upper(),
            year=hours.year,
            month=hours.month,
            total_hours=hours.total_hours,
            hourly_rate=hours.hourly_rate,
            total_amount=total_amount,
            notes=hours.notes
        )
        db.add(new_hours)
    
    await db.commit()
    
    return success_response({
        "message": "Additional course hours saved successfully",
        "staff_id": str(hours.staff_id),
        "period": hours.period.upper(),
        "year": hours.year,
        "month": hours.month,
        "total_amount": float(total_amount)
    })


# ==================== Payroll Records Endpoints ====================

@router.get("/records")
async def get_payroll_records(
    staff_id: Optional[UUID] = Query(None),
    period: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("payroll.read"))
):
    """Get payroll records with filtering"""
    from app.domain.entities.payroll import PayrollRecord
    
    query = select(PayrollRecord)
    
    conditions = []
    if staff_id:
        conditions.append(PayrollRecord.staff_id == staff_id)
    if period:
        conditions.append(PayrollRecord.period == period.upper())
    if year:
        conditions.append(PayrollRecord.year == year)
    if month:
        conditions.append(PayrollRecord.month == month)
    if status:
        conditions.append(PayrollRecord.status == status.upper())
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(PayrollRecord.year.desc(), PayrollRecord.month.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    enriched_records = []
    for record in records:
        # Get staff name
        staff_name = None
        if record.staff_id:
            user_result = await db.execute(
                select(User).where(User.id == record.staff_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                staff_name = f"{user.first_name} {user.last_name}"
        
        # Get approved by name
        approved_by_name = None
        if record.approved_by:
            user_result = await db.execute(
                select(User).where(User.id == record.approved_by)
            )
            user = user_result.scalar_one_or_none()
            if user:
                approved_by_name = f"{user.first_name} {user.last_name}"
        
        enriched_records.append({
            "id": str(record.id),
            "staff_id": str(record.staff_id),
            "staff_name": staff_name,
            "period": record.period,
            "year": record.year,
            "month": record.month,
            "base_salary": float(record.base_salary),
            "additional_course_payment": float(record.additional_course_payment),
            "bonus": float(record.bonus),
            "advance_payment": float(record.advance_payment),
            "deductions": float(record.deductions),
            "net_salary": float(record.net_salary),
            "payment_date": record.payment_date.isoformat() if record.payment_date else None,
            "payment_method": record.payment_method,
            "bank_account": record.bank_account,
            "status": record.status,
            "approved_by": str(record.approved_by) if record.approved_by else None,
            "approved_by_name": approved_by_name,
            "approved_at": utc_iso(record.approved_at),
            "notes": record.notes,
            "created_at": utc_iso(record.created_at)
        })
    
    return success_response(enriched_records)


@router.post("/records")
async def create_payroll_record(
    record: PayrollRecordCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("payroll.write"))
):
    """Create or update a payroll record"""
    from app.domain.entities.payroll import PayrollRecord
    await lock_staff(db, tenant, record.staff_id)
    
    # Calculate net salary
    net_salary = (
        record.base_salary +
        record.additional_course_payment +
        record.bonus -
        record.advance_payment -
        record.deductions
    )
    if not net_salary.is_finite() or abs(net_salary) > Decimal("9999999999999.99"):
        raise ValidationException("Net tutar kayıt sınırını aşıyor")
    
    # Check if record already exists
    existing_result = await db.execute(
        select(PayrollRecord).where(
            and_(
                PayrollRecord.staff_id == record.staff_id,
                PayrollRecord.period == record.period.upper(),
                PayrollRecord.year == record.year,
                PayrollRecord.month == record.month
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        if existing.status != "DRAFT":
            raise ConflictException("Onaylanmış bordro değiştirilemez")
        existing.base_salary = record.base_salary
        existing.additional_course_payment = record.additional_course_payment
        existing.bonus = record.bonus
        existing.advance_payment = record.advance_payment
        existing.deductions = record.deductions
        existing.net_salary = net_salary
        existing.payment_date = record.payment_date
        existing.payment_method = record.payment_method
        existing.bank_account = record.bank_account
        existing.notes = record.notes
    else:
        new_record = PayrollRecord(
            staff_id=record.staff_id,
            period=record.period.upper(),
            year=record.year,
            month=record.month,
            base_salary=record.base_salary,
            additional_course_payment=record.additional_course_payment,
            bonus=record.bonus,
            advance_payment=record.advance_payment,
            deductions=record.deductions,
            net_salary=net_salary,
            payment_date=record.payment_date,
            payment_method=record.payment_method,
            bank_account=record.bank_account,
            status="DRAFT",
            notes=record.notes
        )
        db.add(new_record)
    
    await db.commit()
    
    return success_response({
        "message": "Payroll record saved successfully",
        "staff_id": str(record.staff_id),
        "period": record.period.upper(),
        "year": record.year,
        "month": record.month,
        "net_salary": float(net_salary)
    })


@router.post("/records/{record_id}/approve")
async def approve_payroll_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("payroll.write"))
):
    """Approve a payroll record"""
    from app.domain.entities.payroll import PayrollRecord
    
    result = await db.execute(
        select(PayrollRecord).where(PayrollRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Payroll record not found")
    await lock_staff(db, tenant, record.staff_id)
    record = (await db.execute(select(PayrollRecord).where(PayrollRecord.id == record_id)
        .execution_options(populate_existing=True))).scalar_one()
    if record.status not in {"DRAFT", "APPROVED"}:
        raise ConflictException("Bu durumdaki bordro onaylanamaz")
    if record.status == "DRAFT":
        record.status = "APPROVED"
        record.approved_by = tenant.user_id
        record.approved_at = datetime.now(UTC)
    
    await db.commit()
    
    return success_response({
        "id": str(record.id),
        "status": "APPROVED",
        "approved_by": str(record.approved_by) if record.approved_by else None,
        "approved_at": utc_iso(record.approved_at)
    })
