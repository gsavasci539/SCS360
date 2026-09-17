"""
Personel Bordro & Puantaj Module API
Handles staff timesheets, additional course hours, and payroll records
"""
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response
from app.core.security import PermissionChecker, TenantContext
from app.domain.entities import User

router = APIRouter(prefix="/api/payroll", tags=["Payroll"])


# ==================== Schemas ====================

class StaffTimesheetCreate(BaseModel):
    staff_id: UUID
    timesheet_date: date = Field(..., description="Timesheet date")
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    work_hours: Optional[Decimal] = Field(None, ge=0)
    status: str = Field(default="PRESENT", description="PRESENT, ABSENT, LEAVE, SICK")
    notes: Optional[str] = None

class AdditionalCourseHoursCreate(BaseModel):
    staff_id: UUID
    period: str = Field(..., description="MONTHLY, QUARTERLY")
    year: int = Field(..., ge=2020, le=2100)
    month: Optional[int] = Field(None, ge=1, le=12)
    total_hours: Decimal = Field(default=0, ge=0)
    hourly_rate: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None

class PayrollRecordCreate(BaseModel):
    staff_id: UUID
    period: str = Field(..., description="MONTHLY, QUARTERLY")
    year: int = Field(..., ge=2020, le=2100)
    month: Optional[int] = Field(None, ge=1, le=12)
    base_salary: Decimal = Field(default=0, ge=0)
    additional_course_payment: Decimal = Field(default=0, ge=0)
    bonus: Decimal = Field(default=0, ge=0)
    advance_payment: Decimal = Field(default=0, ge=0)
    deductions: Decimal = Field(default=0, ge=0)
    payment_date: Optional[date] = None
    payment_method: Optional[str] = None
    bank_account: Optional[str] = None
    notes: Optional[str] = None


# ==================== Staff Timesheets Endpoints ====================

@router.get("/timesheets")
async def get_staff_timesheets(
    staff_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
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
            "check_in_time": ts.check_in_time.isoformat() if ts.check_in_time else None,
            "check_out_time": ts.check_out_time.isoformat() if ts.check_out_time else None,
            "work_hours": float(ts.work_hours) if ts.work_hours else 0,
            "status": ts.status,
            "notes": ts.notes,
            "created_at": ts.created_at.isoformat()
        })
    
    return success_response(enriched_timesheets)


@router.post("/timesheets")
async def create_staff_timesheet(
    timesheet: StaffTimesheetCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("payroll.write"))
):
    """Create or update a staff timesheet"""
    from app.domain.entities.payroll import StaffTimesheet
    
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
            "approved_at": hour.approved_at.isoformat() if hour.approved_at else None,
            "notes": hour.notes,
            "created_at": hour.created_at.isoformat()
        })
    
    return success_response(enriched_hours)


@router.post("/additional-hours")
async def create_additional_course_hours(
    hours: AdditionalCourseHoursCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("payroll.write"))
):
    """Create or update additional course hours"""
    from app.domain.entities.payroll import AdditionalCourseHours
    
    # Calculate total amount
    total_amount = (hours.total_hours * hours.hourly_rate) if hours.hourly_rate else 0
    
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
    db: AsyncSession = Depends(get_db),
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
            "approved_at": record.approved_at.isoformat() if record.approved_at else None,
            "notes": record.notes,
            "created_at": record.created_at.isoformat()
        })
    
    return success_response(enriched_records)


@router.post("/records")
async def create_payroll_record(
    record: PayrollRecordCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("payroll.write"))
):
    """Create or update a payroll record"""
    from app.domain.entities.payroll import PayrollRecord
    
    # Calculate net salary
    net_salary = (
        record.base_salary +
        record.additional_course_payment +
        record.bonus -
        record.advance_payment -
        record.deductions
    )
    
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
    db: AsyncSession = Depends(get_db),
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
    
    record.status = "APPROVED"
    record.approved_by = None  # Will be set from current user context
    record.approved_at = datetime.utcnow()
    
    await db.commit()
    
    return success_response({
        "id": str(record.id),
        "status": "APPROVED",
        "approved_at": record.approved_at.isoformat()
    })
