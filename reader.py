#Open and read borrowed literature (US-03) for the University Digital Borrowing System

from datetime import datetime

from database import get_connection
from auth import TIME_FORMAT
from loans import LoanError

def open_literature(university_id, literature_id, now=None):
    #open and read literature (US-03, NFR-04)
    #only allowed while the user has an active loan that hasn't passed its due time
    #the due time is checked here too so an expired loan is blocked even if automatic return hasn't run yet
    now = now or datetime.now()
    conn = get_connection()

    try:
        literature = conn.execute(
            "SELECT title, file_url FROM literature WHERE literature_id = ?",
            (literature_id,),
        ).fetchone()

        if literature is None:
            raise LoanError("Literature not found.")

        loans = conn.execute(
            "SELECT due_at FROM loan "
            "WHERE university_id = ? AND literature_id = ? AND status = 'ACTIVE'",
            (university_id, literature_id),
        ).fetchall()

        if not loans:
            raise LoanError("You need an active loan to read this literature.")

        for loan in loans:
            if datetime.strptime(loan[0], TIME_FORMAT) > now:
                return {
                    "title": literature[0],
                    "file_url": literature[1],
                    "due_at": loan[0],
                }

        raise LoanError("This loan has expired.")
    finally:
        conn.close()
