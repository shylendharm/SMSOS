import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, JSON, ForeignKey, DateTime, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPKMixin, TimestampMixin


class WebhookEvent(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "webhook_events"

    event_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}", nullable=False)
    processed: Mapped[bool] = mapped_column(default=False, nullable=False)
    processing_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class IntentPrediction(Base, UUIDPKMixin):
    __tablename__ = "intent_predictions"

    message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("inbound_messages.id", ondelete="SET NULL"), nullable=True)
    intent: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    entities: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}", nullable=False)
    candidate_intents: Mapped[dict] = mapped_column(JSON, default=list, server_default="[]", nullable=False)
    classifier_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    message: Mapped["InboundMessage"] = relationship("InboundMessage")