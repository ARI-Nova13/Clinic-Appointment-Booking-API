from app.models import Appointment

def appointment_dict(item: Appointment):
    # Load related names safely for response serialization.
    return {
        "id": item.id,
        "patient_id": item.patient_id,
        "doctor_id": item.doctor_id,
        "availability_id": item.availability_id,
        "date": item.date,
        "start_time": item.start_time,
        "end_time": item.end_time,
        "status": item.status,
        "reason": item.reason,
        "doctor_notes": item.doctor_notes,
        "cancellation_reason": item.cancellation_reason,
        "created_at": item.created_at,
        "patient_name": f"{item.patient.first_name} {item.patient.last_name}".strip(),
        "doctor_name": f"{item.doctor.first_name} {item.doctor.last_name}".strip(),
        "doctor_avatar_url": item.doctor.avatar_url,
        "specialty_name": item.doctor.specialty.name if item.doctor.specialty else None,
    }
