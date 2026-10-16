#Early return (US-09) and automatic return (US-05) for the University Digital Borrowing System

from datetime import datetime

from database import get_connection
from auth import TIME_FORMAT

class LoanError(Exception):
    #raised when a loan action is not allowed
    pass

def init_loan_tables():
#creates tables this module needs
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS literature (
                literature_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                title              TEXT NOT NULL,
                file_url           TEXT,
                total_access_slots INTEGER NOT NULL DEFAULT 15
            );

            CREATE TABLE IF NOT EXISTS hold (
                hold_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                university_id TEXT NOT NULL REFERENCES users(university_id),
                literature_id INTEGER NOT NULL REFERENCES literature(literature_id),
                status        TEXT NOT NULL DEFAULT 'WAITING'
            );

            CREATE TABLE IF NOT EXISTS loan (
                loan_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                university_id TEXT NOT NULL REFERENCES users(university_id),
                literature_id INTEGER NOT NULL REFERENCES literature(literature_id),
                hold_id       INTEGER REFERENCES hold(hold_id),
                borrowed_at   TEXT NOT NULL,
                due_at        TEXT NOT NULL,
                returned_at   TEXT,
                return_type   TEXT CHECK (return_type IN ('EARLY', 'AUTO')),
                renewal_count INTEGER NOT NULL DEFAULT 0,
                status        TEXT NOT NULL DEFAULT 'ACTIVE'
                              CHECK (status IN ('ACTIVE', 'RETURNED'))
            );
            """
        )
        conn.commit()
    finally:
        conn.close()

def _available_slots(conn, literature_id):
    #Available = total slots - active loans - slots reserved for pending hold offers
    row = conn.execute(
        "SELECT total_access_slots FROM literature WHERE literature_id = ?",
        (literature_id,),
    ).fetchone()
    if row is None:
        raise LoanError("Literature not found.")

    active = conn.execute(
        "SELECT COUNT(*) FROM loan WHERE literature_id = ? AND status = 'ACTIVE'",
        (literature_id,),
    ).fetchone()[0]

    reserved = conn.execute(
        "SELECT COUNT(*) FROM hold WHERE literature_id = ? AND status = 'READY'",
        (literature_id,),
    ).fetchone()[0]

    return row[0] - active - reserved

def available_slots(literature_id):
    conn = get_connection()
    try:
        return _available_slots(conn, literature_id)
    finally:
        conn.close()

def end_loan(conn, loan_id, return_type, now):
    #shared by early return and automatic return (US-05) so both behave the same
    cur = conn.execute(
        """UPDATE loan
              SET status = 'RETURNED', returned_at = ?, return_type = ?
            WHERE loan_id = ? AND status = 'ACTIVE'""",
        (now.strftime(TIME_FORMAT), return_type, loan_id),
    )
    return cur.rowcount == 1

def release_slot(conn, literature_id):
    #BR-15: offer the freed slot to the next hold in the queue, otherwise leave it open.
    return None

def return_loan(university_id, loan_id, now=None):
    #return a borrowed item early
    now = now or datetime.now()
    conn = get_connection()

    try:
        loan = conn.execute(
            "SELECT university_id, literature_id, due_at, status FROM loan WHERE loan_id = ?",
            (loan_id,),
        ).fetchone()

        if loan is None:
            raise LoanError("Loan not found.")

        owner_id, literature_id, due_at, status = loan[0], loan[1], loan[2], loan[3]

        if owner_id != university_id:
            raise LoanError("You can only return your own loans.")

        if status != "ACTIVE":
            raise LoanError("This loan has already been returned.")

        #expired loans are handled by the automatic return, not an early return
        if datetime.strptime(due_at, TIME_FORMAT) <= now:
            raise LoanError("This loan has already expired.")

        if not end_loan(conn, loan_id, "EARLY", now):
            raise LoanError("This loan has already been returned.")

        release_slot(conn, literature_id)
        conn.commit()

        return {
            "message": "Loan returned.",
            "available_slots": _available_slots(conn, literature_id),
        }
    finally:
        conn.close()

def process_expired_loans(now=None):
    #automatic return (US-05): returns every active loan whose due time has passed
    #returns a list of the loans it returned so notifications (US-14) can use it later
    #for sprint 3: placeholder, freed slots don't go to the hold queue yet (holds are US-10 to US-13)
    now = now or datetime.now()
    conn = get_connection()

    try:
        active = conn.execute(
            "SELECT loan_id, university_id, literature_id, due_at FROM loan WHERE status = 'ACTIVE'"
        ).fetchall()

        returned = []

        for loan in active:
            loan_id, university_id, literature_id, due_at = loan[0], loan[1], loan[2], loan[3]

            if datetime.strptime(due_at, TIME_FORMAT) > now:
                continue

            #end_loan only changes loans that are still ACTIVE so a loan can't be returned twice
            if end_loan(conn, loan_id, "AUTO", now):
                release_slot(conn, literature_id)
                returned.append({
                    "loan_id": loan_id,
                    "university_id": university_id,
                    "literature_id": literature_id,
                })

        conn.commit()
        return returned
    finally:
        conn.close()