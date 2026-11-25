
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "clinic.db"
BACKUP_PATH = Path(__file__).resolve().parent / "clinic_backup.db"

if not BACKUP_PATH.exists():
    raise FileNotFoundError(
        "Backup not found. Create clinic_backup.db before migrating."
    )

if not DB_PATH.exists():
    raise FileNotFoundError(f"Database not found: {DB_PATH}")

conn = sqlite3.connect(DB_PATH, timeout=30)

try:
    conn.execute("PRAGMA foreign_keys = OFF")

    conn.execute("BEGIN IMMEDIATE")

    original_count = conn.execute(
        "SELECT COUNT(*) FROM appointments"
    ).fetchone()[0]

    conn.execute("""
        CREATE TABLE appointments_new (
            id INTEGER NOT NULL,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            availability_id INTEGER NOT NULL,
            date DATE NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            status VARCHAR(20) NOT NULL,
            reason VARCHAR(500),
            doctor_notes TEXT,
            cancellation_reason VARCHAR(500),
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(patient_id)
                REFERENCES users (id) ON DELETE RESTRICT,
            FOREIGN KEY(doctor_id)
                REFERENCES users (id) ON DELETE RESTRICT,
            FOREIGN KEY(availability_id)
                REFERENCES availabilities (id) ON DELETE RESTRICT
        )
    """)

    conn.execute("""
        INSERT INTO appointments_new (
            id, patient_id, doctor_id, availability_id,
            date, start_time, end_time, status, reason,
            doctor_notes, cancellation_reason,
            created_at, updated_at
        )
        SELECT
            id, patient_id, doctor_id, availability_id,
            date, start_time, end_time, status, reason,
            doctor_notes, cancellation_reason,
            created_at, updated_at
        FROM appointments
    """)

    copied_count = conn.execute(
        "SELECT COUNT(*) FROM appointments_new"
    ).fetchone()[0]

    if copied_count != original_count:
        raise RuntimeError("Appointment count mismatch. Migration cancelled.")

    conn.execute("DROP TABLE appointments")
    conn.execute("ALTER TABLE appointments_new RENAME TO appointments")

    conn.execute(
        "CREATE INDEX ix_appointments_date ON appointments (date)"
    )
    conn.execute(
        "CREATE INDEX ix_appointments_doctor_date "
        "ON appointments (doctor_id, date)"
    )
    conn.execute(
        "CREATE INDEX ix_appointments_doctor_id "
        "ON appointments (doctor_id)"
    )
    conn.execute(
        "CREATE INDEX ix_appointments_patient_id "
        "ON appointments (patient_id)"
    )
    conn.execute(
        "CREATE INDEX ix_appointments_status ON appointments (status)"
    )

    foreign_key_errors = conn.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if foreign_key_errors:
        raise RuntimeError(
            f"Foreign key errors detected: {foreign_key_errors}"
        )

    conn.commit()

    print("Migration completed successfully!")
    print(f"Preserved appointments: {copied_count}")
    print("The UNIQUE constraint on availability_id has been removed.")

except Exception:
    conn.rollback()
    raise

finally:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()
