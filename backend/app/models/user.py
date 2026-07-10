from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import UserRole
from app.models.staff import Staff
from app.models.doctor import Doctor
from app.models.patient import Patient


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    firebase_uid: Mapped[str] = mapped_column(String, unique=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff.id"), unique=True, default=None)
    staff: Mapped["Staff | None"] = relationship("Staff", lazy="selectin")

    doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctors.id"), unique=True, default=None)
    doctor: Mapped["Doctor | None"] = relationship("Doctor", lazy="selectin")

    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.id"), unique=True, default=None)
    patient: Mapped["Patient | None"] = relationship("Patient", lazy="selectin")