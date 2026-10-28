# init_db.py
# Run this file once to create the database and tables.

from database.db import init_db, get_connection, DB_PATH

init_db()
print("Database created at:", DB_PATH)

# Ask SQLite to list the tables it now contains.
conn = get_connection()
rows = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
).fetchall()
conn.close()

print("Tables found:")
for row in rows:
    print(" -", row["name"])