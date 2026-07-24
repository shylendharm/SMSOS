import uuid
from sqlalchemy import String, ForeignKey, Boolean, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPKMixin, TimestampMixin


class Customer(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "customers"

    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(nullable=True)

    business: Mapped["Business"] = relationship("Business")

    __table_args__ = (
        UniqueConstraint("business_id", "phone_number", name="uq_business_customer_phone"),
        Index("idx_customer_business_phone", "business_id", "phone_number"),
    )