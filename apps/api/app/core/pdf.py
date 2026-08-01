from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import structlog

logger = structlog.get_logger()

# Ensure receipts directory exists
STATIC_RECEIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "receipts"
STATIC_RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)


def generate_order_receipt_pdf(
    order: Any,
    items: List[Any],
    business: Any,
    customer: Optional[Any] = None
) -> str:
    """
    Generates a clean PDF receipt for an order and returns the relative filename (e.g., 'receipt_order_123.pdf').
    """
    filename = f"receipt_order_{order.id}.pdf"
    filepath = STATIC_RECEIPTS_DIR / filename

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1e293b")
    )

    h2_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0f172a")
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155")
    )

    bold_body_style = ParagraphStyle(
        'BodyBoldCustom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#0f172a")
    )

    footer_style = ParagraphStyle(
        'FooterText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=12,
        alignment=1, # Center
        textColor=colors.HexColor("#64748b")
    )

    elements = []

    # 1. Header: Shop Name + Phone + Location
    biz_name = getattr(business, 'name', 'SMSOS Merchant')
    biz_phone = getattr(business, 'phone_number', '') or ''
    biz_location = getattr(business, 'address', '') or getattr(business, 'location', '') or 'Main Branch'

    header_text = f"<b>{biz_name}</b><br/>"
    if biz_phone:
        header_text += f"Phone: {biz_phone}<br/>"
    if biz_location:
        header_text += f"Address: {biz_location}"

    elements.append(Paragraph(header_text, title_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=15))

    # 2. Order Metadata & Delivery Location
    order_num = getattr(order, 'order_number', f"#{order.id}")
    created_at = getattr(order, 'created_at', datetime.now())
    date_str = created_at.strftime("%d %b %Y, %I:%M %p") if isinstance(created_at, datetime) else str(created_at)
    delivery_loc = getattr(order, 'delivery_location', '') or getattr(order, 'delivery_address', '') or 'Customer Address'
    cust_name = getattr(customer, 'name', 'Valued Customer') if customer else 'Valued Customer'
    cust_phone = getattr(customer, 'phone_number', '') if customer else ''

    meta_left = f"<b>Order #:</b> {order_num}<br/><b>Date:</b> {date_str}<br/><b>Customer:</b> {cust_name}"
    if cust_phone:
        meta_left += f" ({cust_phone})"

    meta_right = f"<b>Delivery Location:</b><br/>{delivery_loc}"

    meta_table_data = [
        [Paragraph(meta_left, body_style), Paragraph(meta_right, body_style)]
    ]
    meta_table = Table(meta_table_data, colWidths=[3.5 * inch, 3.5 * inch])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 15))

    # 3. Itemized Line Items Table
    elements.append(Paragraph("<b>Itemized Bill</b>", h2_style))
    elements.append(Spacer(1, 8))

    table_data = [
        [
            Paragraph("<b>Item</b>", bold_body_style),
            Paragraph("<b>Qty</b>", bold_body_style),
            Paragraph("<b>Unit Price</b>", bold_body_style),
            Paragraph("<b>Line Total</b>", bold_body_style),
        ]
    ]

    subtotal = 0.0
    for item in items:
        name = getattr(item, 'item_name', '') or getattr(item, 'name', 'Item')
        qty = getattr(item, 'quantity', 1)
        unit_price = float(getattr(item, 'unit_price', 0.0) or getattr(item, 'price', 0.0))
        line_total = float(getattr(item, 'total_price', qty * unit_price) or (qty * unit_price))
        subtotal += line_total

        table_data.append([
            Paragraph(name, body_style),
            Paragraph(str(qty), body_style),
            Paragraph(f"INR {unit_price:.2f}", body_style),
            Paragraph(f"INR {line_total:.2f}", body_style),
        ])

    items_table = Table(table_data, colWidths=[3.5 * inch, 1.0 * inch, 1.25 * inch, 1.25 * inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor("#cbd5e1")),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 15))

    # 4. Totals & Payment Status
    total_amount = float(getattr(order, 'total_amount', subtotal) or subtotal)
    
    summary_data = [
        [Paragraph("Subtotal:", body_style), Paragraph(f"INR {subtotal:.2f}", body_style)],
        [Paragraph("<b>Total Amount:</b>", bold_body_style), Paragraph(f"<b>INR {total_amount:.2f}</b>", bold_body_style)],
        [Paragraph("<b>Payment Status:</b>", bold_body_style), Paragraph(f"<font color='#16a34a'><b>Paid on Delivery / Amount: INR {total_amount:.2f}</b></font>", body_style)]
    ]
    summary_table = Table(summary_data, colWidths=[4.75 * inch, 2.25 * inch])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 25))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=15))

    # 5. Footer
    footer_text = f"Thank you! Powered by <b>SMSOS</b><br/>Shop Contact: {biz_name} ({biz_phone})"
    elements.append(Paragraph(footer_text, footer_style))

    doc.build(elements)
    logger.info("Generated PDF receipt", order_id=order.id, filename=filename, filepath=str(filepath))
    return filename
