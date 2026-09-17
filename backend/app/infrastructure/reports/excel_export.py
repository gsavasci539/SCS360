import io
from typing import Any


def export_debts_excel(debts: list[Any]) -> bytes:
    try:
        from openpyxl import Workbook
    except ImportError:
        from app.infrastructure.reports.csv_export import export_debts_csv
        csv_content = export_debts_csv(debts)
        return csv_content.encode("utf-8-sig")

    wb = Workbook()
    ws = wb.active
    ws.title = "Borçlar"
    ws.append(["Öğrenci ID", "Tür", "Tutar", "Ödenen", "Durum", "Vade"])
    for d in debts:
        ws.append([
            str(d.student_id),
            d.debt_type.value,
            float(d.amount),
            float(d.paid_amount),
            d.status.value,
            d.due_date.isoformat(),
        ])
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.read()
