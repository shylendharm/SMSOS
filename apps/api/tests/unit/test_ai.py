import pytest
from app.core.ai import GeminiAIService, IntentResult


@pytest.mark.asyncio
async def test_fallback_response():
    ai = GeminiAIService(api_key=None)
    
    # Test ordering intent fallback
    res1 = await ai.process_customer_message("I want to buy 2 coffees")
    assert res1.intent == "PLACE_ORDER"
    assert "Thank you" in res1.reply_text

    # Test reservation intent fallback
    res2 = await ai.process_customer_message("Can I book a table for 4?")
    assert res2.intent == "RESERVATION"

    # Test general inquiry fallback
    res3 = await ai.process_customer_message("What time do you open?")
    assert res3.intent == "INQUIRY"
