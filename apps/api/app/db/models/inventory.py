import uuid
from decimal import Decimal
from sqlalchemy import String, ForeignKey, Numeric, Boolean, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPKMixin, TimestampMixin


class InventoryItem(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "inventory_items"

    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    current_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.0"), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), default="units", nullable=False)
    is_low_stock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    business: Mapped["Business"] = relationship("Business")
    threshold: Mapped["InventoryThreshold"] = relationship("InventoryThreshold", back_populates="item", uselist=False, cascade="all, delete-orphan")
    events: Mapped[list["InventoryEvent"]] = relationship("InventoryEvent", back_populates="item", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("business_id", "item_name", name="uq_business_inventory_item_name"),
        Index("idx_inventory_low", "business_id", "is_low_stock"),
    )


class InventoryThreshold(Base, UUIDPKMixin):
    __tablename__ = "inventory_thresholds"

    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inventory_items.id", ondelete="CASCADE"), unique=True, nullable=False)
    low_threshold: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("5.0"), nullable=False)
    reorder_quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    auto_alert: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    item: Mapped["InventoryItem"] = relationship("InventoryItem", back_populates="threshold")


class InventoryEvent(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "inventory_events"

    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity_change: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity_after: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    notes: Mapped[str | None] = mapped_column(nullable=True)

    item: Mapped["InventoryItem"] = relationship("InventoryItem", back_populates="events")

    __table_args__ = (
        Index("idx_inv_events_item", "item_id", "created_at"),
    )