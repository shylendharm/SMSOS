import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import structlog

from app.core.config import settings

logger = structlog.get_logger()

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class OrderItemEntity(BaseModel):
    item_name: str = Field(description="Name of the catalog item being ordered")
    quantity: int = Field(default=1, description="Quantity ordered")


class IntentResult(BaseModel):
    intent: str = Field(description="Detected intent: INQUIRY, PLACE_ORDER, RESERVATION, CHECK_STATUS, OTHER")
    confidence: float = Field(default=0.9, description="Confidence score between 0.0 and 1.0")
    language: str = Field(default="english", description="Detected language: english, tamil, or tanglish")
    items: List[OrderItemEntity] = Field(default_factory=list, description="List of items extracted if placing an order")
    party_size: Optional[int] = Field(default=None, description="Party size/count extracted if reserving a table/booking")
    reservation_date: Optional[str] = Field(default=None, description="Date of reservation, e.g. YYYY-MM-DD or today/tomorrow/monday")
    reservation_time: Optional[str] = Field(default=None, description="Time of reservation, e.g. HH:MM or 4 PM/noon")
    customer_name: Optional[str] = Field(default=None, description="Booking customer name for the reservation")
    is_reservation_complete: bool = Field(default=False, description="True ONLY if the customer has fully specified the reservation date, time, party size, and customer name")
    delivery_location: Optional[str] = Field(default=None, description="Delivery location, hostel name, block, room number, or address specified by customer")
    is_order_confirmed: bool = Field(default=False, description="True ONLY if customer explicitly confirms/accepts an order summary by replying YES/confirm/aama/ok")
    reply_text: str = Field(description="Drafted response to customer in their input language (English, Tamil, or Tanglish)")

    @property
    def entities(self) -> Dict[str, Any]:
        res = {}
        if self.items:
            res["items"] = [{"item_name": x.item_name, "quantity": x.quantity} for x in self.items]
        if self.party_size is not None:
            res["party_size"] = self.party_size
        if self.reservation_date is not None:
            res["reservation_date"] = self.reservation_date
        if self.reservation_time is not None:
            res["reservation_time"] = self.reservation_time
        if self.customer_name is not None:
            res["customer_name"] = self.customer_name
        if self.delivery_location is not None:
            res["delivery_location"] = self.delivery_location
        res["is_reservation_complete"] = self.is_reservation_complete
        res["is_order_confirmed"] = self.is_order_confirmed
        return res


class GeminiAIService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.client = None
        if self.api_key and HAS_GENAI:
            self.client = genai.Client(api_key=self.api_key)

    def _fallback_response(self, text: str) -> IntentResult:
        return IntentResult(
            intent="OTHER",
            confidence=0.5,
            language="english",
            reply_text="Thank you for reaching out! We received your message and will update you shortly."
        )

    async def process_customer_message(
        self,
        message_text: str,
        catalog_context: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        business_name: str = "SMSOS Business",
        order_context: Optional[List[Dict[str, Any]]] = None,
        table_count: int = 10,
        business_location: Optional[str] = None,
        reservation_availability: Optional[str] = None,
    ) -> IntentResult:
        """
        Processes customer message, extracts intent/entities, and drafts reply text in the customer's language.
        """
        if not self.client:
            logger.warning("Gemini API key not configured or client missing. Returning fallback response.")
            return self._fallback_response(message_text)

        catalog_str = json.dumps(catalog_context or [], ensure_ascii=False)
        history_str = json.dumps(conversation_history or [], ensure_ascii=False)
        order_str = json.dumps(order_context or [], ensure_ascii=False)

        from datetime import datetime as dt_cls
        now_utc = dt_cls.now()
        current_date_str = now_utc.strftime("%Y-%m-%d (%A)")
        current_time_str = now_utc.strftime("%H:%M")

        system_instruction = f"""
You are an AI Assistant for '{business_name}'. You handle incoming customer messages on WhatsApp/SMS.
You support messages in English, Tamil (தமிழ்), and Tanglish (Tamil written in Latin script, e.g. 'vanakkam', 'ethana mani ki open', '1kg rice irukka').

Current System Date & Time Context:
Today is: {current_date_str}
Current Time: {current_time_str}
CRITICAL DATE RULE: You MUST convert all relative date references ('today', 'tomorrow', 'tmrw', 'next friday', etc.) into an EXACT ISO format 'YYYY-MM-DD' for `reservation_date` based on Today's date above ({now_utc.strftime("%Y-%m-%d")}).
CRITICAL TIME RULE: You MUST convert all time references ('7pm', '7:00 PM', 'noon', etc.) into 24-hour 'HH:MM' format for `reservation_time` (e.g. '19:00').

Available Business Catalog:
{catalog_str}

Shop Location:
The shop is located at: {business_location or "T. Nagar, Chennai"}

Shop Capacity:
The shop has a total of {table_count} dining tables available for reservations.
Each reservation slot is 90 minutes long.

Current Table Availability (Live):
{reservation_availability or "No availability data loaded yet."}

Recent Conversation History:
{history_str}

Recent Orders Status Context for this Customer:
{order_str}

Your task:
1. Detect user's primary intent:
   - 'INQUIRY': Asking about products, prices, stock, opening hours, location.
   - 'PLACE_ORDER': Requesting to order or buy products from catalog.
   - 'RESERVATION': Requesting a table/appointment/booking.
   - 'CHECK_STATUS': Asking for status of a previous order/booking.
   - 'OTHER': Greetings, general feedback, or unclear messages.
2. Detect language ('english', 'tamil', 'tanglish').
3. Extract relevant entities (e.g. item_name, quantity, date, time, customer_name, order_id).
4. Generate a polite, helpful, and concise reply in the SAME language as the customer (English, Tamil, or Tanglish).    - If they are checking order status (CHECK_STATUS), use 'Recent Orders Status Context' to inform them of the exact status of their order (e.g. order #1 is pending/ready/completed/cancelled). If there are no recent orders in the context, politely state you couldn't find any.
    - If they are requesting a table reservation (RESERVATION):
      - Identify if the customer has specified: (1) reservation date, (2) reservation time, (3) party size (number of members/guests), and (4) customer name (booking name).
      - Set `is_reservation_complete = True` ONLY if all four details (date, time, party size, and customer name) are clearly specified by the customer in their message or the recent conversation history.
      - If ANY details are missing (e.g., they said "Book 2 tables" but gave no time or name, or "Book a table today at 4:00" but gave no party size or name), set `is_reservation_complete = False` and use `reply_text` to politely ask them to specify the missing details (date, time, number of members, or booking name) in their input language (English, Tamil, or Tanglish).
    - If they are ordering (PLACE_ORDER):
      - Extract ordered items and quantities.
      - Extract delivery location / hostel / room number into `delivery_location` if provided.
      - If the customer is replying "YES", "confirm", "ok", "aama" to confirm an order summary, set `is_order_confirmed = True`.
"""

        xai_key = settings.XAI_API_KEY or settings.GROK_API_KEY
        if xai_key:
            import httpx
            headers = {
                "Authorization": f"Bearer {xai_key}",
                "Content-Type": "application/json",
            }
            grok_system_prompt = system_instruction + (
                "\n\nCRITICAL OUTPUT FORMAT REQUIREMENT:\n"
                "Return ONLY a valid JSON object with the following fields:\n"
                "{\n"
                '  "intent": "INQUIRY" | "PLACE_ORDER" | "RESERVATION" | "CHECK_STATUS" | "OTHER",\n'
                '  "confidence": float,\n'
                '  "language": "english" | "tamil" | "tanglish",\n'
                '  "items": [{"item_name": str, "quantity": int}],\n'
                '  "party_size": int | null,\n'
                '  "reservation_date": str | null,\n'
                '  "reservation_time": str | null,\n'
                '  "customer_name": str | null,\n'
                '  "is_reservation_complete": bool,\n'
                '  "delivery_location": str | null,\n'
                '  "is_order_confirmed": bool,\n'
                '  "reply_text": str\n'
                "}"
            )
            payload = {
                "model": "grok-beta",
                "messages": [
                    {"role": "system", "content": grok_system_prompt},
                    {"role": "user", "content": message_text},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            }
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post("https://api.x.ai/v1/chat/completions", json=payload, headers=headers)
                    if resp.status_code == 200:
                        resp_json = resp.json()
                        content = resp_json["choices"][0]["message"]["content"]
                        result_data = json.loads(content)
                        logger.info("Successfully processed message with Grok AI")
                        return IntentResult(**result_data)
                    else:
                        logger.error("Grok API call failed", status_code=resp.status_code, body=resp.text)
            except Exception as e:
                logger.error("Grok API exception", error=str(e))

        if self.client:
            try:
                # Fallback to Gemini if configured
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=message_text,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=IntentResult,
                        temperature=0.2,
                    ),
                )

                if response.text:
                    result_data = json.loads(response.text)
                    return IntentResult(**result_data)
            except Exception as e:
                logger.error("Gemini API call failed", error=str(e))
                return self._fallback_response(message_text)

        return self._fallback_response(message_text)

    def _fallback_response(self, message_text: str) -> IntentResult:
        text_lower = message_text.lower()
        if any(w in text_lower for w in ["buy", "order", "vaanga", "venum"]):
            intent = "PLACE_ORDER"
        elif any(w in text_lower for w in ["book", "table", "reserve"]):
            intent = "RESERVATION"
        elif any(w in text_lower for w in ["status", "where is"]):
            intent = "CHECK_STATUS"
        else:
            intent = "INQUIRY"

        return IntentResult(
            intent=intent,
            confidence=0.5,
            language="english",
            items=[],
            party_size=None,
            reply_text="Thank you for reaching out! We received your message and will update you shortly.",
        )


gemini_service = GeminiAIService()
