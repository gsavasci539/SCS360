"""Legacy finance URLs use the same ledger and outbox as the canonical API."""
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy import select

from app.core.dates import school_today
from app.core.exceptions import ValidationException
from app.infrastructure.models.models import (Debt, DebtStatus, DebtType, Student, Parent, StudentParent,
    NotificationJob, NotificationRecipient, NotificationChannel)
from app.infrastructure.repositories.base import BaseRepository


async def plan(db, tenant, user, body):
    student = await BaseRepository(db, tenant).get_by_id(body.student_id, Student)
    down = body.down_payment or Decimal(0)
    if down > body.total_amount:
        raise ValidationException("Peşinat toplam tutardan fazla olamaz")
    cents = int((body.total_amount - down) * 100)
    if cents and cents < body.installment_count:
        raise ValidationException("Her taksit en az 0,01 TL olmalı")
    amounts = [Decimal(cents // body.installment_count + (index < cents % body.installment_count)) / 100
        for index in range(body.installment_count)] if cents else []
    category = {"TRANSPORT": "SERVICE", "UNIFORM": "OTHER"}.get(body.category, body.category)
    values = [(down, school_today(), "Peşinat")] if down else []
    values.extend((amount, body.first_due_date + relativedelta(months=index), f"{index + 1}. Taksit")
        for index, amount in enumerate(amounts))
    debts = []
    for amount, due, description in values:
        debt = Debt(organization_id=student.organization_id, branch_id=student.branch_id, student_id=student.id,
            debt_type=DebtType(category), description=f"{category} - {description}", amount=amount,
            paid_amount=0, due_date=due, status=DebtStatus.UNPAID, created_by=user.id)
        db.add(debt)
        debts.append(debt)
    await db.flush()
    return {"student_id": str(student.id), "total_amount": str(body.total_amount), "down_payment": str(down),
        "installment_count": len(amounts), "installment_amount": str(amounts[0] if amounts else 0),
        "installment_amounts": [str(amount) for amount in amounts],
        "invoices": [{"id": str(row.id), "amount": str(row.amount), "due_date": row.due_date.isoformat()} for row in debts]}


async def reminders(db, tenant, user, body):
    debts = []
    repo = BaseRepository(db, tenant)
    # Validate every requested record before creating any jobs.
    for identifier in dict.fromkeys(body.invoice_ids):
        debts.append(await repo.get_by_id(identifier, Debt))
    result, skipped = [], []
    for debt in debts:
        if debt.status == DebtStatus.CANCELLED or debt.remaining_amount <= 0:
            skipped.append({"invoice_id": str(debt.id), "reason": "Ödenmiş veya iptal edilmiş borç"})
            continue
        student = await repo.get_by_id(debt.student_id, Student)
        parents = (await db.execute(select(Parent).join(StudentParent, StudentParent.parent_id == Parent.id)
            .where(StudentParent.student_id == student.id, Parent.organization_id == debt.organization_id,
                Parent.deleted_at.is_(None), Parent.receive_notifications.is_(True)))).scalars().all()
        targets = {}
        for parent in parents:
            address = parent.email if body.channel == "EMAIL" else (
                (parent.whatsapp_phone if body.channel == "WHATSAPP" else parent.sms_phone) or parent.phone)
            if address and address.strip():
                targets.setdefault(address.strip(), parent)
        if not targets:
            skipped.append({"invoice_id": str(debt.id), "reason": "Bildirim alıcısı veya iletişim adresi bulunamadı"})
            continue
        job = NotificationJob(organization_id=debt.organization_id, branch_id=debt.branch_id,
            channel=NotificationChannel(body.channel), subject="Ödeme hatırlatması",
            body=f"{student.first_name} {student.last_name} için {debt.remaining_amount} TL tutarındaki ödemenin vadesi {debt.due_date.isoformat()}.",
            reference_type="DEBT_REMINDER", reference_id=debt.id, created_by=user.id)
        db.add(job)
        await db.flush()
        db.add_all([NotificationRecipient(notification_job_id=job.id, parent_id=parent.id,
            recipient_address=address, recipient_name=f"{parent.first_name} {parent.last_name}")
            for address, parent in targets.items()])
        result.append({"invoice_id": str(debt.id), "student_id": str(student.id), "job_id": str(job.id),
            "channel": body.channel, "status": "QUEUED", "recipients": len(targets)})
    await db.flush()
    return {"total_sent": 0, "total_queued": len(result), "reminders": result, "skipped": skipped}
