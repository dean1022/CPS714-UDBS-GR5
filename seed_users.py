#10 students, 5 faculty dummy users
#Every demo account uses the same password to login easily "Library2026!"

from auth import hash_password
from database import get_connection, init_db

DEMO_PASSWORD = "Library2026!"

# (university id, first name, last name, pronouns)
STUDENTS = [
    ("501000001", "Ava", "Chen", "she/they"),
    ("501000002", "Liam", "Singh", "he/him"),
    ("501000003", "Noor", "Haddad", "she/her"),
    ("501000004", "Ethan", "Tremblay", "he/him"),
    ("501000005", "Alex", "Ferreira", "they/them"),
    ("501000006", "Jordan", "Reyes", "they/them"),
    ("501000007", "Priya", "Patel", "she/her"),
    ("501000008", "Lucas", "Moreau", "he/they"),
    ("501000009", "Sofia", "Rossi", "she/her"),
    ("501000010", "Daniel", "Kim", "he/him"),
]

FACULTY = [
    ("700000001", "Elaine", "Whitfield", "she/her"),
    ("700000002", "Marcus", "Adeyemi", "he/him"),
    ("700000003", "Hana", "Yamamoto", "she/her"),
    ("700000004", "Robert", "Gallagher", "he/him"),
    ("700000005", "Fatima", "Rahman", "she/her"),
]

def seed():
    init_db()
    rows = []
    for status, people in (("student", STUDENTS), ("faculty", FACULTY)):
        for uid, first, last, pronouns in people:
            rows.append((
                uid,
                f"{first.lower()}.{last.lower()}@torontomu.ca",
                hash_password(DEMO_PASSWORD),
                first, last, first, pronouns, status,
            ))
    with get_connection() as conn:
        conn.executemany(
            """INSERT OR REPLACE INTO users
               (university_id, email, password_hash, first_name, last_name,
                display_name, pronouns, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
    print(f"Seeded {len(STUDENTS)} students and {len(FACULTY)} faculty.")
    print(f"Demo password for every account: {DEMO_PASSWORD}")
    print(f"Example student login: {STUDENTS[0][0]}  |  faculty login: {FACULTY[0][0]}")

if __name__ == "__main__":
    seed()
