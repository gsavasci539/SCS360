"""Intent handlers for processing chatbot queries."""

import logging
from datetime import date as date_type, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.chatbot.date_resolution import DateResolutionService
from app.application.services.chatbot.intent_schemas import DateRange, ResolvedIntent
from app.domain.entities.user import User
from app.infrastructure.models.models import (
    AttendanceRecord,
    Debt,
    Expense,
    Payment,
    Student,
    User as UserModel,
)
from app.domain.entities.canteen import CanteenOrder, CanteenProduct

logger = logging.getLogger(__name__)


class HandlerResponse:
    """Response from intent handler."""

    def __init__(
        self,
        message: str,
        suggested_actions: Optional[list[dict]] = None,
        data: Optional[dict] = None,
    ):
        self.message = message
        self.suggested_actions = suggested_actions or []
        self.data = data or {}


class AttendanceHandler:
    """Handler for attendance-related queries."""

    async def handle(
        self,
        intent: ResolvedIntent,
        current_user: User,
        db: AsyncSession,
    ) -> HandlerResponse:
        """Handle attendance intent."""
        try:
            date_range = intent.date_range
            if not date_range:
                # Default to today if no date range specified
                date_resolver = DateResolutionService()
                date_range = date_resolver.resolve_period("today")

            if not date_range:
                return HandlerResponse(
                    message="📅 Tarih belirlenemedi. Lütfen geçerli bir tarih aralığı belirtin."
                )

            # Check if user has specific student access
            if intent.student_id:
                # Query specific student attendance
                attendance_result = await db.execute(
                    select(AttendanceRecord)
                    .where(AttendanceRecord.student_id == intent.student_id)
                    .where(AttendanceRecord.attendance_date.between(
                        date_range.start_date,
                        date_range.end_date
                    ))
                    .order_by(AttendanceRecord.attendance_date.desc())
                )
                records = attendance_result.scalars().all()

                if not records:
                    return HandlerResponse(
                        message=f"📅 {date_range.description} için devamsızlık kaydı bulunmuyor."
                    )

                # Calculate attendance summary
                present = sum(1 for r in records if r.status.value == "PRESENT")
                absent = sum(1 for r in records if r.status.value == "ABSENT")
                excused = sum(1 for r in records if r.status.value == "EXCUSED")
                late = sum(1 for r in records if r.status.value == "LATE")

                total = len(records)
                attendance_rate = (present / total * 100) if total > 0 else 0

                message = (
                    f"📅 **Devamsızlık Özeti ({date_range.description})**\n\n"
                    f"- Toplam gün: {total}\n"
                    f"- Katılım: {present} (%{attendance_rate:.1f})\n"
                    f"- Devamsız: {absent}\n"
                    f"- Mazeretli: {excused}\n"
                    f"- Geç kaldı: {late}"
                )

                return HandlerResponse(
                    message=message,
                    suggested_actions=[
                        {"label": "📊 Detaylı Rapor", "action_tag": "VIEW_ATTENDANCE_REPORT"},
                    ]
                )

            else:
                # Query all accessible students attendance (for teachers/admins)
                if current_user.organization_id:
                    attendance_result = await db.execute(
                        select(AttendanceRecord)
                        .where(AttendanceRecord.organization_id == current_user.organization_id)
                        .where(AttendanceRecord.attendance_date.between(
                            date_range.start_date,
                            date_range.end_date
                        ))
                        .order_by(AttendanceRecord.attendance_date.desc())
                    )
                    records = attendance_result.scalars().all()

                    if not records:
                        return HandlerResponse(
                            message=f"📅 {date_range.description} için devamsızlık kaydı bulunmuyor."
                        )

                    # Summary for all students
                    present = sum(1 for r in records if r.status.value == "PRESENT")
                    absent = sum(1 for r in records if r.status.value == "ABSENT")
                    total = len(records)

                    message = (
                        f"📅 **Genel Devamsızlık ({date_range.description})**\n\n"
                        f"- Toplam kayıt: {total}\n"
                        f"- Katılım: {present}\n"
                        f"- Devamsız: {absent}"
                    )

                    return HandlerResponse(
                        message=message,
                        suggested_actions=[
                            {"label": "📊 Detaylı Rapor", "action_tag": "VIEW_ATTENDANCE_REPORT"},
                        ]
                    )

        except Exception as e:
            logger.exception(f"Error handling attendance intent: {e}")
            return HandlerResponse(
                message="📅 Devamsızlık bilgileri alınırken hata oluştu. Lütfen daha sonra tekrar deneyin."
            )


class GradesHandler:
    """Handler for grades-related queries."""

    async def handle(
        self,
        intent: ResolvedIntent,
        current_user: User,
        db: AsyncSession,
    ) -> HandlerResponse:
        """Handle grades intent."""
        try:
            if intent.student_id:
                from app.application.services.academic_records import records
                grades = await records(db, current_user.organization_id, [intent.student_id], limit=10)

                if not grades:
                    return HandlerResponse(
                        message="📊 Henüz not kaydı bulunmuyor."
                    )

                # Build grades summary
                grade_lines = []
                for grade in grades:
                    subject = grade.subject.value if hasattr(grade.subject, 'value') else str(grade.subject)
                    grade_lines.append(
                        f"- {subject}: {grade.score if grade.score is not None else (grade.grade_scale or '—')}/{grade.max_score if grade.max_score is not None else '—'} ({grade.exam_date.strftime('%d.%m.%Y')})"
                    )

                message = (
                    f"📊 **Son Notlar**\n\n"
                    + "\n".join(grade_lines)
                )

                return HandlerResponse(
                    message=message,
                    suggested_actions=[
                        {"label": "📊 Tüm Notlar", "action_tag": "VIEW_GRADES"},
                    ]
                )

            else:
                return HandlerResponse(
                    message="📊 Not bilgileri için öğrenci seçin.",
                    suggested_actions=[
                        {"label": "👥 Öğrenciler", "action_tag": "VIEW_STUDENTS"},
                    ]
                )

        except Exception as e:
            logger.exception(f"Error handling grades intent: {e}")
            return HandlerResponse(
                message="📊 Not bilgileri alınırken hata oluştu. Lütfen daha sonra tekrar deneyin."
            )


class PaymentsHandler:
    """Handler for payment-related queries."""

    async def handle(
        self,
        intent: ResolvedIntent,
        current_user: User,
        db: AsyncSession,
    ) -> HandlerResponse:
        """Handle payments intent."""
        try:
            date_range = intent.date_range
            if not date_range and intent.operation == "summary":
                # Default to this month for summaries
                date_resolver = DateResolutionService()
                date_range = date_resolver.resolve_period("this_month")

            if not current_user.organization_id:
                return HandlerResponse(
                    message="💰 Kurum bilgisi bulunamadı."
                )

            from app.core.dates import school_day_bounds, school_datetime
            query = select(Payment).where(Payment.organization_id == current_user.organization_id,
                Payment.status == "completed", Payment.cancelled_at.is_(None))
            if intent.student_id:
                query = query.where(Payment.student_id == intent.student_id)
            if date_range:
                lower, _ = school_day_bounds(date_range.start_date)
                _, upper = school_day_bounds(date_range.end_date)
                query = query.where(Payment.payment_date >= lower, Payment.payment_date < upper)
            if intent.operation == "summary" and date_range:
                total = (await db.execute(query.with_only_columns(func.coalesce(func.sum(Payment.amount), 0), maintain_column_froms=True))).scalar_one()
                return HandlerResponse(message=f"💳 **Ödeme Özeti ({date_range.description})**\n\nToplam ödeme: {total:,.2f} TL",
                    suggested_actions=[{"label": "💳 Ödeme Detayları", "action_tag": "VIEW_PAYMENTS"}])
            payments = (await db.execute(query.order_by(Payment.payment_date.desc(), Payment.id).limit(5))).scalars().all()
            if not payments:
                return HandlerResponse(message="💰 Henüz geçerli ödeme kaydı bulunmuyor.")
            lines = [f"- {payment.amount:,.2f} TL - {payment.notes or 'Ödeme'} - {school_datetime(payment.payment_date).strftime('%d.%m.%Y')}" for payment in payments]
            return HandlerResponse(message="💰 **Son Ödemeler**\n\n" + "\n".join(lines),
                suggested_actions=[{"label": "💳 Tüm Ödemeler", "action_tag": "VIEW_PAYMENTS"}])

        except Exception as e:
            logger.exception(f"Error handling payments intent: {e}")
            return HandlerResponse(
                message="💰 Ödeme bilgileri alınırken hata oluştu. Lütfen daha sonra tekrar deneyin."
            )


class DebtHandler:
    """Handler for debt-related queries."""

    async def handle(
        self,
        intent: ResolvedIntent,
        current_user: User,
        db: AsyncSession,
    ) -> HandlerResponse:
        """Handle debt intent."""
        try:
            if intent.student_id:
                # Query specific student debt
                result = await db.execute(
                    select(Debt)
                    .where(Debt.student_id == intent.student_id, Debt.deleted_at.is_(None), Debt.amount > Debt.paid_amount)
                    .where(Debt.status.in_(["UNPAID", "PARTIALLY_PAID", "OVERDUE"]))
                )
                debts = result.scalars().all()

                if not debts:
                    return HandlerResponse(
                        message="💳 Ödenmemiş borç bulunmuyor."
                    )

                total_debt = sum(d.amount for d in debts)
                remaining_debt = sum(d.amount - d.paid_amount for d in debts)
                total_paid = sum(d.paid_amount for d in debts)

                message = (
                    f"💳 **Borç Durumu**\n\n"
                    f"- Toplam borç: {total_debt:,.2f} TL\n"
                    f"- Ödenen: {total_paid:,.2f} TL\n"
                    f"- Kalan: {remaining_debt:,.2f} TL"
                )

                return HandlerResponse(
                    message=message,
                    suggested_actions=[
                        {"label": "💳 Borç Detayları", "action_tag": "VIEW_DEBTS"},
                    ]
                )

            else:
                return HandlerResponse(
                    message="💳 Borç bilgileri için öğrenci seçin.",
                    suggested_actions=[
                        {"label": "👥 Öğrenciler", "action_tag": "VIEW_STUDENTS"},
                    ]
                )

        except Exception as e:
            logger.exception(f"Error handling debt intent: {e}")
            return HandlerResponse(
                message="💳 Borç bilgileri alınırken hata oluştu. Lütfen daha sonra tekrar deneyin."
            )


class ExpensesHandler:
    """Handler for expense-related queries."""

    async def handle(
        self,
        intent: ResolvedIntent,
        current_user: User,
        db: AsyncSession,
    ) -> HandlerResponse:
        """Handle expenses intent."""
        try:
            if not current_user.organization_id:
                return HandlerResponse(
                    message="📉 Kurum bilgisi bulunamadı."
                )

            date_range = intent.date_range
            if not date_range:
                date_resolver = DateResolutionService()
                date_range = date_resolver.resolve_period("this_month")

            if date_range:
                # Query expenses for the period
                result = await db.execute(
                    select(func.sum(Expense.amount))
                    .where(Expense.organization_id == current_user.organization_id)
                    .where(Expense.expense_date.between(
                        date_range.start_date,
                        date_range.end_date
                    ))
                )
                total = result.scalar() or Decimal("0")

                message = (
                    f"📉 **Gider Özeti ({date_range.description})**\n\n"
                    f"Toplam gider: {total:,.2f} TL"
                )

                return HandlerResponse(
                    message=message,
                    suggested_actions=[
                        {"label": "📉 Gider Detayları", "action_tag": "VIEW_EXPENSES"},
                    ]
                )

            else:
                # Show recent expenses
                result = await db.execute(
                    select(Expense)
                    .where(Expense.organization_id == current_user.organization_id)
                    .order_by(Expense.expense_date.desc())
                    .limit(5)
                )
                expenses = result.scalars().all()

                if not expenses:
                    return HandlerResponse(
                        message="📉 Henüz gider kaydı bulunmuyor."
                    )

                expense_lines = []
                for expense in expenses:
                    amount = float(expense.amount)
                    category = expense.category or "Genel"
                    expense_date = expense.expense_date.strftime("%d.%m.%Y")
                    expense_lines.append(f"- {amount:,.2f} TL - {category} - {expense_date}")

                message = (
                    f"📉 **Son Giderler**\n\n"
                    + "\n".join(expense_lines)
                )

                return HandlerResponse(
                    message=message,
                    suggested_actions=[
                        {"label": "📉 Tüm Giderler", "action_tag": "VIEW_EXPENSES"},
                    ]
                )

        except Exception as e:
            logger.exception(f"Error handling expenses intent: {e}")
            return HandlerResponse(
                message="📉 Gider bilgileri alınırken hata oluştu. Lütfen daha sonra tekrar deneyin."
            )


class CanteenHandler:
    """Handler for canteen-related queries."""

    async def handle(
        self,
        intent: ResolvedIntent,
        current_user: User,
        db: AsyncSession,
    ) -> HandlerResponse:
        """Handle canteen intent."""
        try:
            if not current_user.organization_id:
                return HandlerResponse(
                    message="🥪 Kurum bilgisi bulunamadı."
                )

            date_range = intent.date_range
            if not date_range:
                date_resolver = DateResolutionService()
                date_range = date_resolver.resolve_period("today")

            if intent.operation == "summary" and date_range:
                # Query real canteen data from CanteenOrder table
                
                # Get orders for the date range
                orders_result = await db.execute(
                    select(CanteenOrder)
                    .where(CanteenOrder.order_date.between(date_range.start_date, date_range.end_date))
                    .where(CanteenOrder.status == "COMPLETED")
                )
                orders = orders_result.scalars().all()

                if not orders:
                    return HandlerResponse(
                        message=f"🥪 {date_range.description} için kantin satış kaydı bulunmuyor."
                    )

                # Calculate metrics
                total_revenue = sum(float(order.total_price) for order in orders)
                total_orders = len(orders)
                avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
                
                # Assume 36% profit margin (can be made configurable)
                profit_margin = 0.36
                net_profit = total_revenue * profit_margin

                # Group by payment method
                payment_methods = {}
                for order in orders:
                    method = order.payment_method or "OTHER"
                    if method not in payment_methods:
                        payment_methods[method] = 0
                    payment_methods[method] += float(order.total_price)

                # Format payment methods
                payment_lines = []
                for method, amount in payment_methods.items():
                    percentage = (amount / total_revenue * 100) if total_revenue > 0 else 0
                    payment_lines.append(f"{method}: ₺{amount:,.2f} (%{percentage:.0f})")

                # Get top selling products
                product_sales = {}
                for order in orders:
                    product_id = str(order.product_id)
                    if product_id not in product_sales:
                        product_sales[product_id] = {"quantity": 0, "revenue": 0, "name": None}
                    product_sales[product_id]["quantity"] += order.quantity
                    product_sales[product_id]["revenue"] += float(order.total_price)

                # Get product names
                for product_id in product_sales.keys():
                    try:
                        product_result = await db.execute(
                            select(CanteenProduct).where(CanteenProduct.id == UUID(product_id))
                        )
                        product = product_result.scalar_one_or_none()
                        if product:
                            product_sales[product_id]["name"] = product.name
                    except Exception:
                        pass

                # Sort by quantity and get top 5
                top_products = sorted(
                    product_sales.items(),
                    key=lambda x: x[1]["quantity"],
                    reverse=True
                )[:5]

                top_products_lines = []
                for product_id, data in top_products:
                    name = data["name"] or "Bilinmeyen Ürün"
                    quantity = data["quantity"]
                    revenue = data["revenue"]
                    top_products_lines.append(f"{name} ({quantity} Adet • ₺{revenue:,.0f})")

                # Build response matching specification format
                message = (
                    f"🥪 **Kantin & POS Satış Hasılatı ve Günlük Kazanç Raporu:**\n\n"
                    f"💰 **Günlük Kazanç & Ciro Performansı:**\n"
                    f"• **Bugünkü Toplam Kantin Kazancı (Ciro):** ₺{total_revenue:,.2f}\n"
                    f"• **Toplam İşlem / Fiş Sayısı:** {total_orders} Adet Satış (Ortalama Fiş: ₺{avg_order_value:,.2f})\n"
                    f"• **Tahmini Net Kar:** ₺{net_profit:,.2f} (Brüt Kar Marjı: %{profit_margin*100:.0f})\n\n"
                    f"💳 **Tahsilat Türü:** {', '.join(payment_lines) if payment_lines else 'Veri yok'}\n\n"
                    f"🏆 **Top Satanlar:** {', '.join(top_products_lines) if top_products_lines else 'Veri yok'}"
                )

                return HandlerResponse(
                    message=message,
                    suggested_actions=[
                        {"label": "🥪 POS Satış Ekranı", "action_tag": "NAV_POS"},
                        {"label": "💼 Finans & Kasa", "action_tag": "NAV_FINANCE"},
                        {"label": "💳 Cüzdan Yükle", "action_tag": "NAV_WALLET"},
                        {"label": "🛒 Stok Kataloğu", "action_tag": "NAV_STOCK"},
                    ]
                )
            else:
                message = (
                    f"🥪 **Kantin Bilgileri**\n\n"
                    f"Kantin satışları ve stok durumu için detaylı raporu görüntüleyebilirsiniz."
                )

                return HandlerResponse(
                    message=message,
                    suggested_actions=[
                        {"label": "🥪 POS Satış Ekranı", "action_tag": "NAV_POS"},
                        {"label": "🛒 Stok Kataloğu", "action_tag": "NAV_STOCK"},
                    ]
                )

        except Exception as e:
            logger.exception(f"Error handling canteen intent: {e}")
            return HandlerResponse(
                message="🥪 Kantin bilgileri alınırken hata oluştu. Lütfen daha sonra tekrar deneyin."
            )


class StudentInfoHandler:
    """Handler for student information queries."""

    async def handle(
        self,
        intent: ResolvedIntent,
        current_user: User,
        db: AsyncSession,
    ) -> HandlerResponse:
        """Handle student info intent."""
        try:
            if intent.student_id:
                # Query specific student
                result = await db.execute(
                    select(Student).where(Student.id == intent.student_id)
                )
                student = result.scalar_one_or_none()

                if not student:
                    return HandlerResponse(
                        message="📚 Öğrenci bulunamadı."
                    )

                message = (
                    f"📚 **Öğrenci Bilgisi**\n\n"
                    f"Ad: {student.first_name} {student.last_name}\n"
                    f"Öğrenci No: {student.student_number or '-'}\n"
                    f"Durum: {student.status.value if hasattr(student.status, 'value') else student.status}"
                )

                return HandlerResponse(
                    message=message,
                    suggested_actions=[
                        {"label": "📊 Notlar", "action_tag": "VIEW_GRADES"},
                        {"label": "📅 Devamsızlık", "action_tag": "VIEW_ATTENDANCE"},
                    ]
                )

            else:
                # Show student count
                if current_user.organization_id:
                    result = await db.execute(
                        select(func.count(Student.id))
                        .where(Student.organization_id == current_user.organization_id)
                        .where(Student.deleted_at.is_(None))
                    )
                    count = result.scalar() or 0

                    message = f"📚 Toplam {count} öğrenci kayıtlı."

                    return HandlerResponse(
                        message=message,
                        suggested_actions=[
                            {"label": "👥 Öğrenci Listesi", "action_tag": "VIEW_STUDENTS"},
                        ]
                    )

        except Exception as e:
            logger.exception(f"Error handling student info intent: {e}")
            return HandlerResponse(
                message="📚 Öğrenci bilgileri alınırken hata oluştu. Lütfen daha sonra tekrar deneyin."
            )


class SystemStatusHandler:
    """Handler for system status queries."""

    async def handle(
        self,
        intent: ResolvedIntent,
        current_user: User,
        db: AsyncSession,
    ) -> HandlerResponse:
        """Handle system status intent."""
        try:
            if not current_user.organization_id:
                return HandlerResponse(
                    message="📊 Kurum bilgisi bulunamadı."
                )

            # Get counts
            student_result = await db.execute(
                select(func.count(Student.id))
                .where(Student.organization_id == current_user.organization_id)
                .where(Student.deleted_at.is_(None))
            )
            student_count = student_result.scalar() or 0

            user_result = await db.execute(
                select(func.count(UserModel.id))
                .where(UserModel.organization_id == current_user.organization_id)
                .where(UserModel.deleted_at.is_(None))
            )
            user_count = user_result.scalar() or 0

            message = (
                f"📊 **Sistem Durumu**\n\n"
                f"- 👨‍🎓 Toplam öğrenci: {student_count}\n"
                f"- 👥 Toplam kullanıcı: {user_count}\n"
                f"- 🟢 Sistem durumu: Aktif"
            )

            return HandlerResponse(
                message=message,
                suggested_actions=[
                    {"label": "📊 Dashboard", "action_tag": "VIEW_DASHBOARD"},
                    {"label": "👥 Kullanıcılar", "action_tag": "VIEW_USERS"},
                    {"label": "👥 Öğrenciler", "action_tag": "VIEW_STUDENTS"},
                ]
            )

        except Exception as e:
            logger.exception(f"Error handling system status intent: {e}")
            return HandlerResponse(
                message="📊 Sistem durumu alınırken hata oluştu. Lütfen daha sonra tekrar deneyin."
            )


class GeneralHandler:
    """Handler for general/unknown queries."""

    async def handle(
        self,
        intent: ResolvedIntent,
        current_user: User,
        db: AsyncSession,
    ) -> HandlerResponse:
        """Handle general intent."""
        role = intent.raw_intent.confidence if intent.raw_intent else 0.5

        if role < 0.4:
            # Low confidence - show help
            message = (
                "🤖 **SCS360 Asistanı**\n\n"
                "Size nasıl yardımcı olabilirim?\n\n"
                "📅 Devamsızlık bilgileri\n"
                "📊 Notlar ve sınav sonuçları\n"
                "💰 Ödemeler ve borç durumu\n"
                "📚 Öğrenci bilgileri\n"
                "📢 Duyurular"
            )
        else:
            # General greeting
            message = (
                "🤖 **SCS360 Asistanı**\n\n"
                "Merhaba! Size nasıl yardımcı olabilirim?\n\n"
                "Öğrenci, devamsızlık, not, ödeme veya diğer konular hakkında sorular sorabilirsiniz."
            )

        return HandlerResponse(
            message=message,
            suggested_actions=[
                {"label": "📅 Devamsızlık", "action_tag": "VIEW_ATTENDANCE"},
                {"label": "📊 Notlar", "action_tag": "VIEW_GRADES"},
                {"label": "💰 Ödemeler", "action_tag": "VIEW_PAYMENTS"},
            ]
        )


class NavigationHandler:
    """Return a useful response for supported sections without a data summary handler."""

    ACTIONS = {
        "HOMEWORK": ("📚 Ödevler", "Ödevleri görüntülemek için detay sayfasını açabilirsiniz.", "VIEW_HOMEWORK"),
        "ANNOUNCEMENTS": ("📢 Duyurular", "Güncel duyuruları detay sayfasında görüntüleyebilirsiniz.", "VIEW_ANNOUNCEMENTS"),
        "NOTIFICATIONS": ("🔔 Bildirimler", "Bildirimlerinizi detay sayfasında görüntüleyebilirsiniz.", "VIEW_NOTIFICATIONS"),
        "CANTEEN_BALANCE": ("💳 Kantin Bakiyesi", "Kart bakiyesini detay sayfasında görüntüleyebilirsiniz.", "VIEW_CANTEEN_BALANCE"),
        "REPORTS": ("📈 Raporlar", "Raporları detay sayfasından görüntüleyebilirsiniz.", "VIEW_REPORTS"),
    }

    async def handle(
        self,
        intent: ResolvedIntent,
        current_user: User,
        db: AsyncSession,
    ) -> HandlerResponse:
        if intent.intent not in self.ACTIONS:
            return HandlerResponse(
                message=f"Bu özellik için detaylı sayfa bulunmuyor.",
                suggested_actions=[]
            )
        
        label, message, action_tag = self.ACTIONS[intent.intent]
        return HandlerResponse(
            message=f"{label}\n\n{message}",
            suggested_actions=[{"label": f"{label} detayları", "action_tag": action_tag}],
        )


class HandlerDispatcher:
    """Dispatcher for routing intents to appropriate handlers."""

    def __init__(self):
        self.handlers = {
            "ATTENDANCE": AttendanceHandler(),
            "GRADES": GradesHandler(),
            "PAYMENTS": PaymentsHandler(),
            "PAYMENT_SUMMARY": PaymentsHandler(),
            "DEBT": DebtHandler(),
            "EXPENSES": ExpensesHandler(),
            "CANTEEN": CanteenHandler(),
            "STUDENT_INFO": StudentInfoHandler(),
            "SYSTEM_STATUS": SystemStatusHandler(),
            "HOMEWORK": NavigationHandler(),
            "ANNOUNCEMENTS": NavigationHandler(),
            "NOTIFICATIONS": NavigationHandler(),
            "CANTEEN_BALANCE": NavigationHandler(),
            "REPORTS": NavigationHandler(),
            "GENERAL": GeneralHandler(),
        }

    async def dispatch(
        self,
        intent: ResolvedIntent,
        current_user: User,
        db: AsyncSession,
    ) -> HandlerResponse:
        """Dispatch intent to appropriate handler."""
        rules = {
            "ATTENDANCE": (["attendance.read", "teacher.view_attendance"], "parent.view_attendance"),
            "GRADES": (["academic.read"], "parent.view_children"),
            "PAYMENTS": (["finance.read"], "parent.view_finances"),
            "PAYMENT_SUMMARY": (["finance.read"], "parent.view_finances"),
            "DEBT": (["finance.read"], "parent.view_finances"),
            "EXPENSES": (["finance.read"], None), "CANTEEN": (["canteen.read"], "parent.view_finances"),
            "STUDENT_INFO": (["students.read"], "parent.view_children"),
            "SYSTEM_STATUS": (["dashboard.read"], None),
            "HOMEWORK": (["homework.read"], "parent.view_children"),
            "ANNOUNCEMENTS": (["announcements.read"], "parent.view_children"),
            "NOTIFICATIONS": (["notification.read"], "parent.view_children"),
            "CANTEEN_BALANCE": (["canteen.read"], "parent.view_finances"),
            "REPORTS": (["report.read"], "parent.view_children"),
        }
        if intent.intent in rules:
            tenant = db.info.get("tenant_context")
            primary, guardian = rules[intent.intent]
            parent_mode = tenant and (tenant.parent_portal or tenant.role_slugs == {"parent"})
            if tenant is None or not (tenant.has_any_permission(primary) or (parent_mode and guardian and tenant.has_permission(guardian))):
                return HandlerResponse(message="Bu bilgiyi görüntüleme yetkiniz bulunmuyor.")
        handler = self.handlers.get(intent.intent)

        if not handler:
            logger.warning(f"No handler found for intent: {intent.intent}")
            handler = self.handlers["GENERAL"]

        return await handler.handle(intent, current_user, db)
