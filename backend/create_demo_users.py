# create_demo_users.py
# Run this file once to add demo accounts to the database.
# These are SYNTHETIC accounts for development only.

from werkzeug.security import generate_password_hash

from database.db import init_db, get_connection

# Demo accounts: (user_id, full name, password, role)
# These passwords are for local demo use only.
DEMO_USERS = [
    ("DR001", "Dr. Demo Doctor", "Doctor@12345", "doctor"),
    ("CL001", "Demo Clinician", "Clinician@12345", "clinician"),
]

# Make sure the tables exist before we insert anything.
init_db()

conn = get_connection()
try:
    for user_id, full_name, password, role in DEMO_USERS:
        # Skip the account if it already exists.
        existing = conn.execute(
            "SELECT id FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()

        if existing:
            print(f"Already exists, skipped: {user_id}")
            continue

        # Turn the real password into a scrambled hash.
        password_hash = generate_password_hash(password)

        # The ? marks are placeholders. This is how we avoid SQL injection.
        conn.execute(
            "INSERT INTO users (user_id, full_name, password_hash, role) "
            "VALUES (?, ?, ?, ?)",
            (user_id, full_name, password_hash, role),
        )
        print(f"Created: {user_id} ({role})")

    conn.commit()
finally:
    conn.close()

print("Done.")