"""Read-only canteen ledger facts; catalogue orders are a separate historical source."""
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.application.services.financial_summary import currency, money
from app.core.config import get_settings
from app.core.dates import school_day_bounds, school_today
from app.core.exceptions import AppException, ForbiddenException, ValidationException
from app.core.student_access import accessible_student_ids, parent_student_ids
from app.domain.entities.canteen import CanteenOrder, CanteenWalletTransaction
from app.infrastructure.models.models import Branch, Student


def _period(days, start_date, end_date_exclusive, today):
    if (start_date is None) != (end_date_exclusive is None):
        raise ValidationException("Dönemin başlangıcı ve bitişi birlikte belirtilmeli")
    if start_date is None:
        if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 365:
            raise ValidationException("Gün sayısı 1 ile 365 arasında olmalı")
        return today - timedelta(days=days - 1), today + timedelta(days=1)
    if type(start_date) is not date or type(end_date_exclusive) is not date:
        raise ValidationException("Dönem sınırları takvim tarihi olmalı")
    if not 1 <= (end_date_exclusive - start_date).days <= 365:
        raise ValidationException("Dönem 1 ile 365 gün arasında olmalı")
    return start_date, end_date_exclusive


def _total(values):
    values = list(values)
    parsed = [money(value) for value in values]
    invalid = sum(value is None for value in parsed)
    total = sum(parsed) if values and not invalid else None
    return total, invalid


def _parent_mode(tenant):
    return tenant.parent_portal or tenant.role_slugs == {"parent"}


async def get_recorded_canteen_summary(
    db, tenant, *, days=30, start_date=None, end_date_exclusive=None,
    student_id=None, purpose="analysis",
):
    """Keep native analysis/chatbot permissions and explicitly scope every source.

    No wallet is created or adjusted. The ledger has no historical branch snapshot;
    its scope therefore follows the student's current school/branch. Order totals
    never augment ledger totals: there is no reliable order-to-ledger link.
    """
    if purpose not in {"analysis", "chatbot"}:
        raise ValidationException("Geçersiz kantin özeti amacı")
    guardian = purpose == "chatbot" and _parent_mode(tenant) and tenant.has_permission("parent.view_finances")
    permitted = guardian if purpose == "chatbot" and _parent_mode(tenant) else tenant.has_permission("canteen.read")
    if not tenant.organization_id or not permitted:
        raise ForbiddenException("Kantin kayıtlarını görüntüleme yetkiniz yok")
    now = datetime.now(UTC)
    today = school_today(now)
    start, end = _period(days, start_date, end_date_exclusive, today)
    try:
        return await _read_summary(db, tenant, start, end, now, today, student_id)
    except SQLAlchemyError:
        raise AppException("Kantin kayıtları yüklenemedi; daha sonra tekrar deneyin", status_code=503) from None


async def _read_summary(db, tenant, start, end, now, today, student_id):
    students = select(Student.id).join(Branch, Branch.id == Student.branch_id).where(
        Student.organization_id == tenant.organization_id, Student.deleted_at.is_(None),
        Branch.organization_id == tenant.organization_id, Branch.deleted_at.is_(None),
    )
    if tenant.branch_ids:
        students = students.where(Student.branch_id.in_(tenant.branch_ids))
    ids = await parent_student_ids(db, tenant.user_id, tenant.organization_id) if _parent_mode(tenant) else await accessible_student_ids(db, tenant)
    if ids is not None:
        students = students.where(Student.id.in_(ids))
    if student_id is not None:
        try:
            selected = UUID(str(student_id))
        except (ValueError, TypeError, AttributeError):
            raise ValidationException("Öğrenci kimliği geçersiz") from None
        students = students.where(Student.id == selected)
        if (await db.execute(students)).scalar_one_or_none() is None:
            raise ForbiddenException("Bu öğrenciye erişim yetkiniz yok")
    first_instant = school_day_bounds(start)[0]
    end_instant = school_day_bounds(end - timedelta(days=1))[1]
    transactions = (await db.execute(select(
        CanteenWalletTransaction.amount, CanteenWalletTransaction.transaction_type,
    ).where(
        CanteenWalletTransaction.student_id.in_(students),
        CanteenWalletTransaction.status == "COMPLETED",
        CanteenWalletTransaction.transaction_type.in_(("DEBIT", "SALE", "CREDIT")),
        CanteenWalletTransaction.created_at >= first_instant,
        CanteenWalletTransaction.created_at < end_instant,
        CanteenWalletTransaction.created_at <= now,
    ))).all()
    orders_query = select(CanteenOrder.total_price, CanteenOrder.quantity).where(
        CanteenOrder.student_id.in_(students), CanteenOrder.status == "COMPLETED",
        CanteenOrder.order_date >= start, CanteenOrder.order_date < end,
        CanteenOrder.order_date <= today, CanteenOrder.created_at <= now,
        or_(CanteenOrder.branch_id.is_(None), CanteenOrder.branch_id.in_(select(Branch.id).where(
            Branch.organization_id == tenant.organization_id, Branch.deleted_at.is_(None),
        ))),
    )
    if tenant.branch_ids:
        orders_query = orders_query.where(or_(CanteenOrder.branch_id.is_(None), CanteenOrder.branch_id.in_(tenant.branch_ids)))
    orders = (await db.execute(orders_query)).all()
    sales = [row.amount for row in transactions if row.transaction_type in {"DEBIT", "SALE"}]
    credits = [row.amount for row in transactions if row.transaction_type == "CREDIT"]
    total, bad_sales = _total(sales)
    credit_total, bad_credits = _total(credits)
    wallet_total, _ = _total(row.amount for row in transactions if row.transaction_type == "DEBIT")
    direct_total, _ = _total(row.amount for row in transactions if row.transaction_type == "SALE")
    order_total, bad_orders = _total(row.total_price for row in orders)
    quantities = [row.quantity for row in orders]
    bad_quantity = sum(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in quantities)
    quantity = sum(quantities) if quantities and not bad_quantity else None
    # Future calendar days are not observations, even if requested by a chatbot period.
    observed_days = max(0, (min(end, today + timedelta(days=1)) - start).days)
    average = total / observed_days if total is not None and observed_days else None
    return {
        "analysis_type": "recorded_canteen", "data_source": "canteen_wallet_transactions",
        "period_start": start.isoformat(), "period_end_exclusive": end.isoformat(),
        "timezone": get_settings().BUSINESS_TIMEZONE, "as_of": now.isoformat(),
        "observed_day_count": observed_days,
        "sale_record_count": len(sales), "sales_amount": currency(total),
        "wallet_debit_amount": currency(wallet_total), "direct_sale_amount": currency(direct_total),
        "topup_record_count": len(credits), "topup_amount": currency(credit_total),
        "daily_average": currency(average), "invalid_sale_amount_count": bad_sales,
        "invalid_topup_amount_count": bad_credits,
        "requires_review": bool(bad_sales or bad_credits or bad_orders or bad_quantity),
        "history_status": "requires_review" if bad_sales else "recorded" if sales else "no_history",
        "catalog_orders": {
            "data_source": "canteen_orders", "record_count": len(orders),
            "amount": currency(order_total), "quantity": quantity,
            "invalid_amount_count": bad_orders, "invalid_quantity_count": bad_quantity,
            "included_in_sales_total": False,
        },
        "total_sales": currency(total), "order_count": len(orders),
        "inventory_status": "unknown", "trend": "recorded" if sales and not bad_sales else "insufficient_data",
        "recommendations": [],
    }
