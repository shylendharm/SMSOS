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
    is_reorder: bool = Field(default=False, description="True ONLY if customer asks to repeat, reorder, or send the same order as last time")
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
        res["is_reorder"] = self.is_reorder
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

109: Business Catalog (Includes Availability Status):
110: {catalog_str}
111: 
112: CRITICAL CATALOG AVAILABILITY RULE:
113: Items with `"is_available": false` in the catalog above are OUT OF STOCK.
114: If a customer attempts to order an item, ALWAYS extract all requested items into the `items` array so the system can validate availability.
115: In `reply_text`, if any requested item has `"is_available": false`, explicitly mention that it is currently Out of Stock, and suggest available alternative items from the catalog.
117: 
118: Shop Location:
119: The shop is located at: {business_location or "T. Nagar, Chennai"}
120: 
121: Shop Capacity:
122: The shop has a total of {table_count} dining tables available for reservations.
123: Each reservation slot is 90 minutes long.
124: 
125: Current Table Availability (Live):
126: {reservation_availability or "No availability data loaded yet."}
127: 
128: Recent Conversation History:
129: {history_str}
130: 
131: Recent Orders Status Context for this Customer:
132: {order_str}
133: 
134: Your task:
135: 1. Detect user's primary intent:
136:    - 'INQUIRY': Asking about products, prices, stock, opening hours, location.
137:    - 'PLACE_ORDER': Requesting to order or buy products from catalog.
138:    - 'RESERVATION': Requesting a table/appointment/booking.
139:    - 'CHECK_STATUS': Asking for status of a previous order/booking.
140:    - 'OTHER': Greetings, general feedback, or unclear messages.
141: 2. Detect language ('english', 'tamil', 'tanglish').
142: 3. Extract relevant entities (e.g. item_name, quantity, date, time, customer_name, order_id).
143: 4. Generate a polite, helpful, and concise reply in the SAME language as the customer (English, Tamil, or Tanglish).    - If they are checking order status (CHECK_STATUS), use 'Recent Orders Status Context' to inform them of the exact status of their order (e.g. order #1 is pending/ready/completed/cancelled). If there are no recent orders in the context, politely state you couldn't find any.
144:     - If they are requesting a table reservation (RESERVATION):
145:       - Identify if the customer has specified: (1) reservation date, (2) reservation time, (3) party size (number of members/guests), and (4) customer name (booking name).
146:       - Set `is_reservation_complete = True` ONLY if all four details (date, time, party size, and customer name) are clearly specified by the customer in their message or the recent conversation history.
147:       - If ANY details are missing (e.g., they said "Book 2 tables" but gave no time or name, or "Book a table today at 4:00" but gave no party size or name), set `is_reservation_complete = False` and use `reply_text` to politely ask them to specify the missing details (date, time, number of members, or booking name) in their input language (English, Tamil, or Tanglish).
148:     - If they are ordering (PLACE_ORDER):
149:       - Extract ONLY available ordered items and quantities.
150:       - Extract delivery location / hostel / room number into `delivery_location` if provided.
151:       - CRITICAL TANGLISH LOCATION EXTRACTION: In Tanglish, delivery locations often follow patterns like:
152:         * "X ku anupu/anupunga" = "send to X" → delivery_location = X
153:         * "X ku deliver pannunga" = "deliver to X" → delivery_location = X
154:         * "X block/hostel/room" = location reference → delivery_location = X block/hostel/room
155:         * "ya X anupunga" = "send to X please" → delivery_location = X
156:         Examples:
157:           - "oru chapathi ya IMA anupunga" → items: chapathi x1, delivery_location: "IMA"
158:           - "2 dosa Tinnanur ku anupu" → items: dosa x2, delivery_location: "Tinnanur"
159:           - "idli venpa block ku anupunga" → items: idli x1, delivery_location: "Venpa block"
160:       - If the customer is asking to repeat, reorder, or send the same order as last time (e.g. 'repeat last order', 'same order again', 'order same again', 'pazhaya order thirumba anupunga', 'same order', 'repeat order'), set `intent = "PLACE_ORDER"` and set `is_reorder = True`.
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

        # 1. Try Gemini API (Primary with Model Fallbacks)
        if self.client:
            for gemini_model in ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash"]:
                try:
                    response = self.client.models.generate_content(
                        model=gemini_model,
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
                        logger.info("Successfully processed message with Gemini AI", model=gemini_model)
                        return IntentResult(**result_data)
                except Exception as e:
                    logger.warning("Gemini API call failed for model", model=gemini_model, error=str(e))

        # 2. Try OpenRouter AI (Secondary Fallback with Completely Free Model)
        openrouter_key = settings.OPENROUTER_API_KEY
        if openrouter_key:
            import httpx
            headers = {
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "SMSOS",
            }
            openrouter_prompt = system_instruction + (
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
            # Try OpenRouter Free Models
            for openrouter_model in ["meta-llama/llama-3.3-70b-instruct:free", "google/gemini-2.0-flash-lite-001:free", "mistralai/mistral-7b-instruct:free"]:
                payload = {
                    "model": openrouter_model,
                    "messages": [
                        {"role": "system", "content": openrouter_prompt},
                        {"role": "user", "content": message_text},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 250,
                }
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        resp = await client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
                        if resp.status_code == 200:
                            resp_json = resp.json()
                            content = resp_json["choices"][0]["message"].get("content")
                            if content:
                                content_clean = content.strip()
                                if content_clean.startswith("```"):
                                    content_clean = content_clean.split("```")[1]
                                    if content_clean.startswith("json"):
                                        content_clean = content_clean[4:]
                                    content_clean = content_clean.strip()
                                result_data = json.loads(content_clean)
                                logger.info("Successfully processed message with OpenRouter AI", model=openrouter_model)
                                return IntentResult(**result_data)
                except Exception as e:
                    logger.warning("OpenRouter API model call failed", model=openrouter_model, error=str(e))

        # 3. Smart Offline Fallback (If all APIs fail or rate-limit)
        return self._fallback_response(message_text, catalog_context)

    def _fallback_response(
        self,
        message_text: str,
        catalog_context: Optional[List[Dict[str, Any]]] = None
    ) -> IntentResult:
        text_lower = message_text.lower()
        is_food_inquiry = any(w in text_lower for w in ["enna irukku", "menu", "food", "items", "kitta", "list", "saapada", "listu", "rate"])
        is_order_intent = any(w in text_lower for w in [
            "buy", "order", "vaanga", "venum", "pannanum", "dosa", "dosai", "idli", "idly",
            "biryani", "briyani", "rice", "coffee", "tea", "chapathi", "chappathi", "juice",
            "water", "parotta", "poori", "vada", "pongal", "meals", "anupunga", "anupu",
            "send", "deliver", "kudunga", "thaa"
        ])
        is_reservation = any(w in text_lower for w in ["book", "table", "reserve", "slot"])
        is_status = any(w in text_lower for w in ["status", "where is", "track", "dispatch"])

        if is_food_inquiry or is_order_intent:
            intent = "INQUIRY" if is_food_inquiry and not is_order_intent else "PLACE_ORDER"
            if catalog_context:
                available_items = [c for c in catalog_context if c.get('is_available', True)]
                if available_items:
                    categories: Dict[str, List[str]] = {}
                    for item in available_items:
                        cat_name = item.get('category') or 'General'
                        if cat_name not in categories:
                            categories[cat_name] = []
                        price_val = float(item.get('price', 0))
                        categories[cat_name].append(f"• {item.get('name', '')} (₹{price_val:.2f})")
                    
                    category_blocks = []
                    for cat_name, item_strs in categories.items():
                        category_blocks.append(f"*{cat_name}*:\n" + "\n".join(item_strs))
                    
                    full_menu_str = "\n\n".join(category_blocks)
                    reply = f"Here is our complete menu:\n\n{full_menu_str}\n\nPlease reply with the item name and quantity to place your order!"
                else:
                    reply = "Welcome! What would you like to order today? Please tell us the item name and quantity."
            else:
                reply = "Welcome! What food items would you like to order today? Please let us know the item name and quantity."
        elif is_reservation:
            intent = "RESERVATION"
            reply = "We'd be happy to reserve a table for you! Please tell us the date, time, party size, and your name."
        elif is_status:
            intent = "CHECK_STATUS"
            reply = "Please share your Order Number (e.g. #1) so we can check your order status for you."
        else:
            intent = "INQUIRY"
            reply = "Welcome! How can we assist you today? You can place an order or book a table with us."

        return IntentResult(
            intent=intent,
            confidence=0.7,
            language="tanglish" if any(w in text_lower for w in ["enna", "irukku", "kitta", "pannanum", "venum"]) else "english",
            items=[],
            party_size=None,
            reply_text=reply,
        )


gemini_service = GeminiAIService()
