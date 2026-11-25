from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Float, Date, Time, DateTime, ForeignKey, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Specialty(Base):
    __tablename__ = "specialties"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    doctors = relationship("User", back_populates="specialty")

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    specialty_id: Mapped[int | None] = mapped_column(ForeignKey("specialties.id", ondelete="SET NULL"))
    bio: Mapped[str | None] = mapped_column(Text)
    consultation_fee: Mapped[int | None] = mapped_column(Integer)
    clinic_name: Mapped[str | None] = mapped_column(String(150))
    clinic_address: Mapped[str | None] = mapped_column(String(300))
    experience_years: Mapped[int | None] = mapped_column(Integer)
    rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    specialty = relationship("Specialty", back_populates="doctors")
    slots = relationship("Availability", back_populates="doctor", cascade="all, delete-orphan", foreign_keys="Availability.doctor_id")
    patient_appointments = relationship("Appointment", back_populates="patient", foreign_keys="Appointment.patient_id")
    doctor_appointments = relationship("Appointment", back_populates="doctor", foreign_keys="Appointment.doctor_id")

class Availability(Base):
    __tablename__ = "availabilities"
    __table_args__ = (UniqueConstraint("doctor_id", "date", "start_time", name="uq_doctor_date_start"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[object] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[object] = mapped_column(Time, nullable=False)
    end_time: Mapped[object] = mapped_column(Time, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    doctor = relationship("User", back_populates="slots", foreign_keys=[doctor_id])
    appointments = relationship("Appointment", back_populates="slot")

class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (Index("ix_appointments_doctor_date", "doctor_id", "date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    availability_id: Mapped[int] = mapped_column(
    ForeignKey("availabilities.id", ondelete="RESTRICT"),
    nullable=False,
    index=True
    )
    date: Mapped[object] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[object] = mapped_column(Time, nullable=False)
    end_time: Mapped[object] = mapped_column(Time, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String(500))
    doctor_notes: Mapped[str | None] = mapped_column(Text)
    cancellation_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    patient = relationship("User", back_populates="patient_appointments", foreign_keys=[patient_id])
    doctor = relationship("User", back_populates="doctor_appointments", foreign_keys=[doctor_id])
    slot = relationship("Availability", back_populates="appointments")
