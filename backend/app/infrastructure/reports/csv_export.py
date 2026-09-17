import csv
import io
from typing import Any


def export_debts_csv(debts: list[Any]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "student_id", "debt_type", "amount", "paid_amount", "status", "due_date"])
    for d in debts:
        writer.writerow([
            str(d.id),
            str(d.student_id),
            d.debt_type.value,
            str(d.amount),
            str(d.paid_amount),
            d.status.value,
            d.due_date.isoformat(),
        ])
    return output.getvalue()
