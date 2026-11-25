from datetime import date, datetime
from pathlib import Path
from io import BytesIO
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func, or_
from app.database import get_db
from app.models import User, Specialty, Availability, Appointment
from app.schemas import (
    AdminStatus,
    AdminUserActive,
    AppointmentOut,
    BookingCreate,
    CancelInput,
    DoctorDecision,
    DoctorOut,
    DoctorProfileUpdate,
    LoginRequest,
    ProfileUpdate,
    RegisterDoctor,
    RegisterPatient,
    RescheduleInput,
    SlotCreate,
    SlotOut,
    SpecialtyCreate,
    SpecialtyOut,
    TokenOut,
    UserOut,
)
from app.security import (
    admin_only,
    current_user,
    doctor_only,
    hash_password,
    make_token,
    patient_only,
    verify_password,
)
from app.utils import appointment_dict
from sqlalchemy.exc import IntegrityError
from PIL import Image, UnidentifiedImageError

router = APIRouter()
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads" / "doctor_avatars"
MAX_AVATAR_BYTES = 5 * 1024 * 1024
MAX_AVATAR_PIXELS = 30_000_000


def _slot_is_in_future(slot: Availability) -> bool:
    now = datetime.now()
    return slot.date > date.today() or (
        slot.date == date.today() and slot.start_time > now.time().replace(tzinfo=None)
    )


def _remove_previous_local_avatar(avatar_url: str | None) -> None:
    if not avatar_url or not avatar_url.startswith("/uploads/doctor_avatars/"):
        return
    filename = avatar_url.rsplit("/", 1)[-1]
    if filename and Path(filename).name == filename:
        old_file = UPLOAD_ROOT / filename
        try:
            old_file.unlink(missing_ok=True)
        except OSError:
            # A stale file must not make an otherwise successful profile update fail.
            pass

def doctor_data(d: User):
    data = {c.name: getattr(d, c.name) for c in d.__table__.columns}
    data["specialty_name"] = d.specialty.name if d.specialty else None
    return data

def appointment_list_query(db: Session):
    return db.query(Appointment).options(
        joinedload(Appointment.patient),
        joinedload(Appointment.doctor).joinedload(User.specialty),
    )


def get_appointment(db: Session, appointment_id: int):
    item = appointment_list_query(db).filter(Appointment.id == appointment_id).first()
    if not item:
        raise HTTPException(404, "Appointment not found")
    return item

def update_profile(db, user, payload):
    values = payload.model_dump(exclude_unset=True)
    if values.get("email"):
        values["email"] = str(values["email"])
        exists = db.query(User).filter(User.email == values["email"], User.id != user.id).first()
        if exists:
            raise HTTPException(409, "Email is already registered")
    for key, value in values.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user

# AUTHENTICATION
@router.post("/auth/register/patient", response_model=UserOut, status_code=201, tags=["Authentication"])
def register_patient(data: RegisterPatient, db: Session = Depends(get_db)):
    if db.query(User).filter((User.username == data.username) | (User.email == str(data.email))).first():
        raise HTTPException(409, "Username or email already exists")
    user = User(role="patient", username=data.username, email=str(data.email), hashed_password=hash_password(data.password), first_name=data.first_name, last_name=data.last_name, phone=data.phone)
    db.add(user); db.commit(); db.refresh(user)
    return user

@router.post("/auth/register/doctor", response_model=DoctorOut, status_code=201, tags=["Authentication"])
def register_doctor(data: RegisterDoctor, db: Session = Depends(get_db)):
    if not db.query(Specialty).filter(Specialty.id == data.specialty_id).first():
        raise HTTPException(404, "Specialty not found")
    if db.query(User).filter((User.username == data.username) | (User.email == str(data.email))).first():
        raise HTTPException(409, "Username or email already exists")
    user = User(role="doctor", username=data.username, email=str(data.email), hashed_password=hash_password(data.password), first_name=data.first_name, last_name=data.last_name, phone=data.phone, specialty_id=data.specialty_id, bio=data.bio, consultation_fee=data.consultation_fee, clinic_name=data.clinic_name, clinic_address=data.clinic_address, experience_years=data.experience_years)
    db.add(user); db.commit(); db.refresh(user)
    return doctor_data(user)

@router.post("/auth/login", response_model=TokenOut, tags=["Authentication"])
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_password) or not user.is_active:
        raise HTTPException(401, "Incorrect username or password")
    return {"access_token": make_token(user), "user": user}

@router.get("/auth/me", response_model=UserOut, tags=["Authentication"])
def auth_me(user: User = Depends(current_user)):
    return user

# SPECIALTIES
@router.get("/specialties", response_model=list[SpecialtyOut], tags=["Specialties"])
def specialties(db: Session = Depends(get_db)):
    return db.query(Specialty).order_by(Specialty.name).all()

@router.post("/specialties", response_model=SpecialtyOut, status_code=201, tags=["Specialties"])
def add_specialty(data: SpecialtyCreate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    if db.query(Specialty).filter(func.lower(Specialty.name) == data.name.lower()).first():
        raise HTTPException(409, "Specialty already exists")
    item = Specialty(name=data.name.strip(), description=data.description)
    db.add(item); db.commit(); db.refresh(item)
    return item

@router.patch("/specialties/{specialty_id}", response_model=SpecialtyOut, tags=["Specialties"])
def edit_specialty(specialty_id: int, data: SpecialtyCreate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    item = db.query(Specialty).filter(Specialty.id == specialty_id).first()
    if not item: raise HTTPException(404, "Specialty not found")
    duplicate = db.query(Specialty).filter(func.lower(Specialty.name) == data.name.lower(), Specialty.id != specialty_id).first()
    if duplicate: raise HTTPException(409, "Specialty already exists")
    item.name = data.name.strip(); item.description = data.description
    db.commit(); db.refresh(item)
    return item

@router.delete("/specialties/{specialty_id}", tags=["Specialties"])
def remove_specialty(specialty_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    item = db.query(Specialty).filter(Specialty.id == specialty_id).first()
    if not item: raise HTTPException(404, "Specialty not found")
    if item.doctors: raise HTTPException(409, "Reassign doctors before deleting this specialty")
    db.delete(item); db.commit()
    return {"message": "Specialty deleted"}

# DOCTOR DIRECTORY / DOCTOR PANEL
@router.get("/doctors", response_model=list[DoctorOut], tags=["Doctors"])
def list_doctors(specialty_id: int | None = None, q: str | None = None, db: Session = Depends(get_db)):
    query = db.query(User).options(joinedload(User.specialty)).filter(User.role == "doctor", User.is_active.is_(True))
    if specialty_id is not None: query = query.filter(User.specialty_id == specialty_id)
    if q:
        term = f"%{q}%"
        query = query.filter((User.first_name.ilike(term)) | (User.last_name.ilike(term)) | (User.clinic_name.ilike(term)))
    return [doctor_data(d) for d in query.order_by(User.rating.desc(), User.last_name).all()]

@router.get("/doctors/me", response_model=DoctorOut, tags=["Doctor Panel"])
def doctor_me(db: Session = Depends(get_db), user: User = Depends(doctor_only)):
    db.refresh(user)
    return doctor_data(user)

@router.patch("/doctors/me", response_model=DoctorOut, tags=["Doctor Panel"])
def update_doctor(data: DoctorProfileUpdate, db: Session = Depends(get_db), user: User = Depends(doctor_only)):
    values = data.model_dump(exclude_unset=True)
    if values.get("specialty_id") and not db.query(Specialty).filter(Specialty.id == values["specialty_id"]).first():
        raise HTTPException(404, "Specialty not found")
    update_profile(db, user, data)
    return doctor_data(user)


@router.post("/doctors/me/avatar", response_model=DoctorOut, tags=["Doctor Panel"])
async def upload_doctor_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(doctor_only),
):
    """Upload a doctor profile image. Patients and admins cannot use this route."""
    raw = await file.read(MAX_AVATAR_BYTES + 1)
    await file.close()
    if not raw:
        raise HTTPException(400, "Choose an image to upload")
    if len(raw) > MAX_AVATAR_BYTES:
        raise HTTPException(413, "Profile images must be 5 MB or smaller")

    # Decode and re-encode rather than trusting the client MIME type or raw file.
    # This rejects malformed images, caps decompression size, and strips metadata.
    try:
        with Image.open(BytesIO(raw)) as source:
            image_format = source.format
            if image_format not in {"JPEG", "PNG", "WEBP"}:
                raise HTTPException(415, "Use a JPEG, PNG, or WebP image")
            if source.width * source.height > MAX_AVATAR_PIXELS:
                raise HTTPException(413, "Image dimensions are too large")
            source.load()
            source.thumbnail((1600, 1600))
            if image_format == "JPEG" and source.mode not in {"RGB", "L"}:
                source = source.convert("RGB")
            output = BytesIO()
            save_options = {"optimize": True}
            if image_format in {"JPEG", "WEBP"}:
                save_options["quality"] = 88
            source.save(output, format=image_format, **save_options)
            processed = output.getvalue()
            if len(processed) > MAX_AVATAR_BYTES:
                raise HTTPException(413, "Processed profile image exceeds the 5 MB limit")
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        raise HTTPException(415, "The uploaded file is not a valid supported image")

    extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[image_format]
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f"doctor_{user.id}_{uuid4().hex}.{extension}"
    destination = UPLOAD_ROOT / filename
    try:
        destination.write_bytes(processed)
        previous_avatar = user.avatar_url
        user.avatar_url = f"/uploads/doctor_avatars/{filename}"
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise

    _remove_previous_local_avatar(previous_avatar)
    return doctor_data(user)

@router.get("/doctors/{doctor_id}", response_model=DoctorOut, tags=["Doctors"])
def doctor_detail(doctor_id: int, db: Session = Depends(get_db)):
    d = db.query(User).options(joinedload(User.specialty)).filter(User.id == doctor_id, User.role == "doctor", User.is_active.is_(True)).first()
    if not d: raise HTTPException(404, "Doctor not found")
    return doctor_data(d)

@router.get("/doctors/{doctor_id}/availability", response_model=list[SlotOut], tags=["Availability"])
def doctor_slots(doctor_id: int, date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db)):
    if not db.query(User).filter(User.id == doctor_id, User.role == "doctor", User.is_active.is_(True)).first():
        raise HTTPException(404, "Doctor not found")
    now = datetime.now()
    query = db.query(Availability).filter(
        Availability.doctor_id == doctor_id,
        Availability.is_available.is_(True),
        or_(
            Availability.date > date.today(),
            and_(Availability.date == date.today(), Availability.start_time > now.time().replace(tzinfo=None)),
        ),
    )
    if date_from: query = query.filter(Availability.date >= date_from)
    if date_to: query = query.filter(Availability.date <= date_to)
    return query.order_by(Availability.date, Availability.start_time).all()

@router.post("/availability", response_model=SlotOut, status_code=201, tags=["Doctor Panel", "Availability"])
def create_slot(data: SlotCreate, db: Session = Depends(get_db), doctor: User = Depends(doctor_only)):
    if data.date < date.today(): raise HTTPException(400, "Cannot add availability in the past")
    if data.date == date.today() and data.start_time <= datetime.now().time().replace(tzinfo=None):
        raise HTTPException(400, "Availability must start in the future")
    overlap = db.query(Availability).filter(Availability.doctor_id == doctor.id, Availability.date == data.date, Availability.start_time < data.end_time, Availability.end_time > data.start_time).first()
    if overlap: raise HTTPException(409, "This slot overlaps another availability slot")
    slot = Availability(doctor_id=doctor.id, date=data.date, start_time=data.start_time, end_time=data.end_time)
    db.add(slot)
    try:
        db.commit()
        db.refresh(slot)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A slot already exists at this time")
    return slot

@router.get("/availability/me", response_model=list[SlotOut], tags=["Doctor Panel", "Availability"])
def my_slots(date_from: date | None = None, db: Session = Depends(get_db), doctor: User = Depends(doctor_only)):
    query = db.query(Availability).filter(Availability.doctor_id == doctor.id)
    if date_from: query = query.filter(Availability.date >= date_from)
    return query.order_by(Availability.date, Availability.start_time).all()


@router.delete(
    "/availability/{slot_id}",
    tags=["Doctor Panel", "Availability"],
)
def delete_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    doctor: User = Depends(doctor_only),
):
    slot = (
        db.query(Availability)
        .filter(
            Availability.id == slot_id,
            Availability.doctor_id == doctor.id,
        )
        .first()
    )

    if not slot:
        raise HTTPException(404, "Availability slot not found")

    if slot.appointments:
        raise HTTPException(
            409,
            "This slot has appointment history and cannot be deleted",
        )

    db.delete(slot)
    db.commit()

    return {"message": "Availability deleted"}


# PATIENT PANEL
@router.get("/patients/me", response_model=UserOut, tags=["Patient Panel"])
def patient_me(user: User = Depends(patient_only)):
    return user

@router.patch("/patients/me", response_model=UserOut, tags=["Patient Panel"])
def patient_profile(data: ProfileUpdate, db: Session = Depends(get_db), user: User = Depends(patient_only)):
    return update_profile(db, user, data)

@router.get("/patients/me/appointments", response_model=list[AppointmentOut], tags=["Patient Panel"])
def patient_history(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(patient_only)):
    query = appointment_list_query(db).filter(Appointment.patient_id == user.id)
    if status: query = query.filter(Appointment.status == status)
    rows = query.order_by(Appointment.date.desc(), Appointment.start_time.desc()).all()
    return [appointment_dict(a) for a in rows]


@router.post(
    "/appointments",
    response_model=AppointmentOut,
    status_code=201,
    tags=["Patient Panel", "Appointments"],
)
def book(
    data: BookingCreate,
    db: Session = Depends(get_db),
    patient: User = Depends(patient_only),
):
    slot = (
        db.query(Availability)
        .filter(Availability.id == data.availability_id)
        .first()
    )

    if not slot:
        raise HTTPException(404, "Availability slot not found")

    if not _slot_is_in_future(slot):
        raise HTTPException(400, "Cannot book an appointment in the past")
    if slot.doctor is None or slot.doctor.role != "doctor" or not slot.doctor.is_active:
        raise HTTPException(409, "This doctor is not currently accepting appointments")

    updated_count = (
        db.query(Availability)
        .filter(
            Availability.id == data.availability_id,
            Availability.is_available.is_(True),
        )
        .update(
            {Availability.is_available: False},
            synchronize_session=False,
        )
    )

    if updated_count != 1:
        db.rollback()
        raise HTTPException(
            409,
            "This time slot is unavailable. Please refresh availability.",
        )
    slot.is_available = False

    item = Appointment(
        patient_id=patient.id,
        doctor_id=slot.doctor_id,
        availability_id=slot.id,
        date=slot.date,
        start_time=slot.start_time,
        end_time=slot.end_time,
        reason=data.reason,
        status="pending",
    )

    db.add(item)

    try:
        db.commit()
        db.refresh(item)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409,
            "Could not book this appointment. Please refresh and try again.",
        )

    return appointment_dict(get_appointment(db, item.id))


@router.get("/appointments/me", response_model=list[AppointmentOut], tags=["Patient Panel", "Appointments"])
def patient_appointments(status: str | None = None, db: Session = Depends(get_db), patient: User = Depends(patient_only)):
    query = appointment_list_query(db).filter(Appointment.patient_id == patient.id)
    if status: query = query.filter(Appointment.status == status)
    return [appointment_dict(a) for a in query.order_by(Appointment.date.desc(), Appointment.start_time.desc()).all()]

@router.get("/appointments/{appointment_id}", response_model=AppointmentOut, tags=["Appointments"])
def appointment_detail(appointment_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = get_appointment(db, appointment_id)
    if user.role == "patient" and item.patient_id != user.id: raise HTTPException(404, "Appointment not found")
    if user.role == "doctor" and item.doctor_id != user.id: raise HTTPException(404, "Appointment not found")
    return appointment_dict(item)

@router.post("/appointments/{appointment_id}/cancel", response_model=AppointmentOut, tags=["Patient Panel", "Appointments"])
def cancel(appointment_id: int, data: CancelInput, db: Session = Depends(get_db), patient: User = Depends(patient_only)):
    item = db.query(Appointment).filter(Appointment.id == appointment_id, Appointment.patient_id == patient.id).first()
    if not item: raise HTTPException(404, "Appointment not found")
    if item.status not in ("pending", "confirmed"): raise HTTPException(409, "Only pending or confirmed appointments can be cancelled")
    if not _slot_is_in_future(item.slot):
        raise HTTPException(409, "An appointment that has already started cannot be cancelled")
    item.status = "cancelled"; item.cancellation_reason = data.reason; item.slot.is_available = True
    db.commit()
    return appointment_dict(get_appointment(db, item.id))

@router.post("/appointments/{appointment_id}/reschedule", response_model=AppointmentOut, tags=["Patient Panel", "Appointments"])
def reschedule(appointment_id: int, data: RescheduleInput, db: Session = Depends(get_db), patient: User = Depends(patient_only)):
    item = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.patient_id == patient.id,
    ).first()
    if not item:
        raise HTTPException(404, "Appointment not found")
    if item.status not in ("pending", "confirmed"):
        raise HTTPException(409, "This appointment cannot be rescheduled")
    if not _slot_is_in_future(item.slot):
        raise HTTPException(409, "An appointment that has already started cannot be rescheduled")
    if data.availability_id == item.availability_id:
        raise HTTPException(400, "Choose a different time slot")

    new_slot = db.query(Availability).filter(Availability.id == data.availability_id).first()
    if not new_slot or not _slot_is_in_future(new_slot):
        raise HTTPException(409, "New slot is unavailable or has already started")
    if new_slot.doctor_id != item.doctor_id:
        raise HTTPException(400, "Choose another available time with the same doctor")
    if new_slot.doctor is None or not new_slot.doctor.is_active:
        raise HTTPException(409, "This doctor is not currently accepting appointments")

    # Atomically claim the replacement slot before releasing the current one.
    claimed = db.query(Availability).filter(
        Availability.id == new_slot.id,
        Availability.is_available.is_(True),
    ).update({Availability.is_available: False}, synchronize_session=False)
    if claimed != 1:
        db.rollback()
        raise HTTPException(409, "New slot is no longer available. Please refresh.")
    new_slot.is_available = False

    old_slot = item.slot
    old_slot.is_available = True
    item.availability_id = new_slot.id
    item.slot = new_slot
    item.doctor_id = new_slot.doctor_id
    item.date = new_slot.date
    item.start_time = new_slot.start_time
    item.end_time = new_slot.end_time
    item.status = "pending"
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Could not reschedule. Please refresh and try again.")
    return appointment_dict(get_appointment(db, item.id))

# DOCTOR APPOINTMENT WORKFLOW
@router.get("/doctor/appointments", response_model=list[AppointmentOut], tags=["Doctor Panel", "Appointments"])
def doctor_appointments(date_filter: date | None = None, status: str | None = None, db: Session = Depends(get_db), doctor: User = Depends(doctor_only)):
    query = appointment_list_query(db).filter(Appointment.doctor_id == doctor.id)
    if date_filter: query = query.filter(Appointment.date == date_filter)
    if status: query = query.filter(Appointment.status == status)
    return [appointment_dict(a) for a in query.order_by(Appointment.date, Appointment.start_time).all()]

@router.patch("/doctor/appointments/{appointment_id}", response_model=AppointmentOut, tags=["Doctor Panel", "Appointments"])
def doctor_decision(appointment_id: int, data: DoctorDecision, db: Session = Depends(get_db), doctor: User = Depends(doctor_only)):
    item = db.query(Appointment).filter(Appointment.id == appointment_id, Appointment.doctor_id == doctor.id).first()
    if not item: raise HTTPException(404, "Appointment not found")
    if item.status not in ("pending", "confirmed"):
        raise HTTPException(409, "Appointment is already closed")
    if data.status == "confirmed" and item.status != "pending":
        raise HTTPException(409, "Only pending appointments can be confirmed")
    if data.status == "completed" and item.status != "confirmed":
        raise HTTPException(409, "Only confirmed appointments can be completed")
    item.status = data.status
    if data.doctor_notes is not None: item.doctor_notes = data.doctor_notes
    if data.status == "rejected": item.slot.is_available = True
    db.commit()
    return appointment_dict(get_appointment(db, item.id))

# ROLE DASHBOARDS
@router.get("/dashboards/patient", tags=["Patient Panel", "Dashboards"])
def patient_dashboard(db: Session = Depends(get_db), patient: User = Depends(patient_only)):
    q = appointment_list_query(db).filter(Appointment.patient_id == patient.id)
    upcoming = q.filter(Appointment.date >= date.today(), Appointment.status.in_(("pending", "confirmed"))).order_by(Appointment.date, Appointment.start_time).limit(6).all()
    return {"role": "patient", "metrics": {"total": q.count(), "upcoming": q.filter(Appointment.date >= date.today(), Appointment.status.in_(("pending", "confirmed"))).count(), "completed": q.filter(Appointment.status == "completed").count(), "cancelled": q.filter(Appointment.status == "cancelled").count()}, "upcoming_appointments": [appointment_dict(a) for a in upcoming]}

@router.get("/dashboards/doctor", tags=["Doctor Panel", "Dashboards"])
def doctor_dashboard(db: Session = Depends(get_db), doctor: User = Depends(doctor_only)):
    q = appointment_list_query(db).filter(Appointment.doctor_id == doctor.id)
    today_q = q.filter(Appointment.date == date.today())
    now = datetime.now()
    upcoming_filter = or_(
        Appointment.date > date.today(),
        and_(Appointment.date == date.today(), Appointment.start_time > now.time().replace(tzinfo=None)),
    )
    upcoming = q.filter(upcoming_filter, Appointment.status.in_(("pending", "confirmed"))).order_by(Appointment.date, Appointment.start_time).limit(8).all()
    return {"role": "doctor", "metrics": {"total": q.count(), "today": today_q.count(), "pending": q.filter(Appointment.status == "pending").count(), "completed": q.filter(Appointment.status == "completed").count()}, "upcoming_appointments": [appointment_dict(a) for a in upcoming]}

# ADMIN PANEL
@router.get("/admin/dashboard", tags=["Admin Panel", "Dashboards"])
def admin_dashboard(db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    now = datetime.now()
    upcoming_filter = or_(
        Appointment.date > date.today(),
        and_(Appointment.date == date.today(), Appointment.start_time > now.time().replace(tzinfo=None)),
    )
    upcoming = appointment_list_query(db).filter(upcoming_filter, Appointment.status.in_(("pending", "confirmed"))).order_by(Appointment.date, Appointment.start_time).limit(10).all()
    return {"role": "admin", "metrics": {"patients": db.query(User).filter(User.role == "patient").count(), "doctors": db.query(User).filter(User.role == "doctor").count(), "appointments": db.query(Appointment).count(), "pending": db.query(Appointment).filter(Appointment.status == "pending").count(), "confirmed": db.query(Appointment).filter(Appointment.status == "confirmed").count(), "completed": db.query(Appointment).filter(Appointment.status == "completed").count(), "specialties": db.query(Specialty).count()}, "upcoming_appointments": [appointment_dict(a) for a in upcoming]}

@router.get("/admin/users", response_model=list[UserOut], tags=["Admin Panel"])
def admin_users(role: str | None = None, q: str | None = None, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    query = db.query(User)
    if role in ("patient", "doctor", "admin"): query = query.filter(User.role == role)
    if q:
        term = f"%{q}%"
        query = query.filter((User.username.ilike(term)) | (User.email.ilike(term)) | (User.first_name.ilike(term)) | (User.last_name.ilike(term)))
    return query.order_by(User.created_at.desc()).all()

@router.patch("/admin/users/{user_id}/active", response_model=UserOut, tags=["Admin Panel"])
def set_active(user_id: int, data: AdminUserActive, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(404, "User not found")
    if target.id == admin.id and not data.is_active:
        raise HTTPException(400, "You cannot deactivate your own account")
    target.is_active = data.is_active
    db.commit()
    db.refresh(target)
    return target

@router.delete("/admin/users/{user_id}", tags=["Admin Panel"])
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target: raise HTTPException(404, "User not found")
    if target.id == admin.id: raise HTTPException(400, "You cannot delete your own account")
    if target.role == "doctor" and (target.doctor_appointments or target.slots):
        raise HTTPException(409, "Doctor has schedule/history records. Deactivate the account instead to preserve history.")
    if target.role == "patient" and target.patient_appointments:
        raise HTTPException(409, "Patient has appointment history. Deactivate the account instead to preserve history.")
    db.delete(target); db.commit()
    return {"message": "User deleted"}

@router.get("/admin/appointments", response_model=list[AppointmentOut], tags=["Admin Panel"])
def admin_appointments(status: str | None = None, date_filter: date | None = None, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    query = appointment_list_query(db)
    if status: query = query.filter(Appointment.status == status)
    if date_filter: query = query.filter(Appointment.date == date_filter)
    return [appointment_dict(a) for a in query.order_by(Appointment.date.desc(), Appointment.start_time).all()]

@router.patch("/admin/appointments/{appointment_id}", response_model=AppointmentOut, tags=["Admin Panel"])
def admin_appointment_update(appointment_id: int, data: AdminStatus, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    item = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not item:
        raise HTTPException(404, "Appointment not found")

    if item.status in ("completed", "cancelled", "rejected") and data.status != item.status:
        raise HTTPException(409, "Closed appointments cannot be reopened or changed")
    if data.status == "completed" and item.status != "confirmed":
        raise HTTPException(409, "Only confirmed appointments can be completed")
    if data.status == item.status:
        if data.doctor_notes is not None and data.doctor_notes != item.doctor_notes:
            item.doctor_notes = data.doctor_notes
            db.commit()
        return appointment_dict(get_appointment(db, item.id))

    if data.status in ("cancelled", "rejected"):
        item.slot.is_available = True
    elif data.status in ("confirmed", "completed"):
        conflicting = db.query(Appointment).filter(
            Appointment.availability_id == item.availability_id,
            Appointment.id != item.id,
            Appointment.status.in_(("pending", "confirmed")),
        ).first()
        if conflicting:
            raise HTTPException(409, "This slot has already been booked by another appointment")
        item.slot.is_available = False

    item.status = data.status
    if data.doctor_notes is not None:
        item.doctor_notes = data.doctor_notes
    db.commit()
    return appointment_dict(get_appointment(db, item.id))

@router.get("/admin/patients", response_model=list[UserOut], tags=["Admin Panel"])
def admin_patients(db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    return db.query(User).filter(User.role == "patient").order_by(User.created_at.desc()).all()

@router.get("/admin/doctors", response_model=list[DoctorOut], tags=["Admin Panel"])
def admin_doctors(db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    rows = db.query(User).options(joinedload(User.specialty)).filter(User.role == "doctor").order_by(User.last_name).all()
    return [doctor_data(d) for d in rows]
