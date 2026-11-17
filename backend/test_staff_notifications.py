#Tests for Sprint 4 notifications (US-14 / FR-23)
#staff mode has its own tests in test_staff_mode.py (the team's staff tests)
#uses the same setup as test_udbs.py: every test gets fresh tables in a udbs_test schema
#
#how to run (from the backend folder):
#   set TEST_DATABASE_URL to a postgres connection string, then run: pytest test_staff_notifications.py -v

from datetime import timedelta

import pytest

from test_udbs import (db, run, one, add_user, add_book, hold_of, loan_of, notes, as_time, skip,  # noqa: F401  (db is the shared fixture)
                       full_book_with_queue, free_the_slot)
import library
import notifications
import staff
from staff_borrow import borrow_literature
from library import LibraryError


def add_faculty(**limits):
    #a library user whose university record says faculty
    user_id = add_user(**limits)
    university_id = one("SELECT university_id FROM library_user WHERE user_id = %s", (user_id,))["university_id"]
    run("INSERT INTO users (university_id, email, password_hash, first_name, last_name, display_name, pronouns, status) "
        "VALUES (%s, %s, 'x$y', 'Fac', 'Ulty', 'Prof', NULL, 'faculty')", (university_id, f"{university_id}@fac.ca"))
    return user_id


def add_student(**limits):
    user_id = add_user(**limits)
    university_id = one("SELECT university_id FROM library_user WHERE user_id = %s", (user_id,))["university_id"]
    run("INSERT INTO users (university_id, email, password_hash, first_name, last_name, display_name, pronouns, status) "
        "VALUES (%s, %s, 'x$y', 'Stu', 'Dent', 'Stu', NULL, 'student')", (university_id, f"{university_id}@stu.ca"))
    return user_id


def fill_loans(user_id, how_many):
    for i in range(how_many):
        library.borrow(user_id, add_book(1, title=f"Filler {i}"))


def position(user_id, book_id):
    return hold_of(user_id, book_id)["queue_position"]


#=============================================================================================
#Notifications (US-14 / FR-23, AT-14, ST-10)
#=============================================================================================

def test_borrow_sends_success_notification():
    s, book = add_student(), add_book(1, title="Clean Code")
    library.borrow(s, book)
    [note] = notes(s, "BORROW_SUCCESS")
    assert "Clean Code" in note["message"]
    assert note["loan_id"] == loan_of(s, book)["loan_id"]


def test_return_sends_loan_returned_notification():
    s, book = add_student(), add_book(1)
    library.borrow(s, book)
    library.return_book(s, loan_of(s, book)["loan_id"])
    assert len(notes(s, "LOAN_RETURNED")) == 1


def test_hold_ready_notification_when_slot_opens():
    a = add_student()
    owner, book = full_book_with_queue([a])
    free_the_slot(owner, book)
    [note] = notes(a, "HOLD_READY")
    assert "72 hours" in note["message"]
    assert note["hold_id"] == hold_of(a, book)["hold_id"]


def test_hold_ready_uses_demo_window(monkeypatch):
    monkeypatch.setenv("UDBS_DEMO_HOLD_MINUTES", "3")
    a = add_student()
    owner, book = full_book_with_queue([a])
    free_the_slot(owner, book)
    assert "3 minutes" in notes(a, "HOLD_READY")[0]["message"]


def test_window_closing_reminder_in_last_third_once():
    a = add_student()
    owner, book = full_book_with_queue([a])
    free_the_slot(owner, book)
    skip(hours=47)
    library.check_due_items()
    assert notes(a, "HOLD_WINDOW_CLOSING") == []
    skip(hours=2)  # 49 hours in, so less than 24 left
    library.check_due_items()
    library.check_due_items()
    assert len(notes(a, "HOLD_WINDOW_CLOSING")) == 1


def test_expired_hold_sends_notification_and_next_person_gets_ready():
    a, b = add_student(), add_student()
    owner, book = full_book_with_queue([a, b])
    free_the_slot(owner, book)
    skip(hours=73)
    library.check_due_items()
    assert len(notes(a, "HOLD_EXPIRED")) == 1
    assert len(notes(b, "HOLD_READY")) == 1


def test_hold_limit_notification():
    s = add_student(max_holds=1)
    owner, book1 = full_book_with_queue([s])
    _, book2 = full_book_with_queue([])
    with pytest.raises(LibraryError):
        library.place_hold(s, book2)
    assert len(notes(s, "HOLD_LIMIT")) == 1


def test_loan_limit_notification_for_students():
    s = add_student()
    fill_loans(s, 30)
    with pytest.raises(LibraryError):
        library.borrow(s, add_book(1))
    assert len(notes(s, "LOAN_LIMIT")) == 1


def test_refused_action_sends_error_notification():
    s, book = add_student(), add_book(2)
    library.borrow(s, book)
    with pytest.raises(LibraryError):
        library.borrow(s, book)
    [note] = notes(s, "ERROR")
    assert "already have" in note["message"]
    assert library.pending_error_notes[-1][1] == "ERROR"


def test_hold_placed_cancelled_declined_and_renewed_notifications():
    a, b = add_student(), add_student()
    owner, book = full_book_with_queue([a, b])
    assert "#1" in notes(a, "HOLD_PLACED")[0]["message"]
    library.cancel_hold(b, hold_of(b, book)["hold_id"])
    assert len(notes(b, "HOLD_CANCELLED")) == 1
    free_the_slot(owner, book)
    library.decline_hold(a, hold_of(a, book)["hold_id"])
    assert len(notes(a, "HOLD_DECLINED")) == 1
    s, other = add_student(), add_book(1)
    library.borrow(s, other)
    library.renew(s, loan_of(s, other)["loan_id"])
    assert len(notes(s, "LOAN_RENEWED")) == 1


def test_loan_due_soon_once_and_again_after_renewal():
    s, book = add_student(), add_book(1)
    library.borrow(s, book)
    skip(days=11)
    library.check_due_items()
    assert notes(s, "LOAN_DUE_SOON") == []
    skip(days=1, hours=1)  # under 2 days left
    library.check_due_items()
    library.check_due_items()
    assert len(notes(s, "LOAN_DUE_SOON")) == 1
    library.renew(s, loan_of(s, book)["loan_id"])
    skip(days=14)  # the renewed loan is due 14 days later, so this is under 2 days left again
    library.check_due_items()
    assert len(notes(s, "LOAN_DUE_SOON")) == 2


def test_faculty_loans_get_no_due_soon_reminder():
    f, book = add_faculty(), add_book(1)
    borrow_literature(one("SELECT university_id FROM library_user WHERE user_id = %s", (f,))["university_id"], book)
    assert loan_of(f, book)["due_at"] == staff.NO_DUE_DATE
    skip(days=400)
    library.check_due_items()
    assert notes(f, "LOAN_DUE_SOON") == []


def test_notification_list_newest_first_with_titles_and_book():
    s, book = add_student(), add_book(1)
    library.borrow(s, book)
    skip(minutes=5)
    library.return_book(s, loan_of(s, book)["loan_id"])
    listed = notifications.my_notifications(s)
    assert [n["type"] for n in listed] == ["LOAN_RETURNED", "BORROW_SUCCESS"]
    assert listed[0]["title"] == "Loan returned"
    assert listed[0]["literature_id"] == book
    assert listed[0]["is_read"] is False


def test_unread_count_and_mark_read():
    s = add_student()
    for _ in range(3):
        library.borrow(s, add_book(1))
    assert notifications.unread_count(s) == 3
    first = notifications.my_notifications(s)[0]["notification_id"]
    notifications.mark_read(s, first)
    assert notifications.unread_count(s) == 2
    assert len(notifications.my_notifications(s, unread_only=True)) == 2
    notifications.mark_read(s)
    assert notifications.unread_count(s) == 0


def test_cannot_mark_someone_elses_notification():
    a, b = add_student(), add_student()
    library.borrow(a, add_book(1))
    theirs = notifications.my_notifications(a)[0]["notification_id"]
    notifications.mark_read(b, theirs)
    assert notifications.unread_count(a) == 1


def test_notifications_only_show_own():
    a, b = add_student(), add_student()
    library.borrow(a, add_book(1))
    assert notifications.my_notifications(b) == []
