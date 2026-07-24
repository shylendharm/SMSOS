from typing import Annotated
import structlog
from fastapi import APIRouter, Depends, Request, Form, Response, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.sms import twilio_service
from app.modules.messaging import process_inbound_sms_pipeline

logger = structlog.get_logger()
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/twilio")
async def twilio_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Twilio Webhook Endpoint for incoming SMS/WhatsApp messages.
    Supports application/x-www-form-urlencoded from Twilio.
    """
    form_data = await request.form()
    payload = dict(form_data)

    logger.info("Received Twilio Webhook payload", from_number=payload.get("From"), message_sid=payload.get("MessageSid"))

    # Optional signature verification
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    if signature and not twilio_service.verify_webhook_signature(url, payload, signature):
        logger.warning("Twilio signature validation failed")
        # In strict prod, raise 403; for dev sandbox, log warning and proceed

    try:
        result = await process_inbound_sms_pipeline(db, payload)
        # Return TwiML empty response or JSON
        return Response(content="<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response></Response>", media_type="application/xml")
    except Exception as e:
        logger.error("Error processing Twilio webhook", error=str(e))
        return Response(content="<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response></Response>", media_type="application/xml")
