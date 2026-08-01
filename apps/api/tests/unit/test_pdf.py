import os
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime
from app.core.pdf import generate_order_receipt_pdf, STATIC_RECEIPTS_DIR


def test_generate_order_receipt_pdf():
    # Mock business, order, items, customer
    business = SimpleNamespace(
        name="Test Bakery & Cafe",
        phone_number="+919876543210",
        address="123 Anna Salai, Chennai",
        location="Chennai"
    )

    order = SimpleNamespace(
        id="test-uuid-12345",
        order_number=101,
        created_at=datetime.now(),
        delivery_location="45 Beach Road, Chennai",
        total_amount=250.0
    )

    items = [
        SimpleNamespace(name="Chocolate Muffin", quantity=2, unit_price=75.0, total_price=150.0),
        SimpleNamespace(name="Cold Coffee", quantity=1, unit_price=100.0, total_price=100.0),
    ]

    customer = SimpleNamespace(
        name="Ramesh Kumar",
        phone_number="+919123456789"
    )

    filename = generate_order_receipt_pdf(order=order, items=items, business=business, customer=customer)
    assert filename == f"receipt_order_{order.id}.pdf"

    pdf_path = STATIC_RECEIPTS_DIR / filename
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0

    # Clean up test file
    if pdf_path.exists():
        pdf_path.unlink()
