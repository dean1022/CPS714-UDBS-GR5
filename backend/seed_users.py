#Demo accounts for the University Digital Borrowing System
#staff_demo.py reads STUDENTS and FACULTY from here (the team's original seed_users.py wasn't in the upload,
#so this one is rebuilt from supabase/seed.sql, which is what the live database was seeded with)
#each row is (university_id, email, first_name, last_name)

import pathlib
from database import get_connection

DEMO_PASSWORD = "Library2026!"

#the status in seed.sql before staff_demo.apply_demo_roles() runs
STUDENTS = [
    ('501000001', 'ava.chen@torontomu.ca', 'Ava', 'Chen'),
    ('501000002', 'liam.singh@torontomu.ca', 'Liam', 'Singh'),
    ('501000003', 'noor.haddad@torontomu.ca', 'Noor', 'Haddad'),
    ('501000004', 'ethan.tremblay@torontomu.ca', 'Ethan', 'Tremblay'),
    ('501000005', 'alex.ferreira@torontomu.ca', 'Alex', 'Ferreira'),
    ('501000006', 'jordan.reyes@torontomu.ca', 'Jordan', 'Reyes'),
    ('501000007', 'priya.patel@torontomu.ca', 'Priya', 'Patel'),
    ('501000008', 'lucas.moreau@torontomu.ca', 'Lucas', 'Moreau'),
    ('501000009', 'sofia.rossi@torontomu.ca', 'Sofia', 'Rossi'),
    ('501000010', 'daniel.kim@torontomu.ca', 'Daniel', 'Kim'),
]

FACULTY = [
    ('700000001', 'elaine.whitfield@torontomu.ca', 'Elaine', 'Whitfield'),
    ('700000002', 'marcus.adeyemi@torontomu.ca', 'Marcus', 'Adeyemi'),
    ('700000003', 'hana.yamamoto@torontomu.ca', 'Hana', 'Yamamoto'),
    ('700000004', 'robert.gallagher@torontomu.ca', 'Robert', 'Gallagher'),
    ('700000005', 'fatima.rahman@torontomu.ca', 'Fatima', 'Rahman'),
]

SEED_FILE = pathlib.Path(__file__).resolve().parent.parent / "supabase" / "seed.sql"

def seed():
    #adds the demo accounts (the users rows from seed.sql), used by the tests
    conn = get_connection()
    for line in SEED_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith('INSERT INTO "users"'):
            conn.execute(line.rstrip(";"))
    conn.commit()
    conn.close()
