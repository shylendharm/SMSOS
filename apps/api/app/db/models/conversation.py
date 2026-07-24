import uuid
from datetime import datetime
from sqlalchemy import String, JSON, ForeignKey, DateTime, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPKMixin, TimestampMixin


class ConversationState(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "conversation_states"

    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    from_number: Mapped[str] = mapped_column(String(20), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    business: Mapped["Business"] = relationship("Business")
    customer: Mapped["Customer"] = relationship("Customer")

    __table_args__ = (
        Index("idx_conversation_from", "business_id", "from_number"),
    )