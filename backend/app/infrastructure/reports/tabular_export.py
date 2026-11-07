"""Render the same scoped rows used by the report API as CSV or XLSX."""
import csv
from io import BytesIO, StringIO


def _text(value):
    if value is None:
        return ""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def export_rows(rows: list[dict], format: str) -> str | bytes:
    columns = list(dict.fromkeys(key for row in rows for key in row))
    if format == "csv":
        buffer = StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerow(columns)
        writer.writerows([_text(row.get(key)) for key in columns] for row in rows)
        return "\ufeff" + buffer.getvalue()
    from openpyxl import Workbook
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Rapor"
    sheet.append(columns)
    for row in rows:
        sheet.append([_text(row.get(key)) for key in columns])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
