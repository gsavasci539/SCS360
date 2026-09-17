from typing import Optional, Dict, Any
from datetime import datetime
from io import BytesIO
import os

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class PDFService:
    """Service for generating PDF documents"""
    
    def __init__(self):
        self.available = REPORTLAB_AVAILABLE
        
    def generate_receipt(
        self,
        receipt_data: Dict[str, Any],
        organization_data: Dict[str, Any]
    ) -> Optional[bytes]:
        """Generate receipt PDF"""
        if not self.available:
            return None
            
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center
        )
        elements.append(Paragraph("MAKBUZ", title_style))
        
        # Organization info
        org_style = ParagraphStyle(
            'OrgInfo',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=10
        )
        elements.append(Paragraph(f"{organization_data.get('name', '')}", org_style))
        elements.append(Paragraph(f"{organization_data.get('address', '')}", org_style))
        elements.append(Paragraph(f"{organization_data.get('phone', '')}", org_style))
        elements.append(Spacer(1, 20))
        
        # Receipt details table
        data = [
            ["Fiş No:", receipt_data.get('receipt_number', '')],
            ["Tarih:", receipt_data.get('payment_date', '').strftime('%d.%m.%Y') if receipt_data.get('payment_date') else ''],
            ["Öğrenci:", receipt_data.get('student_name', '')],
            ["Tutar:", f"{receipt_data.get('amount', 0):.2f} TL"],
            ["Ödeme Yöntemi:", receipt_data.get('payment_method', '')],
        ]
        
        table = Table(data, colWidths=[2*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_invoice(
        self,
        invoice_data: Dict[str, Any],
        organization_data: Dict[str, Any]
    ) -> Optional[bytes]:
        """Generate invoice PDF"""
        if not self.available:
            return None
            
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1
        )
        elements.append(Paragraph("FATURA", title_style))
        
        # Organization info
        org_style = ParagraphStyle(
            'OrgInfo',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=10
        )
        elements.append(Paragraph(f"{organization_data.get('name', '')}", org_style))
        elements.append(Paragraph(f"Vergi No: {organization_data.get('tax_number', '')}", org_style))
        elements.append(Paragraph(f"Vergi Dairesi: {organization_data.get('tax_office', '')}", org_style))
        elements.append(Spacer(1, 20))
        
        # Invoice details
        data = [
            ["Fatura No:", invoice_data.get('invoice_number', '')],
            ["Tarih:", invoice_data.get('date', '').strftime('%d.%m.%Y') if invoice_data.get('date') else ''],
            ["Veli:", invoice_data.get('parent_name', '')],
            ["Öğrenci:", invoice_data.get('student_name', '')],
        ]
        
        table = Table(data, colWidths=[2*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
        
        # Items table
        if invoice_data.get('items'):
            elements.append(Spacer(1, 20))
            item_data = [["Açıklama", "Tutar"]]
            for item in invoice_data['items']:
                item_data.append([item.get('description', ''), f"{item.get('amount', 0):.2f} TL"])
            
            item_table = Table(item_data, colWidths=[3*inch, 2*inch])
            item_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(item_table)
            
            # Total
            elements.append(Spacer(1, 20))
            total = sum(item.get('amount', 0) for item in invoice_data['items'])
            elements.append(Paragraph(f"TOPLAM: {total:.2f} TL", styles['Heading2']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_attendance_report(
        self,
        report_data: Dict[str, Any],
        organization_data: Dict[str, Any]
    ) -> Optional[bytes]:
        """Generate attendance report PDF"""
        if not self.available:
            return None
            
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1
        )
        elements.append(Paragraph("YOKLAMA RAPORU", title_style))
        
        # Report info
        info_style = ParagraphStyle(
            'Info',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=10
        )
        elements.append(Paragraph(f"Sınıf: {report_data.get('class_name', '')}", info_style))
        elements.append(Paragraph(f"Tarih: {report_data.get('date', '').strftime('%d.%m.%Y') if report_data.get('date') else ''}", info_style))
        elements.append(Spacer(1, 20))
        
        # Attendance table
        if report_data.get('students'):
            data = [["Öğrenci", "Durum"]]
            for student in report_data['students']:
                data.append([student.get('name', ''), student.get('status', '')])
            
            table = Table(data, colWidths=[3*inch, 2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
