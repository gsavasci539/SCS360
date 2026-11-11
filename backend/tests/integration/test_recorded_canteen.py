"""Service acceptance: recorded ledger, isolated catalogue history, no writes."""
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from time import perf_counter

import pytest
from sqlalchemy import event, func, insert, select, text
from sqlalchemy.exc import SQLAlchemyError
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.application.services.recorded_canteen import get_recorded_canteen_summary
from app.core.dates import school_day_bounds, school_today
from app.core.exceptions import AppException, ForbiddenException, ValidationException
from app.core.tenant import TenantContext
from app.domain.entities.canteen import CanteenOrder, CanteenProduct, CanteenWalletTransaction
from app.infrastructure.models.models import Branch, Student, StudentWallet


@pytest.fixture
async def canteen_db(portal_db):  # noqa: F811 - imported pytest fixture injection
    sessions, data = portal_db
    async with sessions() as db:
        product = CanteenProduct(branch_id=data["branch"].id, name="Recorded food", price=10)
        db.add(product)
        await db.commit()
    return sessions, {**data, "product": product}


def tenant(data, **overrides):
    values = dict(user_id=data["teacher"].id, organization_id=data["org"].id,
        permissions={"canteen.read"}, role_slugs={"owner"})
    return TenantContext(**(values | overrides))


def movement(child, amount, kind="DEBIT", **values):
    return CanteenWalletTransaction(**(dict(student_id=child.id, amount=Decimal(amount),
        transaction_type=kind, status="COMPLETED", created_at=datetime.now(UTC) - timedelta(seconds=1)) | values))


def order(data, amount, *, child=None, **values):
    child = child or data["children"][0]
    return CanteenOrder(**(dict(student_id=child.id, branch_id=child.branch_id, product_id=data["product"].id,
        quantity=1, unit_price=Decimal(amount), total_price=Decimal(amount), status="COMPLETED",
        order_date=school_today(), order_time=datetime.now(UTC).time(), created_at=datetime.now(UTC) - timedelta(seconds=1)) | values))


async def test_ledger_sales_topups_and_legacy_orders_are_separate_without_double_counting(canteen_db):
    sessions, data = canteen_db
    async with sessions() as db:
        db.add_all([movement(data["children"][0], "15"), movement(data["children"][0], "20", "SALE"),
            movement(data["children"][0], "100", "CREDIT"), order(data, "15"), order(data, "7", quantity=2)])
        await db.commit()
        result = await get_recorded_canteen_summary(db, tenant(data))
    assert result["sales_amount"] == result["total_sales"] == "35.00"
    assert result["sale_record_count"] == 2 and result["topup_amount"] == "100.00"
    assert result["wallet_debit_amount"] == "15.00" and result["direct_sale_amount"] == "20.00"
    assert result["catalog_orders"]["amount"] == "22.00" and result["catalog_orders"]["quantity"] == 3
    assert result["catalog_orders"]["included_in_sales_total"] is False
    assert result["order_count"] == 2 and result["data_source"] == "canteen_wallet_transactions"
    assert result["inventory_status"] == "unknown" and result["recommendations"] == []
    assert not {"net_profit", "profit_margin", "confidence"} & result.keys()


async def test_completed_only_institution_branch_and_deleted_student_boundaries(canteen_db):
    sessions, data = canteen_db
    async with sessions() as db:
        branch = Branch(organization_id=data["org"].id, name="Another own branch")
        db.add(branch)
        await db.flush()
        other = Student(organization_id=data["org"].id, branch_id=branch.id, first_name="Other", last_name="Branch")
        deleted = Student(organization_id=data["org"].id, branch_id=data["branch"].id,
            first_name="Deleted", last_name="Record", deleted_at=datetime.now(UTC))
        db.add_all([other, deleted])
        await db.flush()
        child = data["children"][0]
        db.add_all([movement(child, "10"), movement(child, "800", status="PENDING"),
            movement(child, "900", status="CANCELLED"), movement(child, "600", "UNKNOWN"),
            movement(other, "1000"), movement(deleted, "2000"), movement(data["stranger"], "3000"),
            order(data, "5"), order(data, "100", status="CANCELLED"), order(data, "1000", child=other),
            order(data, "2000", child=deleted), order(data, "3000", child=data["stranger"]),
            order(data, "4000", branch_id=data["other_branch"].id)])
        await db.commit()
        scoped = tenant(data, branch_ids=[data["branch"].id])
        db.info["tenant_context"] = scoped
        result = await get_recorded_canteen_summary(db, scoped)
    assert result["sales_amount"] == "10.00" and result["sale_record_count"] == 1
    assert result["catalog_orders"]["amount"] == "5.00" and result["order_count"] == 1


async def test_parent_purpose_and_selected_child_never_expand_to_other_students(canteen_db):
    sessions, data = canteen_db
    parent = tenant(data, user_id=data["user"].id, role_slugs={"parent"},
        permissions={"parent.view_finances"}, parent_portal=True)
    async with sessions() as db:
        unrelated = Student(organization_id=data["org"].id, branch_id=data["branch"].id,
            first_name="Unlinked", last_name="Student")
        db.add(unrelated)
        await db.flush()
        db.add_all([movement(data["children"][0], "10"), movement(data["children"][1], "20"),
            movement(unrelated, "50"), movement(data["stranger"], "100")])
        await db.commit()
        selected = await get_recorded_canteen_summary(db, parent, purpose="chatbot", student_id=data["children"][0].id)
        own = await get_recorded_canteen_summary(db, parent, purpose="chatbot")
        for forbidden in (unrelated, data["stranger"]):
            with pytest.raises(ForbiddenException):
                await get_recorded_canteen_summary(db, parent, purpose="chatbot", student_id=forbidden.id)
        with pytest.raises(ForbiddenException):
            await get_recorded_canteen_summary(db, parent, purpose="analysis")
    assert selected["sales_amount"] == "10.00" and own["sales_amount"] == "30.00"


async def test_school_calendar_bounds_exact_days_year_rollover_and_future_exclusion(canteen_db):
    sessions, data = canteen_db
    today = school_today()
    start, tomorrow = today - timedelta(days=2), today + timedelta(days=1)
    first, end = school_day_bounds(start)[0], school_day_bounds(tomorrow)[0]
    async with sessions() as db:
        child = data["children"][0]
        db.add_all([movement(child, "5", created_at=first), movement(child, "10"),
            movement(child, "100", created_at=first - timedelta(microseconds=1)),
            movement(child, "200", created_at=end), movement(child, "300", created_at=datetime.now(UTC) + timedelta(hours=1)),
            order(data, "4"), order(data, "900", order_date=tomorrow),
            movement(child, "11", created_at=school_day_bounds(date(2025, 12, 31))[0]),
            movement(child, "13", created_at=school_day_bounds(date(2026, 1, 1))[0]),
            movement(child, "17", created_at=school_day_bounds(date(2026, 1, 2))[0])])
        await db.commit()
        result = await get_recorded_canteen_summary(db, tenant(data), days=3)
        year = await get_recorded_canteen_summary(db, tenant(data), start_date=date(2025, 12, 31), end_date_exclusive=date(2026, 1, 2))
    assert result["period_start"] == start.isoformat() and result["period_end_exclusive"] == tomorrow.isoformat()
    assert result["observed_day_count"] == 3 and result["sales_amount"] == "15.00" and result["daily_average"] == "5.00"
    assert result["order_count"] == 1 and result["catalog_orders"]["amount"] == "4.00"
    assert year["sales_amount"] == "24.00" and year["daily_average"] == "12.00"


async def test_empty_summary_is_unknown_zero_is_real_and_reading_creates_no_wallet(canteen_db):
    sessions, data = canteen_db
    async with sessions() as db:
        models = (StudentWallet, CanteenWalletTransaction, CanteenOrder)
        before = [await db.scalar(select(func.count()).select_from(model)) for model in models]
        empty = await get_recorded_canteen_summary(db, tenant(data))
        after = [await db.scalar(select(func.count()).select_from(model)) for model in models]
        assert before == after == [0, 0, 0]
        db.add_all([movement(data["children"][0], "0"), movement(data["children"][0], "0", "CREDIT"), order(data, "0", quantity=0)])
        await db.commit()
        zero = await get_recorded_canteen_summary(db, tenant(data))
        assert await db.scalar(select(func.count()).select_from(StudentWallet)) == 0
    assert empty["sales_amount"] is empty["daily_average"] is None and empty["sale_record_count"] == 0
    assert empty["history_status"] == "no_history" and empty["catalog_orders"]["amount"] is None
    assert zero["sales_amount"] == zero["topup_amount"] == zero["daily_average"] == "0.00"
    assert zero["sale_record_count"] == 1 and zero["catalog_orders"]["quantity"] == 0


async def test_nonfinite_sale_remains_unknown_without_corrupting_other_sources_or_rows(canteen_db):
    sessions, data = canteen_db
    async with sessions() as db:
        invalid = "NaN" if db.bind.dialect.name == "postgresql" else "Infinity"
        broken = movement(data["children"][0], invalid)
        db.add_all([broken, movement(data["children"][0], "2", "SALE"), movement(data["children"][0], "100", "CREDIT"), order(data, "7")])
        await db.commit()
        result = await get_recorded_canteen_summary(db, tenant(data))
        saved = await db.scalar(select(CanteenWalletTransaction.amount).where(CanteenWalletTransaction.id == broken.id))
    assert result["sales_amount"] is result["daily_average"] is None
    assert result["invalid_sale_amount_count"] == 1 and result["requires_review"] is True
    assert result["topup_amount"] == "100.00" and result["direct_sale_amount"] == "2.00"
    assert result["catalog_orders"]["amount"] == "7.00" and not saved.is_finite()


async def test_bad_credit_and_catalogue_do_not_change_valid_sale_and_quantity_is_unknown(canteen_db):
    sessions, data = canteen_db
    async with sessions() as db:
        invalid = "NaN" if db.bind.dialect.name == "postgresql" else "Infinity"
        db.add_all([movement(data["children"][0], "0"), movement(data["children"][0], "-3", "CREDIT"), order(data, invalid, quantity=-1)])
        await db.commit()
        result = await get_recorded_canteen_summary(db, tenant(data))
    assert result["sales_amount"] == "0.00" and result["invalid_sale_amount_count"] == 0
    assert result["topup_amount"] is None and result["invalid_topup_amount_count"] == 1
    assert result["catalog_orders"]["amount"] is result["catalog_orders"]["quantity"] is None
    assert result["catalog_orders"]["invalid_amount_count"] == result["catalog_orders"]["invalid_quantity_count"] == 1


async def test_unused_legacy_identifiers_and_methods_are_not_hydrated(canteen_db):
    sessions, data = canteen_db
    async with sessions() as db:
        db.add_all([movement(data["children"][0], "9", payment_method="LEGACY METHOD"), order(data, "4", payment_method="OLD UNKNOWN")])
        await db.commit()
        if db.bind.dialect.name == "sqlite":
            await db.execute(text("UPDATE canteen_wallet_transactions SET id='legacy-movement', processed_by='invalid-uuid'"))
            await db.execute(text("UPDATE canteen_orders SET id='legacy-order', product_id='invalid-product', processed_by='invalid-uuid'"))
            await db.commit()
        result = await get_recorded_canteen_summary(db, tenant(data))
    assert result["sales_amount"] == "9.00" and result["catalog_orders"]["amount"] == "4.00"


async def test_validation_and_policy_remain_specific_and_sql_failure_is_sanitized(canteen_db, monkeypatch):
    sessions, data = canteen_db
    async with sessions() as db:
        for days in (0, -1, 366, True):
            with pytest.raises(ValidationException):
                await get_recorded_canteen_summary(db, tenant(data), days=days)
        with pytest.raises(ValidationException):
            await get_recorded_canteen_summary(db, tenant(data), start_date=school_today())
        today = school_today()
        for start, end in ((datetime.now(UTC), today), (today, today),
            (today + timedelta(days=1), today), (today, today + timedelta(days=366))):
            with pytest.raises(ValidationException):
                await get_recorded_canteen_summary(db, tenant(data), start_date=start, end_date_exclusive=end)
        with pytest.raises(ValidationException):
            await get_recorded_canteen_summary(db, tenant(data), purpose="unknown")
        with pytest.raises(ValidationException):
            await get_recorded_canteen_summary(db, tenant(data), student_id="malformed")
        with pytest.raises(ForbiddenException):
            await get_recorded_canteen_summary(db, tenant(data, permissions={"finance.read"}))
        with pytest.raises(ForbiddenException):
            await get_recorded_canteen_summary(db, tenant(data, organization_id=None, is_super_admin=True))
        async def fail(*_args, **_kwargs):
            raise SQLAlchemyError("PRIVATE SQL AND CONNECTION DETAILS")
        monkeypatch.setattr(db, "execute", fail)
        with pytest.raises(AppException) as failure:
            await get_recorded_canteen_summary(db, tenant(data))
        assert failure.value.status_code == 503 and "PRIVATE" not in failure.value.message


async def test_bulk_ten_thousand_sales_keep_exact_scope_and_constant_query_count(canteen_db):
    sessions, data = canteen_db
    child = data["children"][0]
    timestamp = datetime.now(UTC) - timedelta(seconds=1)
    rows = [dict(student_id=child.id, amount=Decimal("1.25") if index % 2 == 0 else Decimal("2.75"),
        transaction_type="DEBIT" if index % 2 == 0 else "SALE", status="COMPLETED", created_at=timestamp)
        for index in range(10_000)]
    rows.extend(dict(student_id=child.id, amount=Decimal("100"), transaction_type="CREDIT",
        status="COMPLETED", created_at=timestamp) for _ in range(100))
    rows.extend(dict(student_id=data["children"][1].id, amount=Decimal("9"), transaction_type="SALE",
        status="COMPLETED", created_at=timestamp) for _ in range(200))
    rows.extend(dict(student_id=data["stranger"].id, amount=Decimal("7"), transaction_type="DEBIT",
        status="COMPLETED", created_at=timestamp) for _ in range(20))
    async with sessions() as db:
        await db.execute(insert(CanteenWalletTransaction), rows)
        db.add_all([order(data, "15"), order(data, "7"), order(data, "999", child=data["children"][1])])
        await db.commit()
        engine = db.bind.sync_engine
        queries = []

        def count_query(_connection, _cursor, statement, _parameters, _context, _many):
            queries.append(statement)

        event.listen(engine, "before_cursor_execute", count_query)
        try:
            started = perf_counter()
            result = await get_recorded_canteen_summary(db, tenant(data), student_id=child.id)
            elapsed_ms = (perf_counter() - started) * 1000
        finally:
            event.remove(engine, "before_cursor_execute", count_query)
        print(f"recorded_canteen bulk dialect={db.bind.dialect.name} sales=10000 queries={len(queries)} elapsed_ms={elapsed_ms:.2f}")
    assert result["sales_amount"] == "20000.00" and result["sale_record_count"] == 10_000
    assert result["wallet_debit_amount"] == "6250.00" and result["direct_sale_amount"] == "13750.00"
    assert result["topup_amount"] == "10000.00" and result["topup_record_count"] == 100
    assert result["catalog_orders"]["amount"] == "22.00" and result["order_count"] == 2
    assert result["catalog_orders"]["included_in_sales_total"] is False
    assert 1 <= len(queries) <= 12
