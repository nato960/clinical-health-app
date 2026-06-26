from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import Speciality
from app.models.address import Address

class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True)
    crm: Mapped[str] = mapped_column(String, unique=True)
    birth_date: Mapped[datetime | None] = mapped_column(Date(timezone=True), default=None)
    phone: Mapped[str] = mapped_column(String)
    speciality: Mapped[Speciality] = mapped_column(Enum(Speciality))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    address_id: Mapped[int | None] = mapped_column(ForeignKey("addresses.id"), default=None)
    address: Mapped["Address | None"] = relationship("Address", lazy="selectin")
    