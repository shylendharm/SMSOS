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
    result = await db.execute(
        select(Business).where(
            Business.is_active == True,
            Business.name != "Session Lifecycle Test"
        )
    )
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

    # Fetch customer's recent orders for status context
    from sqlalchemy.orm import selectinload
    orders_query = await db.execute(
        select(Order)
        .where(Order.customer_id == customer.id, Order.business_id == business.id)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .limit(3)
    )
    recent_orders = orders_query.scalars().all()
    
    order_context = []
    for o in recent_orders:
        order_context.append({
            "order_number": o.order_number,
            "status": o.status,
            "total_amount": float(o.total_amount) if o.total_amount else 0.0,
            "items": [item.item_name for item in o.items],
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })

    # Fetch business table count from settings
    from app.db.models.business import BusinessSettings
    settings_res = await db.execute(
        select(BusinessSettings).where(BusinessSettings.business_id == business.id)
    )
    b_settings = settings_res.scalars().first()
    table_count = b_settings.table_count if (b_settings and b_settings.table_count is not None) else 10
    slot_duration = b_settings.reservation_slot_duration if (b_settings and b_settings.reservation_slot_duration) else 90

    # Build live reservation availability context for today
    from datetime import datetime as dt_cls, timezone as tz_cls
    from app.modules.reservation_service import get_day_occupancy_matrix
    today_dt = dt_cls.now(tz_cls.utc)
    try:
        occupancy = await get_day_occupancy_matrix(db, business.id, today_dt, slot_duration)
        avail_lines = []
        for slot in occupancy:
            status = "FULL" if slot["available"] == 0 else f"{slot['available']}/{slot['total']} tables free"
            avail_lines.append(f"  {slot['hour']}: {status}")
        reservation_availability = f"Today's table occupancy (slot duration: {slot_duration} min):\n" + "\n".join(avail_lines)
    except Exception:
        reservation_availability = None

    # 7. Execute AI Processing with Gemini
    ai_result = await gemini_service.process_customer_message(
        message_text=body,
        catalog_context=catalog_context,
        conversation_history=history,
        business_name=business.name,
        order_context=order_context,
        table_count=table_count,
        business_location=business.location,
        reservation_availability=reservation_availability,
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
        from app.db.repositories.order import OrderRepository
        order_repo = OrderRepository(db)
        next_num = await order_repo.get_next_order_number(business.id)

        order = Order(
            business_id=business.id,
            customer_id=customer.id,
            order_number=next_num,
            status="pending",
            total_amount=Decimal("0.00"),
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
                    item_name=item_name,
                    quantity=qty,
                    unit_price=price,
                )
                db.add(order_item)

        order.total_amount = total
        conv_state.state = "ORDER_PENDING"

    elif ai_result.intent == "RESERVATION":
        if ai_result.is_reservation_complete:
            from datetime import datetime, timezone, timedelta
            from app.modules.reservation_service import allocate_table_number, find_alternative_slots
            # --- Robust Date & Time Parser ---
            from datetime import datetime as dt_cls, timezone as tz_cls, timedelta as td_cls
            now_local = dt_cls.now()

            res_date_str = ai_result.entities.get("reservation_date")
            res_time_str = ai_result.entities.get("reservation_time")

            target_date = now_local.date()
            if res_date_str:
                clean_d = res_date_str.strip().lower()
                if clean_d in ["today", "today's"]:
                    target_date = now_local.date()
                elif clean_d in ["tomorrow", "tmrw", "tomorrow's"]:
                    target_date = now_local.date() + td_cls(days=1)
                else:
                    try:
                        target_date = dt_cls.fromisoformat(clean_d[:10]).date()
                    except Exception:
                        try:
                            import dateutil.parser
                            target_date = dateutil.parser.parse(clean_d, fuzzy=True).date()
                        except Exception:
                            pass

            target_hour = 19
            target_min = 0
            if res_time_str:
                clean_t = res_time_str.strip().lower()
                try:
                    import dateutil.parser
                    t_parsed = dateutil.parser.parse(clean_t, fuzzy=True)
                    target_hour = t_parsed.hour
                    target_min = t_parsed.minute
                except Exception:
                    try:
                        parts = clean_t.replace("pm", "").replace("am", "").strip().split(":")
                        target_hour = int(parts[0])
                        if "pm" in clean_t and target_hour < 12:
                            target_hour += 12
                        target_min = int(parts[1]) if len(parts) > 1 else 0
                    except Exception:
                        pass

            # Create slot start datetime in UTC (normalized to 00 seconds for clean slots)
            parsed_dt = dt_cls(
                target_date.year, target_date.month, target_date.day,
                target_hour, target_min, 0, tzinfo=tz_cls.utc
            )

            # --- Conflict Detection & Table Allocation ---
            party_sz = int(ai_result.entities.get("party_size", 2))
            allocated_table = await allocate_table_number(db, business.id, parsed_dt, slot_duration, party_size=party_sz)

            if allocated_table is None:
                # All tables are full at the requested time — find alternatives
                alternatives = await find_alternative_slots(db, business.id, parsed_dt, slot_duration)
                alt_str = ", ".join(alternatives) if alternatives else "no nearby slots available"
                response_text = (
                    f"Sorry, all {table_count} tables are fully booked for the requested time. "
                    f"Available alternative slots: {alt_str}. "
                    f"Would you like to book one of these instead?"
                )
                conv_state.state = "RESERVATION_SLOT_FULL"
            else:
                cust_name = ai_result.entities.get("customer_name")
                reservation = Reservation(
                    business_id=business.id,
                    customer_id=customer.id,
                    customer_name=cust_name or customer.name,
                    reserved_at=parsed_dt,
                    duration_minutes=slot_duration,
                    party_size=party_sz,
                    table_or_slot=allocated_table,
                    status="confirmed",
                    notes=f"AI parsed reservation from: '{body}'",
                )
                db.add(reservation)
                # Override AI reply with assigned table details
                try:
                    time_display = parsed_dt.strftime("%I:%M %p").lstrip("0")
                except Exception:
                    time_display = parsed_dt.strftime("%H:%M")

                response_text = (
                    f"Your reservation is confirmed! "
                    f"Name: {cust_name or customer.name}, "
                    f"Party: {party_sz} guests, "
                    f"Assigned: {allocated_table}, "
                    f"Time: {time_display}. "
                    f"We look forward to welcoming you!"
                )
                conv_state.state = "RESERVATION_CONFIRMED"
        else:
            conv_state.state = "RESERVATION_INCOMPLETE"

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
