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
