#Borrow literature (US-06) for the University Digital Borrowing System

from datetime import datetime, timedelta

from database import get_connection
from auth import TIME_FORMAT
from loans import LoanError, available_slots

LOAN_PERIOD = timedelta(days=14)  # standard loan (BR-01), make it shorter for demos
MAX_LOANS = 30  # max active loans per user (BR-02)

def count_active_loans(university_id):
    #how many loans the user has right now
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM loan WHERE university_id = ? AND status = 'ACTIVE'",
            (university_id,),
        ).fetchone()[0]
    finally:
        conn.close()

def borrow_literature(university_id, literature_id, now=None):
    #borrow an item and add it to the user's personal library
    now = now or datetime.now()

    #available_slots raises LoanError if the lit doesn't exist
    if available_slots(literature_id) <= 0:
        raise LoanError("No access slots available right now. You can place a hold instead.")

    if count_active_loans(university_id) >= MAX_LOANS:
        raise LoanError(f"You've reached the limit of {MAX_LOANS} active loans.")

    conn = get_connection()
    try:
        #can't borrow the same item twice
        already = conn.execute(
            "SELECT loan_id FROM loan WHERE university_id = ? AND literature_id = ? AND status = 'ACTIVE'",
            (university_id, literature_id),
        ).fetchone()

        if already is not None:
            raise LoanError("This item is already in your Personal Library.")

        # loan is due 14 days from now
        due = now + LOAN_PERIOD

        cur = conn.execute(
            "INSERT INTO loan (university_id, literature_id, borrowed_at, due_at, status) "
            "VALUES (?, ?, ?, ?, 'ACTIVE')",
            (university_id, literature_id, now.strftime(TIME_FORMAT), due.strftime(TIME_FORMAT)),
        )
        conn.commit()
        loan_id = cur.lastrowid
    finally:
        conn.close()

    return {
        "message": "Borrowed! It's now in your Personal Library.",
        "loan_id": loan_id,
        "due_at": due.strftime(TIME_FORMAT),
        "available_slots": available_slots(literature_id),
    }
