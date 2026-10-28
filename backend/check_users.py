# check_users.py
# Shows the users stored in the database (for checking only).

from database.db import get_connection

conn = get_connection()
rows = conn.execute(
    "SELECT user_id, full_name, role, password_hash FROM users"
).fetchall()
conn.close()

for row in rows:
    print(row["user_id"], "|", row["role"], "|", row["full_name"])
    # Show only the first 40 characters of the hash.
    print("   hash starts with:", row["password_hash"][:40], "...")