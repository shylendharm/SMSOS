import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.models.business import Business


@pytest.mark.asyncio
async def test_twilio_webhook_endpoint(db_session):
    # Ensure active business exists
    business = Business(
        name="Test Store",
        business_type="retail",
        phone_number="+14155238886",
        is_active=True,
    )
    db_session.add(business)
    await db_session.commit()

    # Send Twilio form payload
    payload = {
        "MessageSid": f"SM{uuid.uuid4().hex[:12]}",
        "From": "whatsapp:+19998887777",
        "To": "whatsapp:+14155238886",
        "Body": "Vanakkam, 2 coffee venum",
        "ProfileName": "Karthik",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/webhooks/twilio",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == 200
        assert "<Response>" in response.text


@pytest.mark.asyncio
async def test_auto_substitution_message(db_session):
    from unittest.mock import AsyncMock, patch
    from app.core.ai import IntentResult, OrderItemEntity
    from app.modules.messaging import process_inbound_sms_pipeline
    from app.db.models.catalog import CatalogItem
    from app.db.models.business import BusinessSettings

    # 1. Reuse or Create Business
    from sqlalchemy import select
    res_biz = await db_session.execute(select(Business).where(Business.phone_number == "+14155238886"))
    business = res_biz.scalars().first()
    if not business:
        business = Business(
            name="Shylu's Cafe",
            business_type="restaurant",
            phone_number="+14155238886",
            is_active=True,
        )
        db_session.add(business)
        await db_session.flush()

        b_settings = BusinessSettings(
            business_id=business.id,
            table_count=10,
        )
        db_session.add(b_settings)

    # 2. Add Out of Stock Item (Masala Dosa) & In Stock Alternative (Pongal)
    dosa = CatalogItem(
        business_id=business.id,
        name="Masala Dosa",
        price=110.0,
        category="Breakfast",
        is_available=False,
    )
    pongal = CatalogItem(
        business_id=business.id,
        name="Pongal",
        price=100.0,
        category="Breakfast",
        is_available=True,
    )
    db_session.add(dosa)
    db_session.add(pongal)
    await db_session.commit()

    # 3. Mock AI extraction for Masala Dosa
    mock_ai_result = IntentResult(
        intent="PLACE_ORDER",
        confidence=0.95,
        language="english",
        items=[OrderItemEntity(item_name="Masala Dosa", quantity=1)],
        delivery_location=None,
        is_order_confirmed=False,
        reply_text="User wants Masala Dosa"
    )

    payload = {
        "MessageSid": f"SM{uuid.uuid4().hex[:12]}",
        "From": "whatsapp:+19998887777",
        "To": "whatsapp:+14155238886",
        "Body": "I want to order Masala Dosa",
        "ProfileName": "Karthik",
    }

    with patch("app.core.ai.gemini_service.process_customer_message", new_callable=AsyncMock) as mock_process:
        mock_process.return_value = mock_ai_result
        
        result = await process_inbound_sms_pipeline(db_session, payload)
        
        # 4. Assert response was handled and includes the suggestion warning
        assert result["status"] == "success"
        response_body = result["reply"]
        
        # Verify that out of stock warning and suggestion are in response
        assert "*Out of Stock*" in response_body
        assert "Masala Dosa" in response_body
        assert "Instead of *Masala Dosa*" in response_body
        assert "Pongal" in response_body

