# library.py
# This file holds the RULES of the library: one function per user story.
# It doesn't print anything or ask for input; main.py does that. Keeping them apart means you can
# later swap the text menu for a website without changing any of these rules.

from datetime import datetime, timedelta  # tools for working with dates and times
from database import conn  # the open database connection from database.py

# ---------------------------------------------------------------------------------------------
# Settings you can change
# ---------------------------------------------------------------------------------------------
DECISION_WINDOW_HOURS = 72  # US-12: how long someone has to accept a book that became free
REMINDER_HOURS_LEFT = 24  # send a reminder when this many hours are left in the window
MAX_RENEWALS = 2  # US-08: how many times one loan can be renewed

# ---------------------------------------------------------------------------------------------
# Clock: lets the demo "skip ahead" in time to show auto-returns and expired holds
# ---------------------------------------------------------------------------------------------
skipped_time = timedelta()  # how far into the future we've jumped (starts at zero)


def now():
    """The current time, plus any days we skipped."""
    return datetime.now() + skipped_time  # real time + the skip


def stamp(moment):
    """Turn a datetime into text like '2026-10-04 18:30' so it can be stored in the database."""
    return moment.strftime("%Y-%m-%d %H:%M")  # this format sorts correctly as text, so < and > work in SQL


def skip_days(days):
    """Jump forward in time (demo only)."""
    global skipped_time  # we're changing the variable defined above, not making a new one
    skipped_time += timedelta(days=days)  # add the days to the total skip


class LibraryError(Exception):
    """Raised when a user tries something the rules don't allow. main.py shows the message."""


# ---------------------------------------------------------------------------------------------
# Small helpers used by many functions below
# ---------------------------------------------------------------------------------------------
def notify(user_id, kind, message, loan_id=None, hold_id=None):
    """US-14: save a notification for a user."""
    conn.execute(  # add one row to the notification table
        "INSERT INTO notification (user_id, loan_id, hold_id, type, message, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",  # the ? marks get filled with the values below
        (user_id, loan_id, hold_id, kind, message, stamp(now())),  # the values, in the same order
    )


def fail(user_id, message, kind="ERROR"):
    """Save the problem as a notification, then stop the current action with an error."""
    notify(user_id, kind, message)  # US-14 says users get notified about errors too
    conn.commit()  # save the notification before we stop
    raise LibraryError(message)  # stop here; main.py catches this and prints the message


def get_book(book_id):
    """Fetch one book's row, or raise an error if the id doesn't exist."""
    book = conn.execute("SELECT * FROM literature WHERE literature_id = ?", (book_id,)).fetchone()  # look it up
    if book is None:  # no row came back
        raise LibraryError(f"There is no book with id {book_id}.")  # tell the user
    return book  # hand the row back


def free_slots(book_id):
    """How many more people can borrow this book right now."""
    book = get_book(book_id)  # we need its total number of slots
    on_loan = conn.execute(  # count the active loans for this book
        "SELECT COUNT(*) FROM loan WHERE literature_id = ? AND status = 'ACTIVE'", (book_id,)
    ).fetchone()[0]  # fetchone() gives one row; [0] takes the count out of it
    reserved = conn.execute(  # count holds that are READY (that slot is saved for that person)
        "SELECT COUNT(*) FROM hold WHERE literature_id = ? AND status = 'READY'", (book_id,)
    ).fetchone()[0]  # same trick to read the count
    return book["total_access_slots"] - on_loan - reserved  # whatever is left is free


def people_waiting(book_id):
    """How many people are in the hold line for this book."""
    return conn.execute(  # count the WAITING holds
        "SELECT COUNT(*) FROM hold WHERE literature_id = ? AND status = 'WAITING'", (book_id,)
    ).fetchone()[0]  # read the number out of the result


def active_loan_count(user_id):
    """How many books this user has borrowed right now."""
    return conn.execute(  # count their ACTIVE loans
        "SELECT COUNT(*) FROM loan WHERE user_id = ? AND status = 'ACTIVE'", (user_id,)
    ).fetchone()[0]  # read the number out of the result


def renumber_queue(book_id):
    """After someone leaves the line, close the gap: positions become 1, 2, 3... again."""
    waiting = conn.execute(  # everyone still waiting, in their current order
        "SELECT hold_id FROM hold WHERE literature_id = ? AND status = 'WAITING' ORDER BY queue_position",
        (book_id,),
    ).fetchall()  # fetchall() gives a list of rows
    for position, row in enumerate(waiting, start=1):  # enumerate counts 1, 2, 3... as we loop
        conn.execute("UPDATE hold SET queue_position = ? WHERE hold_id = ?", (position, row["hold_id"]))  # save the new position


def give_free_slots_to_holds(book_id):
    """US-12: when a slot opens, the first person in line gets it and 72 hours to decide."""
    while free_slots(book_id) > 0:  # keep going while there's a free slot to hand out
        first = conn.execute(  # the person at the front of the line
            "SELECT * FROM hold WHERE literature_id = ? AND status = 'WAITING' ORDER BY queue_position LIMIT 1",
            (book_id,),
        ).fetchone()  # one row, or None if nobody is waiting
        if first is None:  # nobody is waiting...
            break  # ...so the slot simply stays free
        deadline = now() + timedelta(hours=DECISION_WINDOW_HOURS)  # they have until this time to decide
        conn.execute(  # mark their hold as READY and start the clock
            "UPDATE hold SET status = 'READY', queue_position = NULL, ready_at = ?, decision_deadline = ?"
            " WHERE hold_id = ?",
            (stamp(now()), stamp(deadline), first["hold_id"]),  # the values for the three ? marks
        )
        title = get_book(book_id)["title"]  # used in the message
        notify(first["user_id"], "HOLD_READY",  # tell them the good news
               f"'{title}' is ready for you. Accept or decline by {stamp(deadline)}.", hold_id=first["hold_id"])
        renumber_queue(book_id)  # everyone else moves up one place


# ---------------------------------------------------------------------------------------------
# US-01: Log in and log out
# ---------------------------------------------------------------------------------------------
def login(identifier, password):
    """Compatibility entry point for the text menu; returns (profile, token)."""
    import auth
    try:
        token = auth.login(identifier, password)
    except auth.AuthError as error:
        raise LibraryError(str(error)) from error
    return auth.get_current_user(token), token


def logout(token):
    import auth
    auth.logout(token)


# ---------------------------------------------------------------------------------------------
# US-02: Search by title, author, category or keyword (one search box checks all four)
# ---------------------------------------------------------------------------------------------
def search(text):
    """Return books whose title, author, category or keyword contains `text`."""
    pattern = f"%{text}%"  # in SQL, % means "anything", so this matches the text anywhere
    rows = conn.execute(  # LEFT JOIN keeps books even if they have no author/keyword rows
        """
        SELECT DISTINCT l.literature_id, l.title, c.name AS category
        FROM literature l
        JOIN category c            ON c.category_id = l.category_id
        LEFT JOIN literature_author la ON la.literature_id = l.literature_id
        LEFT JOIN author a          ON a.author_id = la.author_id
        LEFT JOIN literature_keyword lk ON lk.literature_id = l.literature_id
        LEFT JOIN keyword k         ON k.keyword_id = lk.keyword_id
        WHERE l.title ILIKE ? OR a.name ILIKE ? OR c.name ILIKE ? OR k.word ILIKE ?
        ORDER BY l.title
        """,  # DISTINCT stops a book showing twice when it has two matching keywords
        (pattern, pattern, pattern, pattern),  # the same pattern for each of the four ? marks
    ).fetchall()  # get every matching row
    return [dict(row) | {"free_slots": free_slots(row["literature_id"])} for row in rows]  # add free slots to each result


# ---------------------------------------------------------------------------------------------
# US-04: View a book's details and availability
# ---------------------------------------------------------------------------------------------
def book_details(book_id):
    """Everything about one book, as a dictionary."""
    book = dict(get_book(book_id))  # start with the book's own columns
    book["authors"] = [r["name"] for r in conn.execute(  # list of author names
        "SELECT a.name FROM author a JOIN literature_author la ON la.author_id = a.author_id"
        " WHERE la.literature_id = ?", (book_id,))]  # only this book's authors
    book["keywords"] = [r["word"] for r in conn.execute(  # list of keywords
        "SELECT k.word FROM keyword k JOIN literature_keyword lk ON lk.keyword_id = k.keyword_id"
        " WHERE lk.literature_id = ?", (book_id,))]  # only this book's keywords
    book["free_slots"] = free_slots(book_id)  # how many can borrow it now
    book["people_waiting"] = people_waiting(book_id)  # how many are in line
    return book  # hand it back to main.py to print


# ---------------------------------------------------------------------------------------------
# US-06: Borrow a book into your Personal Library
# ---------------------------------------------------------------------------------------------
def borrow(user_id, book_id, hold_id=None):
    """Create a loan. `hold_id` is filled in when the loan comes from an accepted hold."""
    check_due_items()
    book = get_book(book_id)  # also checks the book exists
    user = conn.execute("SELECT * FROM library_user WHERE user_id = ?", (user_id,)).fetchone()  # we need their loan limit
    already = conn.execute(  # do they already have this book?
        "SELECT 1 FROM loan WHERE user_id = ? AND literature_id = ? AND status = 'ACTIVE'", (user_id, book_id)
    ).fetchone()  # a row means yes, None means no
    if already:  # can't borrow the same book twice
        fail(user_id, f"You already have '{book['title']}'.")  # stop with a message
    if active_loan_count(user_id) >= user["max_loans"]:  # at their limit?
        fail(user_id, f"Loan limit reached: you can have {user['max_loans']} books at once.", "LOAN_LIMIT_REACHED")  # stop
    if hold_id is None and (free_slots(book_id) <= 0 or people_waiting(book_id) > 0):  # no slot, or others are in line first
        fail(user_id, f"'{book['title']}' isn't available. Place a hold to join the line.")  # stop
    if hold_id is not None:
        hold = conn.execute("SELECT 1 FROM hold WHERE hold_id=? AND user_id=? AND literature_id=? AND status='READY'", (hold_id, user_id, book_id)).fetchone()
        if hold is None:
            fail(user_id, "That hold is not ready for this user and book.")
        conn.execute("UPDATE hold SET status='ACCEPTED' WHERE hold_id=?", (hold_id,))
    due = now() + timedelta(days=book["loan_period_days"])  # when the loan ends
    cursor = conn.execute(  # create the loan
        "INSERT INTO loan (user_id, literature_id, hold_id, borrowed_at, due_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, book_id, hold_id, stamp(now()), stamp(due)),  # the values for each ? mark
    )
    notify(user_id, "BORROW_SUCCESS", f"'{book['title']}' is in your library until {stamp(due)}.", loan_id=cursor.lastrowid)  # confirm it
    conn.commit()  # save to the file


# ---------------------------------------------------------------------------------------------
# US-03 and US-07: See your Personal Library with time left, and read a book
# ---------------------------------------------------------------------------------------------
def my_loans(user_id):
    """The user's active loans, each with how much time is left."""
    rows = conn.execute(  # active loans joined with the book title
        "SELECT lo.loan_id, l.literature_id, l.title, lo.due_at, lo.renewal_count"
        " FROM loan lo JOIN literature l ON l.literature_id = lo.literature_id"
        " WHERE lo.user_id = ? AND lo.status = 'ACTIVE' ORDER BY lo.due_at",  # soonest-due first
        (user_id,),
    ).fetchall()  # get them all
    loans = []  # we'll build the result list here
    for row in rows:  # for each loan...
        left = datetime.strptime(row["due_at"], "%Y-%m-%d %H:%M") - now()  # ...work out the time left
        loans.append(dict(row) | {"time_left": f"{left.days} days {left.seconds // 3600} hours"})  # ...and add it as text
    return loans  # hand the list back


def read_book(user_id, book_id):
    """Return the book's file link, but only if the user has it on loan."""
    row = conn.execute(  # look for an active loan of this book by this user
        "SELECT l.file_url FROM loan lo JOIN literature l ON l.literature_id = lo.literature_id"
        " WHERE lo.user_id = ? AND lo.literature_id = ? AND lo.status = 'ACTIVE'",
        (user_id, book_id),
    ).fetchone()  # one row or None
    if row is None:  # no active loan
        fail(user_id, "You can only read books that are in your library.")  # stop
    return row["file_url"]  # the link to open


# ---------------------------------------------------------------------------------------------
# US-09 and US-05: Return a book (early by the user, or automatically when it expires)
# ---------------------------------------------------------------------------------------------
def return_book(user_id, loan_id, return_type="EARLY"):
    """Close a loan and pass the free slot to the next person in line."""
    loan = conn.execute(  # find the loan, making sure it's theirs and still active
        "SELECT * FROM loan WHERE loan_id = ? AND user_id = ? AND status = 'ACTIVE'", (loan_id, user_id)
    ).fetchone()  # one row or None
    if loan is None:  # wrong id, not theirs, or already returned
        fail(user_id, "That isn't one of your active loans.")  # stop
    conn.execute(  # mark it returned
        "UPDATE loan SET status = 'RETURNED', returned_at = ?, return_type = ? WHERE loan_id = ?",
        (stamp(now()), return_type, loan_id),  # the values for each ? mark
    )
    title = get_book(loan["literature_id"])["title"]  # used in the message
    how = "returned early" if return_type == "EARLY" else "returned automatically because the loan ended"  # wording depends on how
    notify(user_id, "LOAN_RETURNED", f"'{title}' was {how}.", loan_id=loan_id)  # tell the user
    give_free_slots_to_holds(loan["literature_id"])  # the next person in line may now get it
    conn.commit()  # save to the file


# ---------------------------------------------------------------------------------------------
# US-08: Renew a loan (only if nobody is waiting for the book)
# ---------------------------------------------------------------------------------------------
def renew(user_id, loan_id):
    """Push the due date back by one more loan period."""
    loan = conn.execute(  # find the loan, making sure it's theirs and still active
        "SELECT * FROM loan WHERE loan_id = ? AND user_id = ? AND status = 'ACTIVE'", (loan_id, user_id)
    ).fetchone()  # one row or None
    if loan is None:  # not found
        fail(user_id, "That isn't one of your active loans.")  # stop
    if people_waiting(loan["literature_id"]) > 0:  # someone else is waiting
        fail(user_id, "Can't renew: other people are waiting for this book.")  # stop
    if loan["renewal_count"] >= MAX_RENEWALS:  # renewed too many times already
        fail(user_id, f"Can't renew more than {MAX_RENEWALS} times.")  # stop
    book = get_book(loan["literature_id"])  # we need its loan length
    old_due = datetime.strptime(loan["due_at"], "%Y-%m-%d %H:%M")  # turn the stored text back into a datetime
    new_due = old_due + timedelta(days=book["loan_period_days"])  # add one more loan period
    conn.execute(  # save the new date and count the renewal
        "UPDATE loan SET due_at = ?, renewal_count = renewal_count + 1 WHERE loan_id = ?", (stamp(new_due), loan_id)
    )
    notify(user_id, "LOAN_RENEWED", f"'{book['title']}' renewed until {stamp(new_due)}.", loan_id=loan_id)  # confirm it
    conn.commit()  # save to the file


# ---------------------------------------------------------------------------------------------
# US-10, US-11, US-13: Place a hold, see your holds, cancel a hold
# ---------------------------------------------------------------------------------------------
def place_hold(user_id, book_id):
    """Join the line for a book that isn't available."""
    check_due_items()
    book = get_book(book_id)  # also checks the book exists
    user = conn.execute("SELECT * FROM library_user WHERE user_id = ?", (user_id,)).fetchone()  # we need their hold limit
    if free_slots(book_id) > 0 and people_waiting(book_id) == 0:  # it's free right now
        fail(user_id, f"'{book['title']}' is available, so you can borrow it now.")  # no need to wait
    has_it = conn.execute(  # do they already have it on loan?
        "SELECT 1 FROM loan WHERE user_id = ? AND literature_id = ? AND status = 'ACTIVE'", (user_id, book_id)
    ).fetchone()  # a row means yes
    if has_it:  # can't wait for a book you already have
        fail(user_id, "You already have this book.")  # stop
    in_line = conn.execute(  # are they already in the line?
        "SELECT 1 FROM hold WHERE user_id = ? AND literature_id = ? AND status IN ('WAITING', 'READY')",
        (user_id, book_id),
    ).fetchone()  # a row means yes
    if in_line:  # can't join twice
        fail(user_id, "You already have a hold on this book.")  # stop
    open_holds = conn.execute(  # how many holds do they have across all books?
        "SELECT COUNT(*) FROM hold WHERE user_id = ? AND status IN ('WAITING', 'READY')", (user_id,)
    ).fetchone()[0]  # read the number
    if open_holds >= user["max_holds"]:  # at their limit?
        fail(user_id, f"Hold limit reached: you can have {user['max_holds']} holds at once.", "HOLD_LIMIT_REACHED")  # stop
    conn.execute(  # add them to the back of the line
        "INSERT INTO hold (user_id, literature_id, placed_at, queue_position) VALUES (?, ?, ?, ?)",
        (user_id, book_id, stamp(now()), people_waiting(book_id) + 1),  # their position = people ahead + 1
    )
    conn.commit()  # save to the file


def my_holds(user_id):
    """The user's open holds with their place in line (or their deadline if READY)."""
    rows = conn.execute(  # open holds joined with the book title
        "SELECT h.hold_id, l.title, h.status, h.queue_position, h.decision_deadline"
        " FROM hold h JOIN literature l ON l.literature_id = h.literature_id"
        " WHERE h.user_id = ? AND h.status IN ('WAITING', 'READY') ORDER BY h.placed_at",  # oldest first
        (user_id,),
    ).fetchall()  # get them all
    return [dict(row) for row in rows]  # turn each row into a normal dictionary


def cancel_hold(user_id, hold_id):
    """Leave the line (or give up a READY hold)."""
    hold = conn.execute(  # find the hold, making sure it's theirs and still open
        "SELECT * FROM hold WHERE hold_id = ? AND user_id = ? AND status IN ('WAITING', 'READY')", (hold_id, user_id)
    ).fetchone()  # one row or None
    if hold is None:  # not found
        fail(user_id, "That isn't one of your open holds.")  # stop
    conn.execute("UPDATE hold SET status = 'CANCELLED', queue_position = NULL WHERE hold_id = ?", (hold_id,))  # mark it cancelled
    renumber_queue(hold["literature_id"])  # people behind them move up
    give_free_slots_to_holds(hold["literature_id"])  # if it was READY, its slot goes to the next person
    conn.commit()  # save to the file


# ---------------------------------------------------------------------------------------------
# US-12: Accept or decline a READY hold within 72 hours
# ---------------------------------------------------------------------------------------------
def accept_hold(user_id, hold_id):
    """Turn a READY hold into a loan."""
    check_due_items()  # first expire anything whose time is up, so a late accept is refused
    hold = conn.execute(  # find the hold, making sure it's theirs and READY
        "SELECT * FROM hold WHERE hold_id = ? AND user_id = ? AND status = 'READY'", (hold_id, user_id)
    ).fetchone()  # one row or None
    if hold is None:  # not ready, not theirs, or the window already passed
        fail(user_id, "That hold isn't ready, or its 72 hours have passed.")  # stop
    borrow(user_id, hold["literature_id"], hold_id=hold_id)  # create the loan first (if this fails, the hold stays READY)
    conn.execute("UPDATE hold SET status = 'ACCEPTED' WHERE hold_id = ?", (hold_id,))  # then mark the hold as used
    conn.commit()  # save to the file


def decline_hold(user_id, hold_id):
    """Say no to a READY hold; the next person in line gets the book."""
    hold = conn.execute(  # find the hold, making sure it's theirs and READY
        "SELECT * FROM hold WHERE hold_id = ? AND user_id = ? AND status = 'READY'", (hold_id, user_id)
    ).fetchone()  # one row or None
    if hold is None:  # not found
        fail(user_id, "That hold isn't ready.")  # stop
    conn.execute("UPDATE hold SET status = 'DECLINED' WHERE hold_id = ?", (hold_id,))  # mark it declined
    give_free_slots_to_holds(hold["literature_id"])  # pass the slot on
    conn.commit()  # save to the file


# ---------------------------------------------------------------------------------------------
# US-05 and US-12: The "background job" that handles anything whose time is up.
# main.py calls this every time the menu is shown. A real system would run it on a timer.
# ---------------------------------------------------------------------------------------------
def check_due_items():
    """Auto-return expired loans, expire unanswered holds, and send deadline reminders."""
    right_now = stamp(now())  # the current time as text, to compare with stored dates

    expired_loans = conn.execute(  # active loans whose due date has passed
        "SELECT * FROM loan WHERE status = 'ACTIVE' AND due_at <= ?", (right_now,)
    ).fetchall()  # get them all
    for loan in expired_loans:  # return each one automatically
        return_book(loan["user_id"], loan["loan_id"], return_type="AUTO")  # same function as an early return

    expired_holds = conn.execute(  # READY holds whose 72 hours are up
        "SELECT * FROM hold WHERE status = 'READY' AND decision_deadline <= ?", (right_now,)
    ).fetchall()  # get them all
    for hold in expired_holds:  # expire each one
        conn.execute("UPDATE hold SET status = 'EXPIRED' WHERE hold_id = ?", (hold["hold_id"],))  # mark it expired
        title = get_book(hold["literature_id"])["title"]  # used in the message
        notify(hold["user_id"], "HOLD_EXPIRED", f"Your 72 hours for '{title}' ran out; it went to the next person.",
               hold_id=hold["hold_id"])  # tell them
        give_free_slots_to_holds(hold["literature_id"])  # the next person in line gets it

    reminder_time = stamp(now() + timedelta(hours=REMINDER_HOURS_LEFT))  # "deadline is before this" = less than 24h left
    needs_reminder = conn.execute(  # READY holds close to their deadline that haven't been reminded yet
        "SELECT * FROM hold h WHERE status = 'READY' AND decision_deadline <= ?"
        " AND NOT EXISTS (SELECT 1 FROM notification n WHERE n.hold_id = h.hold_id AND n.type = 'DECISION_REMINDER')",
        (reminder_time,),
    ).fetchall()  # get them all
    for hold in needs_reminder:  # remind each one once
        notify(hold["user_id"], "DECISION_REMINDER", f"Less than {REMINDER_HOURS_LEFT} hours left to accept your hold "
               f"(deadline {hold['decision_deadline']}).", hold_id=hold["hold_id"])  # send the reminder

    conn.commit()  # save everything to the file


# ---------------------------------------------------------------------------------------------
# US-14: Read your notifications
# ---------------------------------------------------------------------------------------------
def my_notifications(user_id):
    """All of the user's notifications, newest last. Marks them as read."""
    rows = conn.execute(  # every notification for this user
        "SELECT type, message, created_at, is_read FROM notification WHERE user_id = ? ORDER BY notification_id",
        (user_id,),
    ).fetchall()  # get them all
    conn.execute("UPDATE notification SET is_read = 1 WHERE user_id = ?", (user_id,))  # they've seen them now
    conn.commit()  # save to the file
    return [dict(row) for row in rows]  # turn each row into a normal dictionary


def unread_count(user_id):
    """How many notifications the user hasn't seen yet."""
    return conn.execute(  # count the unread ones
        "SELECT COUNT(*) FROM notification WHERE user_id = ? AND is_read = 0", (user_id,)
    ).fetchone()[0]  # read the number


# ---------------------------------------------------------------------------------------------
# US-15: View and edit personal information
# ---------------------------------------------------------------------------------------------
def get_profile(user_id):
    """The user's own row from the user table."""
    return dict(conn.execute("SELECT * FROM library_user WHERE user_id = ?", (user_id,)).fetchone())  # as a dictionary


def update_profile(user_id, phone, address):
    """Only phone and address can be changed; name and email come from the university."""
    conn.execute("UPDATE library_user SET phone = ?, address = ? WHERE user_id = ?", (phone, address, user_id))  # save the new values
    conn.commit()  # save to the file
