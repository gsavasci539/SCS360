from io import BytesIO

from openpyxl import load_workbook

from app.infrastructure.reports.tabular_export import export_rows


def test_export_preserves_values_and_prevents_formula_execution():
    rows = [{"student": "=HYPERLINK(1)", "amount": 120.50}, {"student": "Ayşe", "amount": 0}]
    csv = export_rows(rows, "csv")
    assert "'=HYPERLINK(1)" in csv
    assert "Ayşe,0" in csv
    workbook = load_workbook(BytesIO(export_rows(rows, "excel")))
    assert workbook.active["A2"].data_type != "f"
    assert workbook.active["B2"].value == 120.50
    assert workbook.active["A3"].value == "Ayşe"
