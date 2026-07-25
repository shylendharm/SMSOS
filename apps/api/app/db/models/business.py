import uuid
from sqlalchemy import String, Boolean, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPKMixin, TimestampMixin


class Business(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "businesses"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_type: Mapped[str] = mapped_column(String(50), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    locale: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    settings: Mapped["BusinessSettings"] = relationship("BusinessSettings", back_populates="business", uselist=False, cascade="all, delete-orphan")


class BusinessSettings(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "business_settings"

    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), unique=True, nullable=False)
    operating_hours: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}", nullable=False)
    table_count: Mapped[int | None] = mapped_column(nullable=True)
    appointment_slots: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}", nullable=False)
    sms_aliases: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}", nullable=False)
    notification_preferences: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}", nullable=False)

    business: Mapped["Business"] = relationship("Business", back_populates="settings")