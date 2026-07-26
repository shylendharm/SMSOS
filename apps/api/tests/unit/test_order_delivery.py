import pytest
from app.core.ai import IntentResult, OrderItemEntity


def test_intent_result_delivery_fields():
    res = IntentResult(
        intent="PLACE_ORDER",
        confidence=0.95,
        language="english",
        items=[OrderItemEntity(item_name="Biryani", quantity=2)],
        delivery_location="Hostel 3 Gate",
        is_order_confirmed=True,
        reply_text="Order summary: 2 Biryani to Hostel 3 Gate."
    )
    
    entities = res.entities
    assert entities["delivery_location"] == "Hostel 3 Gate"
    assert entities["is_order_confirmed"] is True
    assert len(entities["items"]) == 1
    assert entities["items"][0]["item_name"] == "Biryani"
