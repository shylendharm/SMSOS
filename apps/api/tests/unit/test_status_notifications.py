"""
Unit tests for automated customer status update notifications.
Tests that order and reservation status changes produce correct notification messages.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# ─── Order Notification Message Formatting Tests ───

def _build_order_status_msg(status: str, order_number: int, delivery_location: str = "IMa Hostel") -> str:
    """Replicate the order status message logic from orders.py."""
    st_lower = status.lower()
    if st_lower in ["in_preparation", "preparing"]:
        return f"👨‍🍳 Your order #{order_number} is now being prepared in the kitchen!"
    elif st_lower in ["out_for_delivery", "ready"]:
        return f"🛵 Your order #{order_number} is out for delivery! Driver is on the way to {delivery_location}."
    elif st_lower in ["delivered", "completed"]:
        return f"📦 Your order #{order_number} has been delivered at {delivery_location}. Enjoy your meal!"
    elif st_lower == "cancelled":
        return f"❌ Your order #{order_number} has been cancelled."
    else:
        return f"Your order #{order_number} status updated to: {status.upper()}."


def test_order_preparing_message():
    msg = _build_order_status_msg("preparing", 5)
    assert "👨‍🍳" in msg
    assert "#5" in msg
    assert "kitchen" in msg


def test_order_out_for_delivery_message():
    msg = _build_order_status_msg("out_for_delivery", 7, "Tinnanur")
    assert "🛵" in msg
    assert "#7" in msg
    assert "Tinnanur" in msg


def test_order_delivered_message():
    msg = _build_order_status_msg("delivered", 3, "Venpa Block")
    assert "📦" in msg
    assert "#3" in msg
    assert "Venpa Block" in msg


def test_order_cancelled_message():
    msg = _build_order_status_msg("cancelled", 10)
    assert "❌" in msg
    assert "#10" in msg


def test_order_unknown_status_message():
    msg = _build_order_status_msg("on_hold", 2)
    assert "ON_HOLD" in msg
    assert "#2" in msg


# ─── Reservation Notification Message Formatting Tests ───

def _build_reservation_status_msg(
    status: str,
    party_size: int = 4,
    reserved_at: datetime = None,
    table_or_slot: str = "Table 3",
) -> str:
    """Replicate the reservation status message logic from reservations.py."""
    if reserved_at is None:
        reserved_at = datetime(2026, 8, 1, 19, 0, tzinfo=timezone.utc)

    try:
        date_str = reserved_at.strftime("%d %b %Y")
        time_str = reserved_at.strftime("%I:%M %p").lstrip("0")
    except Exception:
        date_str = str(reserved_at)
        time_str = ""

    table_str = table_or_slot or "your table"
    party_str = f"{party_size} guest{'s' if party_size != 1 else ''}"

    st_lower = status.lower()
    if st_lower == "confirmed":
        return (
            f"🎉 Your reservation for {party_str} on {date_str} at {time_str} "
            f"({table_str}) has been CONFIRMED by the venue!"
        )
    elif st_lower == "seated":
        return f"🍽️ Welcome! You are now seated at {table_str}. Enjoy your meal!"
    elif st_lower == "cancelled":
        return f"❌ Your reservation for {date_str} at {time_str} has been CANCELLED."
    elif st_lower == "completed":
        return f"✨ Thank you for dining with us! Your reservation on {date_str} is completed. We hope to see you again!"
    elif st_lower == "no_show":
        return f"⚠️ Your reservation for {date_str} at {time_str} has been marked as No-Show."
    else:
        return f"Your reservation status has been updated to: {status.upper()}."


def test_reservation_confirmed_message():
    msg = _build_reservation_status_msg("confirmed", party_size=4, table_or_slot="Table 3")
    assert "🎉" in msg
    assert "4 guests" in msg
    assert "Table 3" in msg
    assert "CONFIRMED" in msg


def test_reservation_confirmed_single_guest():
    msg = _build_reservation_status_msg("confirmed", party_size=1)
    assert "1 guest" in msg
    assert "guests" not in msg


def test_reservation_seated_message():
    msg = _build_reservation_status_msg("seated", table_or_slot="Table 5")
    assert "🍽️" in msg
    assert "Table 5" in msg


def test_reservation_cancelled_message():
    msg = _build_reservation_status_msg("cancelled")
    assert "❌" in msg
    assert "CANCELLED" in msg


def test_reservation_completed_message():
    msg = _build_reservation_status_msg("completed")
    assert "✨" in msg
    assert "completed" in msg


def test_reservation_no_show_message():
    msg = _build_reservation_status_msg("no_show")
    assert "⚠️" in msg
    assert "No-Show" in msg
