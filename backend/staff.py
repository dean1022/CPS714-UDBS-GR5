#Staff mode rules for the University Digital Borrowing System
#staff get three perks: no due date, a higher loan limit, and priority in the hold queue
#every staff rule lives in the staff_*.py files so the student code stays untouched

from database import get_connection

#which account types count as staff
#the users table only allows 'student' and 'faculty' right now, so faculty are the staff
STAFF_STATUSES = ("faculty", "staff")

STAFF_MAX_LOANS = 60  # students get 30 (MAX_LOANS in borrow.py)

#the loan table needs a due date, so staff loans get one so far away it never arrives
NO_DUE_DATE = "9999-12-31 23:59:59"

def is_staff(university_id):
    #True if this user has a staff account
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT status FROM users WHERE university_id = %s",
            (university_id,),
        ).fetchone()
    finally:
        conn.close()
    return row is not None and row["status"] in STAFF_STATUSES

def has_no_due_date(due_at):
    return due_at == NO_DUE_DATE
