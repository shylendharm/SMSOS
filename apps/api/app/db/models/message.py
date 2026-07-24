import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, JSON, ForeignKey, DateTime, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPKMixin, TimestampMixin


class InboundMessage(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "inbound_messages"

    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    message_sid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    from_number: Mapped[str] = mapped_column(String(20), nullable=False)
    to_number: Mapped[str] = mapped_column(String(20), nullable=False)
    body: Mapped[str] = mapped_column(nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}", nullable=False)
    processed: Mapped[bool] = mapped_column(default=False, nullable=False)
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    business: Mapped["Business"] = relationship("Business")

    __table_args__ = (
        Index("idx_inbound_business_time", "business_id", "created_at"),
    )


class OutboundMessage(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "outbound_messages"

    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    to_number: Mapped[str] = mapped_column(String(20), nullable=False)
    body: Mapped[str] = mapped_column(nullable=False)
    message_sid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(nullable=True)

    business: Mapped["Business"] = relationship("Business")

    __table_args__ = (
        Index("idx_outbound_business", "business_id", "created_at"),
        Index("idx_outbound_sid", "message_sid"),
    )