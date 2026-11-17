#Hold offers with staff mode for the University Digital Borrowing System
#works like hold_offers.py with two changes:
#  1. a free slot is offered to waiting staff before waiting students
#  2. when staff accept a hold the loan has no due date and uses the staff loan limit
#
#changed: the old hold_offers.py, loans.py and borrow.py were replaced by library.py. library.py now hands every
#freed slot to offer_next_hold() below, and check_due_items() uses process_holds() for expired offers.
#The hold table names the offer times ready_at and decision_deadline (the old offered_at and expires_at).
#Every change from the team's original staff_hold_offers.py is marked with "changed:".

from datetime import datetime

import library  # changed: replaces the loans, borrow and hold_offers imports
from database import get_connection
from staff import is_staff, STAFF_STATUSES, STAFF_MAX_LOANS, NO_DUE_DATE
from staff_holds import STAFF_FIRST, HOLD_USERS

LoanError = library.LibraryError  # changed: was from loans import LoanError
TIME_FORMAT = "%Y-%m-%d %H:%M"  # changed: library.py saves times to the minute

def offer_next_hold(conn, literature_id, now):
    #free slot goes to the first person in line (staff first), they get 72 hrs
    offered = []  # changed: returns who got an offer
    while library.free_slots(literature_id) > 0:  # changed: was _available_slots(conn, literature_id)
        nxt = conn.execute(
            f"""SELECT h.hold_id, h.user_id
                {HOLD_USERS}
                WHERE h.literature_id = %s AND h.status = 'WAITING'
                ORDER BY {STAFF_FIRST}, h.placed_at, h.hold_id LIMIT 1""",
            (literature_id, list(STAFF_STATUSES)),
        ).fetchone()
        if nxt is None:
            return offered

        window = library.decision_window()  # changed: 72 hours, or the shorter demo window (NFR-05)
        conn.execute(
            "UPDATE hold SET status = 'READY', queue_position = NULL, ready_at = %s, decision_deadline = %s WHERE hold_id = %s",
            (now.strftime(TIME_FORMAT), (now + window).strftime(TIME_FORMAT), nxt["hold_id"]),  # changed: column names
        )
        #changed: US-14 hold ready notification, and the people still waiting move up
        title = library.get_book(literature_id)["title"]
        library.notify(nxt["user_id"], "HOLD_READY",
                       f"'{title}' is ready for you. You have {library.window_words(window)} to accept or decline it"
                       " on your Holds page.", hold_id=nxt["hold_id"])
        library.renumber_queue(literature_id)
        offered.append(nxt["hold_id"])
    return offered

def end_offer(conn, hold, status, now):
    #shared by decline and expire, the slot moves to the next person
    conn.execute(
        "UPDATE hold SET status = %s WHERE hold_id = %s",  # changed: there's no responded_at column
        (status, hold["hold_id"]),
    )
    offer_next_hold(conn, hold["literature_id"], now)

def get_ready_hold(conn, university_id, hold_id, now):
    #postgres can't compare an id that isn't a number
    if not str(hold_id).isdigit():
        raise LoanError("Hold not found.")

    hold = conn.execute(
        """SELECT h.hold_id, h.user_id, lu.university_id, h.literature_id, h.status, h.decision_deadline AS expires_at
           FROM hold h JOIN library_user lu ON lu.user_id = h.user_id WHERE h.hold_id = %s""",  # changed: user_id join
        (int(hold_id),),
    ).fetchone()

    if hold is None:
        raise LoanError("Hold not found.")
    if hold["university_id"] != university_id:
        raise LoanError("You can only answer your own holds.")
    if hold["status"] != "READY":
        library.fail(hold["user_id"], "This hold isn't ready yet.")  # changed: fail() also sends the US-14 notification

    if datetime.strptime(hold["expires_at"], TIME_FORMAT) <= now:
        end_offer(conn, hold, "EXPIRED", now)
        conn.commit()
        library.fail(hold["user_id"], "The 72 hours are up, this hold has expired.")  # changed: fail()
    return hold

def accept_hold(university_id, hold_id, now=None):
    #READY hold turns into a loan
    now = now or library.now()  # changed: library.now() so the tests can skip time
    staff = is_staff(university_id)
    limit = STAFF_MAX_LOANS if staff else library.MAX_LOANS()  # changed: library.py's student limit

    conn = get_connection()
    try:
        hold = get_ready_hold(conn, university_id, hold_id, now)

        active = conn.execute(
            "SELECT COUNT(*) AS n FROM loan WHERE user_id = %s AND status = 'ACTIVE'",  # changed: user_id
            (hold["user_id"],),
        ).fetchone()["n"]
        if active >= limit:
            library.fail(hold["user_id"], f"You've reached the limit of {limit} active loans.", kind="LOAN_LIMIT")  # changed: fail()

        #staff keep the item with no due date, students get the normal 14 days
        book = library.get_book(hold["literature_id"])
        if staff:
            due_at = NO_DUE_DATE
        else:
            due_at = library.loan_due(book, now)  # changed: 14 days, or the demo loan length (NFR-05)

        cur = conn.execute(
            "INSERT INTO loan (user_id, literature_id, hold_id, borrowed_at, due_at, status) "  # changed: user_id
            "VALUES (%s, %s, %s, %s, %s, 'ACTIVE') RETURNING loan_id",
            (hold["user_id"], hold["literature_id"], hold["hold_id"], now.strftime(TIME_FORMAT), due_at),
        )
        loan_id = cur.fetchone()["loan_id"]

        conn.execute(
            "UPDATE hold SET status = 'ACCEPTED' WHERE hold_id = %s",  # changed: there's no responded_at column
            (hold["hold_id"],),
        )
        #changed: US-14 successful borrowing notification
        when = "It has no due date (faculty loan)." if staff else "You can read it in your Personal Library."
        library.notify(hold["user_id"], "BORROW_SUCCESS", f"You borrowed '{book['title']}'. {when}",
                       loan_id=loan_id, hold_id=hold["hold_id"])
        conn.commit()
    finally:
        conn.close()

    return {
        "message": "Hold accepted! It's now in your Personal Library.",
        "loan_id": loan_id,
        "due_at": due_at,
    }

def decline_hold(university_id, hold_id, now=None):
    #slot goes to the next person in line
    now = now or library.now()  # changed: library.now()
    conn = get_connection()
    try:
        hold = get_ready_hold(conn, university_id, hold_id, now)
        #changed: US-14 notification
        library.notify(hold["user_id"], "HOLD_DECLINED",
                       f"You declined '{library.get_book(hold['literature_id'])['title']}'. It went to the next person in line.",
                       hold_id=hold["hold_id"])
        end_offer(conn, hold, "DECLINED", now)
        conn.commit()
    finally:
        conn.close()

    return {"message": "Hold declined."}

def process_holds(now=None):
    #expires READY holds past 72 hrs, then offers free slots to the queue
    #returns the expired holds so notifications (US-14) can use it later
    now = now or library.now()  # changed: library.now()
    conn = get_connection()
    try:
        ready = conn.execute(
            """SELECT h.hold_id, h.user_id, lu.university_id, h.literature_id, h.decision_deadline AS expires_at
               FROM hold h JOIN library_user lu ON lu.user_id = h.user_id WHERE h.status = 'READY'"""  # changed: user_id join
        ).fetchall()

        expired = []
        for hold in ready:
            if hold["expires_at"] is None or datetime.strptime(hold["expires_at"], TIME_FORMAT) > now:
                continue
            end_offer(conn, hold, "EXPIRED", now)
            expired.append({
                "hold_id": hold["hold_id"],
                "user_id": hold["user_id"],  # changed: library.notify() needs the user_id
                "university_id": hold["university_id"],
                "literature_id": hold["literature_id"],
            })

        #slots freed by returns or cancels get offered here
        waiting = conn.execute("SELECT DISTINCT literature_id FROM hold WHERE status = 'WAITING'").fetchall()
        for row in waiting:
            offer_next_hold(conn, row["literature_id"], now)

        conn.commit()
        return expired
    finally:
        conn.close()
