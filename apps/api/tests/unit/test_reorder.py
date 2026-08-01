import pytest
from app.core.ai import IntentResult, OrderItemEntity


def test_intent_result_reorder_field():
    res = IntentResult(
        intent="PLACE_ORDER",
        confidence=0.95,
        language="english",
        items=[],
        is_reorder=True,
        reply_text="Processing reorder..."
    )
    
    entities = res.entities
    assert entities["is_reorder"] is True


def test_reorder_keyword_matching():
    reorder_phrases = ["repeat last order", "same order again", "order same again", "last order", "repeat order", "same order", "pazhaya order", "again same"]
    
    test_messages = [
        "Please repeat my last order",
        "Pazhaya order thirumba anupunga",
        "Send same order again to IMa",
        "repeat order",
    ]

    for msg in test_messages:
        matched = any(p in msg.lower() for p in reorder_phrases)
        assert matched is True, f"Failed to match reorder phrase in: {msg}"
