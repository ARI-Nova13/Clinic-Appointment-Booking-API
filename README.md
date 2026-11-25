# MediCare – Clinic Appointment Booking API

A RESTful clinic appointment booking backend built with **FastAPI, SQLAlchemy, and SQLite**. MediCare provides a complete API for managing patients, doctors, administrators, medical specialties, doctor availability, and clinic appointments.

The API supports JWT authentication, role-based authorization, appointment scheduling, rescheduling, cancellation, and doctor profile image uploads.

## Features

### Authentication and Authorization
- JWT access-token authentication.
- Secure password hashing using Argon2.
- Role-based access control for patients, doctors, and administrators.
- Protected endpoints and current-user authentication.
- Patient and doctor registration.
- Persistent user account management.

### Patient Management
- Patient registration and authentication.
- View and update patient profiles.
- Browse doctors and medical specialties.
- View doctor availability.
- Book appointments.
- View personal appointments.
- Cancel and reschedule appointments.
- Access patient dashboard information.

### Doctor Management
- Doctor registration and profile management.
- Update professional information.
- Upload and manage doctor profile pictures.
- Manage medical specialties and clinic information.
- Create and manage availability slots.
- View and manage personal appointments.
- Confirm, reject, and complete appointments.
- Access doctor dashboard information.

### Administrator Management
- Administrative dashboard and statistics.
- View and manage users.
- Activate and deactivate accounts.
- Manage doctors and patients.
- Manage medical specialties.
- View and manage appointments.

### Appointment Management
- Doctor availability scheduling.
- Appointment booking and status management.
- Appointment cancellation and rescheduling.
- Availability restoration after cancellation.
- Prevention of duplicate slot bookings.
- Scheduling validation and appointment ownership checks.
- Protection against invalid appointment transitions.

### Doctor Profile Images
- Multipart image upload.
- Doctor-only upload authorization.
- JPEG, PNG, and WebP support.
- Maximum upload size of 5 MB.
- Server-generated image filenames.
- Static image serving through the API.

## Tech Stack

| Technology | Purpose |
|---|---|
| Python | Programming language |
| FastAPI | REST API framework |
| SQLAlchemy | ORM and database management |
| SQLite | Default development database |
| Pydantic | Data validation and schemas |
| Pydantic Settings | Environment configuration |
| JWT | Authentication |
| HTTP Bearer | Token-based authorization |
| pwdlib / Argon2 | Password hashing |
| Uvicorn | ASGI server |
| Pillow | Image processing and validation |
| python-multipart | Image upload handling |

## Project Structure

```text
Clinic-Appointment-Booking-API/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── security.py
│   ├── utils.py
│   │
│   └── routers/
│       ├── __init__.py
│       └── api.py
│
├── create_admin.py
├── migrate_appointments.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Authentication

The API uses JWT access tokens.

### Login

```http
POST /api/v1/auth/login
```

The login endpoint accepts username and password and returns an access token and authenticated user information.

Use the token for protected endpoints:

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Authentication endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register/patient` | Register a patient |
| POST | `/api/v1/auth/register/doctor` | Register a doctor |
| POST | `/api/v1/auth/login` | Authenticate a user |
| GET | `/api/v1/auth/me` | Get current authenticated user |

## API Endpoints

All application endpoints use the `/api/v1` prefix.

### Medical Specialties

| Method | Endpoint | Description |
|---|---|---|
| GET | `/specialties` | List specialties |
| POST | `/specialties` | Create a specialty (admin) |
| PATCH | `/specialties/{id}` | Update a specialty (admin) |
| DELETE | `/specialties/{id}` | Delete a specialty (admin) |

### Doctors

| Method | Endpoint | Description |
|---|---|---|
| GET | `/doctors` | Browse and search doctors |
| GET | `/doctors/{id}` | Get doctor details |
| GET | `/doctors/me` | Get current doctor profile |
| PATCH | `/doctors/me` | Update doctor profile |
| GET | `/doctors/{id}/availability` | Get doctor's available slots |
| POST | `/doctors/me/avatar` | Upload doctor profile picture |

### Patients

| Method | Endpoint | Description |
|---|---|---|
| GET | `/patients/me` | Get patient profile |
| PATCH | `/patients/me` | Update patient profile |
| GET | `/patients/me/appointments` | Get patient appointments |

### Availability

| Method | Endpoint | Description |
|---|---|---|
| POST | `/availability` | Create an availability slot |
| GET | `/availability/me` | Get doctor's availability |
| DELETE | `/availability/{slot_id}` | Delete an availability slot |

### Appointments

| Method | Endpoint | Description |
|---|---|---|
| POST | `/appointments` | Book an appointment |
| GET | `/appointments/me` | Get current user's appointments |
| GET | `/appointments/{id}` | Get appointment details |
| POST | `/appointments/{id}/cancel` | Cancel an appointment |
| POST | `/appointments/{id}/reschedule` | Reschedule an appointment |
| GET | `/doctor/appointments` | Get doctor's appointments |
| PATCH | `/doctor/appointments/{id}` | Update appointment status |

### Dashboards

| Method | Endpoint | Description |
|---|---|---|
| GET | `/dashboards/patient` | Patient dashboard |
| GET | `/dashboards/doctor` | Doctor dashboard |
| GET | `/admin/dashboard` | Administrator dashboard |

### Administrator Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/admin/users` | List users |
| GET | `/admin/doctors` | List doctors |
| GET | `/admin/patients` | List patients |
| GET | `/admin/appointments` | List appointments |
| PATCH | `/admin/users/{id}/active` | Activate or deactivate user |
| DELETE | `/admin/users/{id}` | Delete user |
| PATCH | `/admin/appointments/{id}` | Update appointment |

For request parameters, payload schemas, response models, and permissions, use the interactive API documentation.

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/ARK13-org/Clinic-Appointment-Booking-API.git
cd Clinic-Appointment-Booking-API
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file from the example:

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux / macOS:

```bash
cp .env.example .env
```

Configure your environment:

```env
APP_NAME=MediCare Appointment Booking API
DATABASE_URL=sqlite:///./clinic.db
SECRET_KEY=YOUR_SECURE_RANDOM_SECRET
ACCESS_TOKEN_EXPIRE_MINUTES=60
APP_ENV=development
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

Replace the secret with a strong, unique value of at least 32 characters.

Never commit your real `.env` file.

### 5. Run the application

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at:

```text
http://127.0.0.1:8000
```

## API Documentation

FastAPI automatically generates interactive API documentation.

| Documentation | URL |
|---|---|
| Swagger UI | http://127.0.0.1:8000/docs |
| ReDoc | http://127.0.0.1:8000/redoc |
| Health Check | http://127.0.0.1:8000/health |

Use Swagger UI to authenticate and test the API endpoints.

## Appointment Workflow

The appointment system follows this general workflow:

```text
Doctor
   |
   v
Create Availability
   |
   v
Available Time Slots
   |
   v
Patient Selects a Slot
   |
   v
Book Appointment
   |
   v
Doctor Reviews Appointment
   |
   v
Confirm / Reject
   |
   v
Complete or Cancel
```

Rescheduling reserves the replacement slot before releasing the previous slot. This helps prevent losing the original booking when a replacement cannot be reserved.

Cancelled appointment slots can become available again, subject to scheduling and appointment-history rules.

## Booking Integrity and Validation

The API includes safeguards for appointment scheduling:

- Conditional database updates prevent multiple patients from claiming the same available slot.
- Past dates and time slots that have already started cannot be booked.
- Availability creation validates dates and times.
- Rescheduling preserves the original doctor.
- Rescheduling reserves the replacement slot before releasing the old slot.
- Patients cannot cancel appointments after they have started.
- Appointment actions enforce role and ownership restrictions.

## Security Considerations

- Passwords are hashed before storage.
- JWT tokens protect authenticated endpoints.
- Role-based authorization restricts access to sensitive operations.
- Doctor image uploads are restricted to doctor accounts.
- Uploaded images are validated and receive server-generated filenames.
- Environment variables hold secrets and configuration.
- Local databases, uploaded files, and private configuration are excluded from Git.

For production deployments, use HTTPS, a strong unique secret, explicit CORS origins, persistent storage, regular backups, and an appropriate production ASGI configuration.

## What This Project Demonstrates

- REST API architecture and development.
- FastAPI routing and dependency injection.
- SQLAlchemy ORM and database relationships.
- Pydantic schemas and request validation.
- JWT authentication and role-based authorization.
- Secure password hashing.
- CRUD operations.
- Appointment scheduling and business logic.
- Transactional booking and availability management.
- File uploads and image validation.
- API documentation and backend/frontend integration.

## Developer

**Alireza Koupaei**

GitHub: [ARK13-org](https://github.com/ARK13-org)

Repository: [Clinic Appointment Booking API](https://github.com/ARK13-org/Clinic-Appointment-Booking-API)
