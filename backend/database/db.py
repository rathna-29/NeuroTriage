# db.py
# SQLite database connection and table creation for NeuroTriage.

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "backend" / "database" / "neurotriage.db"


def get_connection():
    """
    Create and return a SQLite database connection.

    sqlite3.Row allows us to access columns by name, for example:
    row["patient_code"]
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """
    Create all NeuroTriage database tables if they do not already exist.
    Existing data is preserved.
    """

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = get_connection()

    try:
        conn.executescript(
            """
            -- =====================================================
            -- USERS
            -- =====================================================
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT NOT NULL UNIQUE,
                password    TEXT NOT NULL,
                role        TEXT NOT NULL CHECK (role IN ('doctor', 'clinician')),
                full_name   TEXT NOT NULL,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );


            -- =====================================================
            -- PATIENTS
            -- =====================================================
            CREATE TABLE IF NOT EXISTS patients (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_code TEXT NOT NULL UNIQUE,
                age         INTEGER NOT NULL CHECK (age BETWEEN 0 AND 120),
                sex         TEXT NOT NULL,
                created_by  INTEGER NOT NULL,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (created_by) REFERENCES users (id)
            );


            -- =====================================================
            -- AUDIT LOGS
            -- =====================================================
            CREATE TABLE IF NOT EXISTS audit_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id  INTEGER,
                user_id     INTEGER NOT NULL,
                action      TEXT NOT NULL,
                details     TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (patient_id) REFERENCES patients (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            );


            -- =====================================================
            -- VITALS
            -- =====================================================
            CREATE TABLE IF NOT EXISTS vitals (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id        INTEGER NOT NULL,
                recorded_by       INTEGER NOT NULL,
                heart_rate        REAL NOT NULL,
                systolic_bp       REAL NOT NULL,
                diastolic_bp      REAL NOT NULL,
                spo2              REAL NOT NULL,
                temperature_c     REAL NOT NULL,
                respiratory_rate  REAL,
                recorded_at       TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (patient_id) REFERENCES patients (id),
                FOREIGN KEY (recorded_by) REFERENCES users (id)
            );


            -- =====================================================
            -- CLINICAL RECORDS
            -- =====================================================
            CREATE TABLE IF NOT EXISTS clinical_records (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id            INTEGER NOT NULL,
                recorded_by           INTEGER NOT NULL,
                symptoms              TEXT NOT NULL,
                symptom_onset         TEXT,
                medical_history       TEXT,
                existing_conditions   TEXT,
                clinical_observations TEXT,
                recorded_at            TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (patient_id) REFERENCES patients (id),
                FOREIGN KEY (recorded_by) REFERENCES users (id)
            );


            -- =====================================================
            -- EEG RECORDS
            -- =====================================================
            CREATE TABLE IF NOT EXISTS eeg_records (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id        INTEGER NOT NULL,
                uploaded_by       INTEGER NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename   TEXT NOT NULL,
                created_at        TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (patient_id) REFERENCES patients (id),
                FOREIGN KEY (uploaded_by) REFERENCES users (id)
            );


            -- =====================================================
            -- PRIORITY MAPPING
            -- Project-defined mapping between EEG model classes
            -- and AI-assisted priority indications.
            -- =====================================================
            CREATE TABLE IF NOT EXISTS priority_mapping (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                model_class     TEXT NOT NULL UNIQUE,
                priority_label  TEXT NOT NULL
            );


            -- =====================================================
            -- PREDICTIONS
            -- =====================================================
            CREATE TABLE IF NOT EXISTS predictions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id       INTEGER NOT NULL,
                eeg_record_id    INTEGER NOT NULL,
                created_by       INTEGER NOT NULL,
                predicted_class  TEXT NOT NULL,
                priority_label   TEXT NOT NULL,
                probability      REAL NOT NULL CHECK (probability BETWEEN 0 AND 1),
                created_at       TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (patient_id) REFERENCES patients (id),
                FOREIGN KEY (eeg_record_id) REFERENCES eeg_records (id),
                FOREIGN KEY (created_by) REFERENCES users (id)
            );


            -- =====================================================
            -- STEP 17: SIMULATED MONITORING RECORDS
            -- One row = one simulated monitoring measurement.
            -- These records are kept separate from real EEG uploads.
            -- =====================================================
            CREATE TABLE IF NOT EXISTS monitoring_records (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id       INTEGER NOT NULL,
                created_by       INTEGER NOT NULL,
                run_id           TEXT NOT NULL,
                scenario         TEXT NOT NULL,
                step_index       INTEGER NOT NULL,
                sim_source_class TEXT NOT NULL,
                predicted_class  TEXT NOT NULL,
                priority_label   TEXT NOT NULL,
                probability      REAL NOT NULL CHECK (probability BETWEEN 0 AND 1),
                mean_std         REAL NOT NULL,
                created_at       TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (patient_id) REFERENCES patients (id),
                FOREIGN KEY (created_by) REFERENCES users (id)
            );
            """
        )

        conn.commit()

    finally:
        conn.close()


if __name__ == "__main__":
    init_db()

    print(f"Database created at: {DB_PATH}")

    conn = get_connection()

    try:
        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()

        print("Tables found:")

        for table in tables:
            print(f" - {table['name']}")

    finally:
        conn.close()