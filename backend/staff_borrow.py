#Borrowing with staff mode for the University Digital Borrowing System
#students still go through borrow.py, staff get a higher limit and no due date
#
#changed: the old borrow.py, loans.py and loan_time.py were replaced by library.py, so this file now calls
#library.py for those jobs. Every change from the team's original staff_borrow.py
#is marked with "changed:". The staff rules themselves are the same.

from datetime import datetime

import library as borrow  # changed: library.py does what borrow.py did (borrow, count loans, the 30 loan limit)
from database import get_connection
from library import LibraryError as LoanError, free_slots as available_slots  # changed: was from loans import ...
from staff import is_staff, has_no_due_date, STAFF_MAX_LOANS, NO_DUE_DATE
from staff_holds import queue_length

def loan_limit(university_id):
    #how many active loans this user is allowed
    if is_staff(university_id):
        return STAFF_MAX_LOANS
    return borrow.MAX_LOANS()  # changed: library.py works the student limit out (30, or lower for demos)

def borrow_literature(university_id, literature_id, now=None):
    user_id = borrow.user_id_for(university_id)  # changed: library.py tables use user_id

    #students use the normal rules
    if not is_staff(university_id):
        borrow.borrow(user_id, literature_id)  # changed: was borrow.borrow_literature(university_id, literature_id, now)
        return loan_result(user_id, literature_id, "Borrowed! It's now in your Personal Library.")

    borrow.check_due_items()  # changed: same first step library.borrow() takes
    now = now or borrow.now()  # changed: library.now() so the tests can skip time

    #available_slots raises LoanError if the lit doesn't exist
    if available_slots(literature_id) <= 0:
        borrow.fail(user_id, "No access slots available right now. You can place a hold instead.")  # changed: fail() also sends the US-14 notification

    #staff still can't take a slot that's being saved for the queue
    #they place a hold instead and it goes ahead of the students
    if queue_length(literature_id) > 0:
        borrow.fail(user_id, "Other users are waiting in the hold queue for this item. You can place a hold instead.")  # changed: fail()

    if borrow.count_active_loans(university_id) >= STAFF_MAX_LOANS:
        borrow.fail(user_id, f"You've reached the limit of {STAFF_MAX_LOANS} active loans.", kind="LOAN_LIMIT")  # changed: fail()

    conn = get_connection()
    try:
        already = conn.execute(
            "SELECT loan_id FROM loan WHERE user_id = %s AND literature_id = %s AND status = 'ACTIVE'",  # changed: user_id
            (user_id, literature_id),
        ).fetchone()

        if already is not None:
            borrow.fail(user_id, "This item is already in your Personal Library.")  # changed: fail()

        cur = conn.execute(
            "INSERT INTO loan (user_id, literature_id, borrowed_at, due_at, status) "  # changed: user_id
            "VALUES (%s, %s, %s, %s, 'ACTIVE') RETURNING loan_id",
            (user_id, literature_id, borrow.stamp(now), NO_DUE_DATE),  # changed: library.py time format
        )
        loan_id = cur.fetchone()["loan_id"]
        title = borrow.get_book(literature_id)["title"]  # changed: US-14 successful borrowing notification
        borrow.notify(user_id, "BORROW_SUCCESS", f"You borrowed '{title}'. It has no due date (faculty loan).", loan_id=loan_id)
        conn.commit()
    finally:
        conn.close()

    return {
        "message": "Borrowed! It's now in your Personal Library. Staff loans have no due date.",
        "loan_id": loan_id,
        "due_at": NO_DUE_DATE,
        "available_slots": available_slots(literature_id),
    }

def loan_result(user_id, literature_id, message):
    #changed: new helper, gives the student path the same result shape the staff path returns
    loan = get_connection().execute(
        "SELECT loan_id, due_at FROM loan WHERE user_id = %s AND literature_id = %s AND status = 'ACTIVE'",
        (user_id, literature_id),
    ).fetchone()
    return {"message": message, "loan_id": loan["loan_id"], "due_at": loan["due_at"],
            "available_slots": available_slots(literature_id)}

def due_text(due_at):
    #what to show for the due date
    if has_no_due_date(due_at):
        return "No due date"
    return due_at

def time_left_text(due_at, now=None):
    #what to show for the time left
    if has_no_due_date(due_at):
        return "Keep as long as you need"
    return remaining_time(due_at, now)

def remaining_time(due_at, now=None):
    #changed: was imported from loan_time.py, which isn't in the project anymore
    #shows the time left like "14d 0h 0m 0s"
    now = now or borrow.now()
    due = datetime.strptime(due_at[:16], "%Y-%m-%d %H:%M")
    left = max(int((due - now).total_seconds()), 0)
    return f"{left // 86400}d {left % 86400 // 3600}h {left % 3600 // 60}m {left % 60}s"
