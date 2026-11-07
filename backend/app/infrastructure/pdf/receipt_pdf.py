from io import BytesIO
from pathlib import Path
from functools import lru_cache

import reportlab
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

LOGO_PATH = Path(__file__).resolve().parent / "assets" / "scs360-mark.png"


@lru_cache(maxsize=1)
def register_receipt_fonts():
    fonts = Path(reportlab.__file__).resolve().parent / "fonts"
    for name, filename in (("SCS360-Regular", "Vera.ttf"), ("SCS360-Bold", "VeraBd.ttf"), ("SCS360-Italic", "VeraIt.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(fonts / filename)))


def draw_receipt(c, data: dict, x: float, y: float, width: float, height: float, copy_type: str):
    """Draw a single receipt on the canvas at specified position"""
    register_receipt_fonts()
    
    # Background
    c.setFillColor(colors.white)
    c.rect(x, y, width, height, fill=1, stroke=1)
    
    # Header background
    c.setFillColor(colors.HexColor("#edf3ef"))
    c.rect(x, y + height - 22 * mm, width, 22 * mm, fill=1, stroke=0)
    
    # Product identity and the institution's legal name remain separate.
    c.drawImage(str(LOGO_PATH), x + 5 * mm, y + height - 17 * mm, width=12 * mm, height=12 * mm, mask="auto")
    c.setFillColor(colors.HexColor("#163b3b"))
    c.setFont("SCS360-Bold", 8)
    c.drawString(x + 21 * mm, y + height - 8 * mm, "SCS360")
    c.setFont("SCS360-Bold", 12)
    c.drawString(x + 21 * mm, y + height - 15 * mm, data.get("organization_name", "Okul Yönetim Sistemi"))
    
    # Copy type indicator
    c.setFont("SCS360-Bold", 9)
    c.setFillColor(colors.darkgrey)
    if copy_type == "parent":
        c.drawRightString(x + width - 5 * mm, y + height - 15 * mm, "VELİ KOPYASI")
    else:
        c.drawRightString(x + width - 5 * mm, y + height - 15 * mm, "YÖNETİM KOPYASI")
    
    # Receipt number and date
    current_y = y + height - 30 * mm
    c.setFillColor(colors.black)
    c.setFont("SCS360-Bold", 11)
    cancelled = data.get("status") == "CANCELLED"
    if cancelled:
        c.setFillColor(colors.HexColor("#b42318"))
    c.drawString(x + 5 * mm, current_y, "İPTAL EDİLMİŞ MAKBUZ" if cancelled else "TAHSİLAT MAKBUZU")
    c.setFillColor(colors.black)
    
    current_y -= 7 * mm
    c.setFont("SCS360-Regular", 8)
    c.drawString(x + 5 * mm, current_y, f"Makbuz No: {data.get('receipt_number', '')}")
    c.drawString(x + width - 30 * mm, current_y, f"Tarih: {data.get('issued_at', '')}")
    
    # Divider line
    current_y -= 4 * mm
    c.setLineWidth(0.5)
    c.line(x + 5 * mm, current_y, x + width - 5 * mm, current_y)
    
    # Receipt details
    current_y -= 8 * mm
    c.setFont("SCS360-Regular", 8)
    
    details = [
        ("Şube:", data.get('branch_name', '')),
        ("Öğrenci:", data.get('student_name', '')),
    ]
    
    # Add student number if available
    if data.get('student_number'):
        details.append(("Öğrenci No:", data.get('student_number', '')))
    
    # Add parent if available
    if data.get('parent_name'):
        details.append(("Veli:", data.get('parent_name', '')))
    
    details.extend([
        ("Ödeme Tutarı:", f"{data.get('amount', '0')} TL"),
        ("Ödeme Yöntemi:", data.get('payment_method', '')),
    ])
    
    # Add remaining debt if > 0
    remaining_debt = data.get('remaining_debt', '0')
    try:
        if float(remaining_debt) > 0:
            details.append(("Kalan Borç:", f"{remaining_debt} TL"))
    except (ValueError, TypeError):
        pass
    
    # Add received by if available
    if data.get('received_by'):
        details.append(("Tahsilatı Alan:", data.get('received_by', '')))
    
    for label, value in details:
        c.setFont("SCS360-Bold", 8)
        c.drawString(x + 5 * mm, current_y, label)
        c.setFont("SCS360-Regular", 8)
        c.drawString(x + 34 * mm, current_y, str(value))
        current_y -= 5 * mm
    
    # Footer
    current_y = y + 12 * mm
    c.setLineWidth(0.3)
    c.line(x + 5 * mm, current_y, x + width - 5 * mm, current_y)
    
    current_y -= 4 * mm
    c.setFont("SCS360-Italic", 7)
    c.setFillColor(colors.darkgrey)
    c.drawString(x + 5 * mm, current_y, "Bu belge SCS360 üzerinden oluşturulmuştur.")
    
    # Signature area
    if copy_type == "management":
        current_y = y + 20 * mm
        c.setFont("SCS360-Regular", 7)
        c.setFillColor(colors.black)
        c.drawString(x + 5 * mm, current_y, "İmza:")
        c.line(x + 12 * mm, current_y - 2 * mm, x + 40 * mm, current_y - 2 * mm)


def generate_receipt_pdf(data: dict) -> bytes:
    """Generate A4 PDF with 2 A5 receipts stacked vertically (parent copy and management copy)"""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # A5 dimensions (half of A4 height)
    a5_width = width
    a5_height = height / 2
    
    # Draw parent copy on top
    draw_receipt(c, data, 0, a5_height, a5_width, a5_height, "parent")
    
    # Draw management copy on bottom
    draw_receipt(c, data, 0, 0, a5_width, a5_height, "management")
    
    # Horizontal divider line
    c.setLineWidth(1)
    c.setDash([5, 5])
    c.line(10 * mm, a5_height, width - 10 * mm, a5_height)
    c.setDash([])
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()
