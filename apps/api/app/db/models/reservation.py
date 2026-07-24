import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, Integer, Index, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPKMixin, TimestampMixin


class Reservation(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "reservations"

    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    table_or_slot: Mapped[str | None] = mapped_column(String(50), nullable=True)
    party_size: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="confirmed", nullable=False)
    notes: Mapped[str | None] = mapped_column(nullable=True)

    business: Mapped["Business"] = relationship("Business")
    customer: Mapped["Customer"] = relationship("Customer")

    __table_args__ = (
        Index("idx_reservation_time", "business_id", "reserved_at", "status"),
        Index("idx_reservation_customer", "business_id", "customer_name"),
    )