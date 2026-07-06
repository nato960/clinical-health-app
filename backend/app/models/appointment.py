from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.enums import CancellationReason, Speciality


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index(
            "uq_appointment_doctor_active_slot",
            "doctor_id", "date",
            unique=True,
            postgresql_where=text("cancellation_reason IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    date: Mapped[datetime] = mapped_column(DateTime())
    speciality: Mapped[Speciality | None] = mapped_column(Enum(Speciality), default=None)
    cancellation_reason: Mapped[CancellationReason | None] = mapped_column(Enum(CancellationReason), default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    doctor: Mapped["Doctor"] = relationship("Doctor", lazy="selectin")
    patient: Mapped["Patient"] = relationship("Patient", lazy="selectin")
