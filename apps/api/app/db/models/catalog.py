import uuid
from decimal import Decimal
from sqlalchemy import String, ForeignKey, Numeric, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPKMixin, TimestampMixin


class CatalogItem(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "catalog_items"

    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    unit: Mapped[str] = mapped_column(String(50), nullable=False, default="piece")
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="General")
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    business: Mapped["Business"] = relationship("Business")

    __table_args__ = (
        Index("idx_catalog_business_category", "business_id", "category", "is_available"),
    )