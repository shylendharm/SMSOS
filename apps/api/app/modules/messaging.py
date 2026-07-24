import uuid
from decimal import Decimal
from typing import Dict, Any, Optional
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.ai import gemini_service
from app.core.sms import twilio_service
from app.db.models.business import Business
from app.db.models.customer import Customer
from app.db.models.catalog import CatalogItem
from app.db.models.order import Order, OrderItem
from app.db.models.reservation import Reservation
from app.db.models.message import InboundMessage, OutboundMessage
from app.db.models.conversation import ConversationState
from app.db.models.webhook import WebhookEvent, IntentPrediction

logger = structlog.get_logger()


async def process_inbound_sms_pipeline(
    db: AsyncSession,
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Main orchestration function for processing an incoming SMS/WhatsApp message.
    """
    message_sid = payload.get("MessageSid", f"MS_GEN_{uuid.uuid4().hex[:12]}")
    from_number = payload.get("From", "")
    to_number = payload.get("To", "")
    body = payload.get("Body", "").strip()

    if not body:
        logger.warning("Received empty message body", from_number=from_number)
        return {"status": "skipped", "reason": "empty body"}

    # 1. Save raw Webhook Event
    event = WebhookEvent(
        event_id=message_sid,
        event_type="twilio.inbound_message",
        payload=payload,
        processed=False,
    )
    db.add(event)
    await db.flush()

    # 2. Get Business (match by to_number or get default business)
    clean_to = to_number.replace("whatsapp:", "")
    result = await db.execute(select(Business).where(Business.is_active == True))
    businesses = result.scalars().all()
    
    business = None
    for b in businesses:
        if b.phone_number == clean_to:
            business = b
            break
    if not business and businesses:
        business = businesses[0]

    if not business:
        logger.error("No active business found to handle incoming message")
        event.processed = True
        event.processing_result = {"error": "No business available"}
        await db.commit()
        return {"status": "error", "reason": "no business"}

    # 3. Get or Create Customer
    clean_from = from_number.replace("whatsapp:", "")
    res = await db.execute(
        select(Customer).where(
            Customer.business_id == business.id,
            Customer.phone_number == clean_from,
        )
    )
    customer = res.scalars().first()

    if not customer:
        customer = Customer(
            business_id=business.id,
            phone_number=clean_from,
            name=payload.get("ProfileName", f"Customer {clean_from[-4:]}"),
            metadata_json={"whatsapp": from_number.startswith("whatsapp:")},
        )
        db.add(customer)
        await db.flush()

    # 4. Create InboundMessage DB Record
    inbound_msg = InboundMessage(
        business_id=business.id,
        message_sid=message_sid,
        from_number=from_number,
        to_number=to_number,
        body=body,
        raw_payload=payload,
        processed=False,
    )
    db.add(inbound_msg)
    await db.flush()

    # 5. Fetch Catalog context for AI
    cat_res = await db.execute(
        select(CatalogItem).where(
            CatalogItem.business_id == business.id,
            CatalogItem.is_available == True,
        )
    )
    catalog_items = cat_res.scalars().all()
    catalog_context = [
        {
            "id": str(item.id),
            "name": item.name,
            "price": float(item.price),
            "category": item.category,
            "description": item.description or "",
        }
        for item in catalog_items
    ]

    # 6. Fetch or Create Conversation State
    conv_res = await db.execute(
        select(ConversationState).where(
            ConversationState.business_id == business.id,
            ConversationState.from_number == from_number,
        )
    )
    conv_state = conv_res.scalars().first()

    if not conv_state:
        conv_state = ConversationState(
            business_id=business.id,
            customer_id=customer.id,
            from_number=from_number,
            state="IDLE",
            context={"messages": []},
        )
        db.add(conv_state)
        await db.flush()

    history = (conv_state.context or {}).get("messages", [])[-5:]

    # 7. Execute AI Processing with Gemini
    ai_result = await gemini_service.process_customer_message(
        message_text=body,
        catalog_context=catalog_context,
        conversation_history=history,
        business_name=business.name,
    )

    # 8. Record Intent Prediction
    prediction = IntentPrediction(
        message_id=inbound_msg.id,
        intent=ai_result.intent,
        confidence=ai_result.confidence,
        entities=ai_result.entities,
        candidate_intents={"detected_language": ai_result.language},
    )
    db.add(prediction)

    # 9. Execute domain actions based on intent
    response_text = ai_result.reply_text

    if ai_result.intent == "PLACE_ORDER":
        # Create an Order draft
        order = Order(
            business_id=business.id,
            customer_id=customer.id,
            order_number=f"ORD-{uuid.uuid4().hex[:6].upper()}",
            status="pending",
            total_amount=Decimal("0.00"),
            channel="whatsapp" if from_number.startswith("whatsapp:") else "sms",
            notes=f"AI parsed order from: '{body}'",
        )
        db.add(order)
        await db.flush()

        total = Decimal("0.00")
        items_extracted = ai_result.entities.get("items", [])
        if isinstance(items_extracted, list):
            for itm in items_extracted:
                item_name = itm.get("item_name", "Item") if isinstance(itm, dict) else str(itm)
                qty = int(itm.get("quantity", 1)) if isinstance(itm, dict) else 1

                # Match item in catalog
                matched_catalog = None
                for c_item in catalog_items:
                    if c_item.name.lower() in item_name.lower():
                        matched_catalog = c_item
                        break

                price = matched_catalog.price if matched_catalog else Decimal("10.00")
                line_total = price * qty
                total += line_total

                order_item = OrderItem(
                    order_id=order.id,
                    catalog_item_id=matched_catalog.id if matched_catalog else None,
                    item_name=item_name,
                    unit_price=price,
                    quantity=qty,
                    total_price=line_total,
                )
                db.add(order_item)

        order.total_amount = total
        conv_state.state = "ORDER_PENDING"

    elif ai_result.intent == "RESERVATION":
        reservation = Reservation(
            business_id=business.id,
            customer_id=customer.id,
            party_size=int(ai_result.entities.get("party_size", 2)),
            status="confirmed",
            notes=f"AI parsed reservation from: '{body}'",
        )
        db.add(reservation)
        conv_state.state = "RESERVATION_CONFIRMED"

    # Update conversation state context
    updated_history = history + [
        {"role": "user", "content": body},
        {"role": "assistant", "content": response_text},
    ]
    conv_state.context = {"messages": updated_history, "last_intent": ai_result.intent}

    # 10. Send Outbound SMS/WhatsApp via Twilio
    twilio_sid = twilio_service.send_message(to_number=from_number, body=response_text)

    # 11. Save Outbound Message record
    outbound_msg = OutboundMessage(
        business_id=business.id,
        to_number=from_number,
        body=response_text,
        message_sid=twilio_sid,
        status="sent" if twilio_sid else "failed",
        correlation_id=inbound_msg.id,
    )
    db.add(outbound_msg)

    # 12. Mark Inbound & Webhook as processed
    inbound_msg.processed = True
    inbound_msg.correlation_id = outbound_msg.id
    event.processed = True
    event.processing_result = {
        "intent": ai_result.intent,
        "outbound_sid": twilio_sid,
    }

    await db.commit()

    logger.info(
        "Processed inbound message pipeline successfully",
        intent=ai_result.intent,
        to=from_number,
        response_sid=twilio_sid,
    )

    return {
        "status": "success",
        "intent": ai_result.intent,
        "reply": response_text,
        "twilio_sid": twilio_sid,
    }
