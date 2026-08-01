from typing import Optional, Dict, Any
import structlog
from twilio.rest import Client
from twilio.request_validator import RequestValidator

from app.core.config import settings

logger = structlog.get_logger()


class TwilioService:
    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
    ):
        self.account_sid = account_sid or settings.TWILIO_ACCOUNT_SID
        self.auth_token = auth_token or settings.TWILIO_AUTH_TOKEN
        self.from_number = from_number or settings.TWILIO_PHONE_NUMBER
        
        self.client = None
        if self.account_sid and self.auth_token and not self.account_sid.startswith("ACXXXX"):
            try:
                self.client = Client(self.account_sid, self.auth_token)
            except Exception as e:
                logger.error("Failed to initialize Twilio Client", error=str(e))
        
        self.validator = RequestValidator(self.auth_token) if self.auth_token else None

    def send_message(self, to_number: str, body: str, from_number: Optional[str] = None, media_url: Optional[str] = None) -> Optional[str]:
        """
        Sends an SMS or WhatsApp message via Twilio with optional media attachment.
        Returns the Twilio Message SID on success, None on error.
        """
        sender = from_number or self.from_number
        
        # Ensure proper whatsapp prefix formatting if to_number starts with whatsapp:
        if to_number.startswith("whatsapp:") and not sender.startswith("whatsapp:"):
            sender = f"whatsapp:{sender}"
        elif not to_number.startswith("whatsapp:") and sender.startswith("whatsapp:"):
            sender = sender.replace("whatsapp:", "")

        if not self.client:
            logger.info("Twilio client mock: message sending simulated", to=to_number, body=body, media_url=media_url)
            return "SM_MOCK_" + str(hash(to_number + body))[:16]

        try:
            kwargs = {
                "to": to_number,
                "from_": sender,
                "body": body,
            }
            if media_url:
                kwargs["media_url"] = [media_url]

            message = self.client.messages.create(**kwargs)
            logger.info("Sent Twilio message", sid=message.sid, to=to_number, media_url=media_url)
            return message.sid
        except Exception as e:
            logger.error("Failed to send message via Twilio", error=str(e), to=to_number)
            return None

    def verify_webhook_signature(self, url: str, params: Dict[str, Any], signature: str) -> bool:
        """
        Validates that an incoming HTTP request originated from Twilio.
        """
        if not self.validator or settings.APP_ENV == "development":
            return True  # Bypass in dev if configured

        return self.validator.validate(url, params, signature)


twilio_service = TwilioService()
