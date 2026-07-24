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


class IntentResult(BaseModel):
    intent: str = Field(description="Detected intent: INQUIRY, PLACE_ORDER, RESERVATION, CHECK_STATUS, OTHER")
    confidence: float = Field(default=0.9, description="Confidence score between 0.0 and 1.0")
    language: str = Field(default="english", description="Detected language: english, tamil, or tanglish")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities like items, quantities, reservation time, customer name, etc.")
    reply_text: str = Field(description="Drafted response to customer in their input language (English, Tamil, or Tanglish)")


class GeminiAIService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.client = None
        if self.api_key and HAS_GENAI:
            self.client = genai.Client(api_key=self.api_key)

    async def process_customer_message(
        self,
        message_text: str,
        catalog_context: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        business_name: str = "SMSOS Business",
    ) -> IntentResult:
        """
        Processes customer message, extracts intent/entities, and drafts reply text in the customer's language.
        """
        if not self.client:
            logger.warning("Gemini API key not configured or client missing. Returning fallback response.")
            return self._fallback_response(message_text)

        catalog_str = json.dumps(catalog_context or [], ensure_ascii=False)
        history_str = json.dumps(conversation_history or [], ensure_ascii=False)

        system_instruction = f"""
You are an AI Assistant for '{business_name}'. You handle incoming customer messages on WhatsApp/SMS.
You support messages in English, Tamil (தமிழ்), and Tanglish (Tamil written in Latin script, e.g. 'vanakkam', 'ethana mani ki open', '1kg rice irukka').

Available Business Catalog:
{catalog_str}

Recent Conversation History:
{history_str}

Your task:
1. Detect user's primary intent:
   - 'INQUIRY': Asking about products, prices, stock, opening hours, location.
   - 'PLACE_ORDER': Requesting to order or buy products from catalog.
   - 'RESERVATION': Requesting a table/appointment/booking.
   - 'CHECK_STATUS': Asking for status of a previous order/booking.
   - 'OTHER': Greetings, general feedback, or unclear messages.
2. Detect language ('english', 'tamil', 'tanglish').
3. Extract relevant entities (e.g. item_name, quantity, date, time, customer_name, order_id).
4. Generate a polite, helpful, and concise reply in the SAME language as the customer (English, Tamil, or Tanglish). If ordering, summarize items and total price if known. Keep responses brief for SMS/WhatsApp.
"""

        try:
            # We use gemini-1.5-flash or gemini-2.5-flash for speed
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
            entities={},
            reply_text="Thank you for reaching out! We received your message and will update you shortly.",
        )


gemini_service = GeminiAIService()
