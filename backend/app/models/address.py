from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

class Address(Base):
    __tablename__ = "addresses"

    id : Mapped[int] = mapped_column(primary_key=True)
    street: Mapped[str | None] = mapped_column(String, default=None)
    city: Mapped[str | None] = mapped_column(String, default=None)
    state: Mapped[str | None] = mapped_column(String(2), default=None)
    zip_code: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
