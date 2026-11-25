# MediCare FastAPI backend

## Local setup

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Replace `SECRET_KEY` in `.env` with a random secret of at least 32 characters. Keep `.env`, database files, and uploaded images out of source control.

Start the API:

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`
- API prefix: `/api/v1`
- Doctor profile images are served from `/uploads/doctor_avatars/`.

Binding to `0.0.0.0` is for local network development so an Android emulator or physical phone can reach the API. Do not expose this development server directly to the public internet. Use a production ASGI deployment behind HTTPS for release builds.

## Important configuration

- `APP_ENV=development` enables localhost CORS ports for local Flutter web work.
- In production set `APP_ENV=production`, a strong unique `SECRET_KEY`, and explicit comma-separated `CORS_ORIGINS`.
- Configure `DATABASE_URL` for the selected database. `create_all` initializes new tables but is not a schema migration system; use explicit migrations when changing existing database schemas.
- The avatar upload endpoint is doctor-role-only, accepts JPEG/PNG/WebP files up to 5 MB, and generates server-side filenames.
- Production should serve HTTPS and should store user-uploaded files on persistent storage with backups.

## API integration updates

- `PATCH /api/v1/admin/users/{user_id}/active` accepts JSON: `{"is_active": true|false}`.
- `POST /api/v1/doctors/me/avatar` accepts multipart form data with field name `file`.
- `POST /api/v1/appointments/{appointment_id}/reschedule` reserves the new slot before freeing the old slot.

## Booking integrity

- The public availability endpoint excludes slots that have already started today.
- Booking claims a slot with a conditional database update, so two patients cannot both reserve the same available slot.
- Rescheduling keeps the same doctor, requires both appointments to be in the future, reserves the replacement before releasing the old slot, and returns the appointment to `pending` for doctor confirmation.
- Patient cancellation is blocked once an appointment has started.
- Admin activation uses a JSON request body with `is_active`.

