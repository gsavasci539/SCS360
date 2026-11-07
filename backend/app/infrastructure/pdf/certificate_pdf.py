from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import KeepInFrame, Paragraph, Spacer

from app.infrastructure.pdf.receipt_pdf import LOGO_PATH, register_receipt_fonts


def generate_certificate_pdf(data: dict) -> bytes:
    register_receipt_fonts()
    width, height = landscape(A4)
    stream = BytesIO()
    page = canvas.Canvas(stream, pagesize=(width, height))
    page.setTitle("SCS360 - Öğrenci belgesi")
    page.setAuthor("SCS360")
    ink, accent, gold = colors.HexColor("#163b3b"), colors.HexColor("#176b5b"), colors.HexColor("#d4a65f")
    page.setFillColor(colors.HexColor("#fffdf7"))
    page.rect(0, 0, width, height, fill=1, stroke=0)
    page.setStrokeColor(ink)
    page.setLineWidth(2)
    page.rect(25, 25, width - 50, height - 50)
    page.setStrokeColor(gold)
    page.setLineWidth(0.8)
    page.rect(33, 33, width - 66, height - 66)
    page.drawImage(str(LOGO_PATH), width / 2 - 24, height - 98, width=48, height=48, mask="auto")
    page.setFillColor(ink)
    page.setFont("SCS360-Bold", 11)
    page.drawCentredString(width / 2, height - 116, "SCS360")
    text_width = width - 140
    styles = {
        "school": ParagraphStyle("school", fontName="SCS360-Bold", fontSize=11 if len(data.get("organization_name", "")) > 120 else 14, leading=18, alignment=TA_CENTER, textColor=ink),
        "title": ParagraphStyle("title", fontName="SCS360-Bold", fontSize=18 if len(data.get("title", "")) > 120 else 24, leading=27, alignment=TA_CENTER, textColor=accent),
        "name": ParagraphStyle("name", fontName="SCS360-Bold", fontSize=20 if len(data.get("student_name", "")) > 70 else 27, leading=31, alignment=TA_CENTER, textColor=ink),
        "body": ParagraphStyle("body", fontName="SCS360-Regular", fontSize=10 if len(data.get("description", "")) > 700 else 11, leading=16, alignment=TA_CENTER, textColor=ink),
        "issuer": ParagraphStyle("issuer", fontName="SCS360-Regular", fontSize=8 if len(data.get("issuer_name", "")) > 80 else 9, leading=11, alignment=TA_CENTER, textColor=ink),
    }
    paragraph = lambda text, style: Paragraph(escape(str(text or "")).replace("\n", "<br/>"), styles[style])
    content = [paragraph(data.get("organization_name"), "school"), Spacer(1, 15),
        paragraph(data.get("title"), "title"), Spacer(1, 20),
        paragraph(data.get("student_name"), "name"), Spacer(1, 18)]
    if data.get("description"):
        content.append(paragraph(data["description"], "body"))
    if data.get("branch_name"):
        content.extend([Spacer(1, 13), paragraph(data["branch_name"], "body")])
    frame = KeepInFrame(text_width, height - 265, content, mode="shrink", hAlign="CENTER", vAlign="TOP")
    _, used_height = frame.wrapOn(page, text_width, height - 265)
    frame.drawOn(page, 70, height - 140 - used_height)
    page.setStrokeColor(gold)
    page.line(65, 105, width - 65, 105)
    page.setFillColor(ink)
    page.setFont("SCS360-Regular", 9)
    page.drawString(65, 85, f"Düzenlenme tarihi: {data.get('issue_date', '')}")
    reference = str(data.get("id", "")).replace("-", "")[:12].upper()
    page.drawString(65, 68, f"Belge no: {reference}")
    issuer = KeepInFrame(300, 34, [paragraph(data.get("issuer_name"), "issuer")], mode="shrink", hAlign="CENTER")
    issuer.wrapOn(page, 300, 34)
    issuer.drawOn(page, width - 365, 50)
    page.setFont("SCS360-Regular", 8)
    page.drawCentredString(width - 215, 92, "Düzenleyen")
    page.showPage()
    page.save()
    return stream.getvalue()
