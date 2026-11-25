from datetime import date, time, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

class RegisterPatient(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    phone: str | None = None

class RegisterDoctor(RegisterPatient):
    specialty_id: int
    bio: str | None = None
    consultation_fee: int | None = Field(default=None, ge=0)
    clinic_name: str | None = None
    clinic_address: str | None = None
    experience_years: int | None = Field(default=None, ge=0)

class LoginRequest(BaseModel):
    username: str
    password: str

class ProfileUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=80)
    last_name: str | None = Field(default=None, max_length=80)
    email: EmailStr | None = None
    phone: str | None = None
class DoctorProfileUpdate(ProfileUpdate):
    specialty_id: int | None = None
    bio: str | None = None
    consultation_fee: int | None = Field(default=None, ge=0)
    clinic_name: str | None = None
    clinic_address: str | None = None
    experience_years: int | None = Field(default=None, ge=0)

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None
    avatar_url: str | None
    is_active: bool
    created_at: datetime

class DoctorOut(UserOut):
    specialty_id: int | None
    specialty_name: str | None = None
    bio: str | None
    consultation_fee: int | None
    clinic_name: str | None
    clinic_address: str | None
    experience_years: int | None
    rating: float

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class SpecialtyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None

class SpecialtyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None

class SlotCreate(BaseModel):
    date: date
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def valid_range(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")
        return self

class SlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    doctor_id: int
    date: date
    start_time: time
    end_time: time
    is_available: bool

class BookingCreate(BaseModel):
    availability_id: int
    reason: str | None = Field(default=None, max_length=500)

class RescheduleInput(BaseModel):
    availability_id: int

class CancelInput(BaseModel):
    reason: str | None = Field(default=None, max_length=500)

class DoctorDecision(BaseModel):
    status: Literal["confirmed", "completed", "rejected"]
    doctor_notes: str | None = None

class AdminUserActive(BaseModel):
    is_active: bool

class AdminStatus(BaseModel):
    status: Literal["pending", "confirmed", "completed", "cancelled", "rejected"]
    doctor_notes: str | None = None

class AppointmentOut(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    availability_id: int
    date: date
    start_time: time
    end_time: time
    status: str
    reason: str | None
    doctor_notes: str | None
    cancellation_reason: str | None
    created_at: datetime
    patient_name: str | None = None
    doctor_name: str | None = None
    doctor_avatar_url: str | None = None
    specialty_name: str | None = None
