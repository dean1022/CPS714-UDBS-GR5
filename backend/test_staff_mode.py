#Tests for staff mode: the team's test_staff_auth_borrow.py, test_staff_holds.py and test_staff_reader.py
#moved onto the current tables.
#Each test keeps its original name and what it checks. What changed:
#  - setup uses the same fresh udbs_test schema as test_udbs.py instead of reset_db()/init_db()
#  - library.py tables use user_id and save times to the minute, so the expected times use that format
#  - student loans go through library.py, which uses library.now(), so "now=" dates became skip() calls
#  - reader.open_literature() became library.read_book(), which is what api.py uses to open a book
#
#how to run (from the backend folder):
#   set TEST_DATABASE_URL to a postgres connection string, then run: pytest test_staff_mode.py -v

from datetime import timedelta

import pytest

from test_udbs import db, run, one, add_book, as_time, skip  # noqa: F401  (db is the shared fixture)
import library
from auth import AuthError, login, logout, get_current_user
from library import LibraryError as LoanError
from seed_users import seed, DEMO_PASSWORD
from staff import is_staff, STAFF_MAX_LOANS, NO_DUE_DATE
from staff_demo import apply_demo_roles, demo_status
from staff_borrow import borrow_literature, loan_limit, due_text, time_left_text
from staff_holds import place_hold, get_queue, get_queue_position, next_position, get_my_holds
from staff_hold_offers import accept_hold, decline_hold, process_holds

MAX_LOANS = 30

#odd IDs are students and even IDs are faculty (staff_demo.py)
STUDENT = "501000001"
STAFF = "501000002"
OTHER_STAFF = "700000002"
STUDENT_1, STUDENT_2, STUDENT_3 = "501000001", "501000003", "501000005"
STAFF_1, STAFF_2 = "501000002", "501000004"


@pytest.fixture(autouse=True)
def demo_accounts(db):
    #the demo accounts from seed.sql with the even/odd roles, and a library account for each
    seed()
    apply_demo_roles()
    run("""INSERT INTO library_user (university_id, first_name, last_name, email, created_at, max_loans, max_holds)
           SELECT university_id, first_name, last_name, email, '2026-11-01 09:00', 30, 15 FROM users""")


#helper function to add a literature item
def add_literature(title="Test Book", total_slots=15):
    return add_book(total_slots, title=title)


#helper function to give a user a number of active loans without borrowing one by one
def add_loans(university_id, how_many):
    user_id = library.user_id_for(university_id)
    for i in range(how_many):
        lit_id = add_book(1, title=f"Filler {i}")
        run("INSERT INTO loan (user_id, literature_id, borrowed_at, due_at, status) VALUES (%s, %s, '2026-11-01 09:00', %s, 'ACTIVE')",
            (user_id, lit_id, NO_DUE_DATE))


#helper function to log in and get the user the way the app does
def log_in(identifier):
    token = login(identifier, DEMO_PASSWORD)
    return token, get_current_user(token)


def get_hold(hold_id):
    return one("SELECT * FROM hold WHERE hold_id = %s", (hold_id,))


def return_loan(university_id, loan_id):
    library.return_book(library.user_id_for(university_id), loan_id)


def open_literature(university_id, literature_id):
    #what reader.open_literature() did: refuses unless there's an active loan, after expired loans are returned
    library.check_due_items()
    return library.read_book(library.user_id_for(university_id), literature_id)


def loan_due_at(university_id, literature_id):
    return one("SELECT due_at FROM loan WHERE user_id = %s AND literature_id = %s AND status = 'ACTIVE'",
               (library.user_id_for(university_id), literature_id))["due_at"]


#=============================================================================================
#test_staff_auth_borrow.py
#=============================================================================================

#tests that a logged in staff member is recognised as staff
def test_staff_login_is_staff():
    _, user = log_in(STAFF)

    assert user["status"] == "faculty"
    assert is_staff(user["university_id"]) is True
    assert loan_limit(user["university_id"]) == STAFF_MAX_LOANS

#tests that a logged in student is not staff
def test_student_login_is_not_staff():
    _, user = log_in(STUDENT)

    assert user["status"] == "student"
    assert is_staff(user["university_id"]) is False
    assert loan_limit(user["university_id"]) == MAX_LOANS

#tests the even/odd rule on its own
@pytest.mark.parametrize("university_id, expected", [
    ("501000001", "student"),
    ("501000002", "faculty"),
    ("501000010", "faculty"),
    ("700000001", "student"),
    ("700000004", "faculty"),
])
def test_demo_status_rule(university_id, expected):
    assert demo_status(university_id) == expected

#tests that every demo account in the database follows the rule after setup
def test_all_demo_accounts_follow_the_rule():
    users = run("SELECT university_id, status FROM users")

    assert len(users) == 15
    for user in users:
        assert user["status"] == demo_status(user["university_id"])

#tests that an odd ID from the old faculty list now logs in as a student
def test_odd_700_account_is_now_a_student():
    lit_id = add_literature()
    _, user = log_in("700000001")

    result = borrow_literature(user["university_id"], lit_id)

    assert user["status"] == "student"
    assert is_staff("700000001") is False
    assert result["due_at"] != NO_DUE_DATE

#tests that the rule doesn't touch an account that isn't a demo account
def test_non_demo_account_is_left_alone():
    run("INSERT INTO users (university_id, email, password_hash, first_name, last_name, display_name, status) "
        "VALUES ('800000002', 'real.person@torontomu.ca', 'x', 'Real', 'Person', 'Real', 'student')")

    apply_demo_roles()

    assert is_staff("800000002") is False

#tests that an ID that doesn't exist is never treated as staff
def test_unknown_user_is_not_staff():
    assert is_staff("999999999") is False

#tests the whole path for staff: log in, borrow, no due date
def test_staff_login_then_borrow_has_no_due_date():
    lit_id = add_literature()
    _, user = log_in(STAFF)

    result = borrow_literature(user["university_id"], lit_id)

    assert result["due_at"] == NO_DUE_DATE
    assert library.count_active_loans(STAFF) == 1

#tests the whole path for a student: log in, borrow, due in 14 days
def test_student_login_then_borrow_due_in_14_days():
    lit_id = add_literature()
    _, user = log_in(STUDENT)

    result = borrow_literature(user["university_id"], lit_id)

    borrowed = one("SELECT borrowed_at FROM loan WHERE loan_id = %s", (result["loan_id"],))["borrowed_at"]
    assert as_time(result["due_at"]) - as_time(borrowed) == timedelta(days=14)

#tests that logging in with an email gives the same staff perks as the ID
def test_staff_login_with_email():
    lit_id = add_literature()
    _, user = log_in("liam.singh@torontomu.ca")

    result = borrow_literature(user["university_id"], lit_id)

    assert user["university_id"] == STAFF
    assert result["due_at"] == NO_DUE_DATE

#tests that a wrong password gives no session, so nothing can be borrowed
def test_wrong_password_cannot_borrow():
    with pytest.raises(AuthError):
        login(STAFF, "wrong password")

    assert library.count_active_loans(STAFF) == 0

#tests that the token stops working after logout
def test_logged_out_user_is_gone():
    token, user = log_in(STAFF)
    assert user is not None

    logout(token)

    assert get_current_user(token) is None

#tests that a student is stopped at 30 loans
def test_student_stops_at_student_limit():
    _, user = log_in(STUDENT)
    add_loans(STUDENT, MAX_LOANS)

    with pytest.raises(LoanError):
        borrow_literature(user["university_id"], add_literature("One More"))

#tests that staff can borrow past the student limit
def test_staff_can_pass_student_limit():
    _, user = log_in(STAFF)
    add_loans(STAFF, MAX_LOANS)

    borrow_literature(user["university_id"], add_literature("One More"))

    assert library.count_active_loans(STAFF) == MAX_LOANS + 1

#tests that staff are stopped at their own limit
def test_staff_stop_at_staff_limit():
    _, user = log_in(STAFF)
    add_loans(STAFF, STAFF_MAX_LOANS)

    with pytest.raises(LoanError):
        borrow_literature(user["university_id"], add_literature("One More"))

#tests that staff still can't borrow the same item twice
def test_staff_cannot_borrow_same_item_twice():
    lit_id = add_literature()
    _, user = log_in(STAFF)
    borrow_literature(user["university_id"], lit_id)

    with pytest.raises(LoanError):
        borrow_literature(user["university_id"], lit_id)

#tests that staff can't borrow when every slot is taken
def test_staff_cannot_borrow_without_a_free_slot():
    lit_id = add_literature(total_slots=1)
    _, student = log_in(STUDENT)
    _, staff = log_in(STAFF)
    borrow_literature(student["university_id"], lit_id)

    with pytest.raises(LoanError):
        borrow_literature(staff["university_id"], lit_id)


#=============================================================================================
#test_staff_holds.py
#=============================================================================================

#helper function to add a one-slot item that STUDENT_3 has already borrowed
#returns the literature id and the loan id so the test can free the slot
def add_full_literature(title="Test Book"):
    lit_id = add_book(1, title=title)
    loan = borrow_literature(STUDENT_3, lit_id)
    return lit_id, loan["loan_id"]

#tests that students on their own still queue in the order they arrived
def test_students_keep_normal_order():
    lit_id, _ = add_full_literature()

    first = place_hold(STUDENT_1, lit_id)
    skip(hours=1)
    second = place_hold(STUDENT_2, lit_id)

    assert first["queue_position"] == 1
    assert second["queue_position"] == 2

#tests that staff go ahead of a student who was already waiting
def test_staff_jump_ahead_of_students():
    lit_id, _ = add_full_literature()
    student = place_hold(STUDENT_1, lit_id)
    skip(hours=1)

    staff = place_hold(STAFF_1, lit_id)

    assert staff["queue_position"] == 1
    assert "#1" in staff["message"]
    assert get_queue_position(student["hold_id"], lit_id) == 2

#tests that two staff members are sorted by who placed their hold first
def test_staff_keep_order_among_staff():
    lit_id, _ = add_full_literature()
    student = place_hold(STUDENT_1, lit_id)
    skip(hours=1)
    staff_a = place_hold(STAFF_1, lit_id)
    skip(hours=1)
    staff_b = place_hold(STAFF_2, lit_id)

    order = [spot["hold_id"] for spot in get_queue(lit_id)]

    assert order == [staff_a["hold_id"], staff_b["hold_id"], student["hold_id"]]

#tests that the queue still hides who is waiting
def test_queue_does_not_show_users():
    lit_id, _ = add_full_literature()
    place_hold(STAFF_1, lit_id)

    assert "university_id" not in get_queue(lit_id)[0]

#tests the "you'll be #N in line" number shown before placing a hold
def test_next_position():
    lit_id, _ = add_full_literature()
    place_hold(STUDENT_1, lit_id)
    place_hold(STAFF_1, lit_id)

    assert next_position(STAFF_2, lit_id) == 2
    assert next_position(STUDENT_2, lit_id) == 3

#tests that the holds page shows the student's new position after staff join
def test_holds_page_shows_staff_first_position():
    lit_id, _ = add_full_literature()
    place_hold(STUDENT_1, lit_id)
    place_hold(STAFF_1, lit_id)

    my_holds = get_my_holds(STUDENT_1)

    assert my_holds[0]["queue_position"] == 2
    assert my_holds[0]["queue_length"] == 2

#tests that a freed slot is offered to staff before the student who waited longer
def test_free_slot_offered_to_staff_first():
    lit_id, loan_id = add_full_literature()
    student = place_hold(STUDENT_1, lit_id)
    skip(hours=1)
    staff = place_hold(STAFF_1, lit_id)

    return_loan(STUDENT_3, loan_id)
    process_holds()

    assert get_hold(staff["hold_id"])["status"] == "READY"
    assert get_hold(student["hold_id"])["status"] == "WAITING"

#tests that a hold accepted by staff becomes a loan with no due date
def test_staff_accept_hold_has_no_due_date():
    lit_id, loan_id = add_full_literature()
    staff = place_hold(STAFF_1, lit_id)
    return_loan(STUDENT_3, loan_id)
    process_holds()

    result = accept_hold(STAFF_1, staff["hold_id"])

    assert result["due_at"] == NO_DUE_DATE
    assert get_hold(staff["hold_id"])["status"] == "ACCEPTED"

#tests that a hold accepted by a student still gets the normal 14 days
def test_student_accept_hold_still_14_days():
    lit_id, loan_id = add_full_literature()
    student = place_hold(STUDENT_1, lit_id)
    return_loan(STUDENT_3, loan_id)
    process_holds()

    result = accept_hold(STUDENT_1, student["hold_id"])

    assert as_time(result["due_at"]) - as_time(library.stamp(library.now())) == timedelta(days=14)

#tests that when staff decline, the slot moves on to the student
def test_staff_decline_passes_slot_to_student():
    lit_id, loan_id = add_full_literature()
    student = place_hold(STUDENT_1, lit_id)
    staff = place_hold(STAFF_1, lit_id)
    return_loan(STUDENT_3, loan_id)
    process_holds()

    decline_hold(STAFF_1, staff["hold_id"])

    assert get_hold(staff["hold_id"])["status"] == "DECLINED"
    assert get_hold(student["hold_id"])["status"] == "READY"

#tests that staff who don't answer in 72 hrs lose the offer like anyone else
def test_staff_offer_expires_after_72_hours():
    lit_id, loan_id = add_full_literature()
    student = place_hold(STUDENT_1, lit_id)
    staff = place_hold(STAFF_1, lit_id)
    return_loan(STUDENT_3, loan_id)
    process_holds()

    expired = process_holds(now=library.now() + timedelta(hours=73))

    assert [hold["hold_id"] for hold in expired] == [staff["hold_id"]]
    assert get_hold(student["hold_id"])["status"] == "READY"

#tests that staff can't take an offer that already went to a student
def test_staff_do_not_take_a_ready_offer():
    lit_id, loan_id = add_full_literature()
    student = place_hold(STUDENT_1, lit_id)
    return_loan(STUDENT_3, loan_id)
    process_holds()

    staff = place_hold(STAFF_1, lit_id)
    process_holds()

    assert get_hold(student["hold_id"])["status"] == "READY"
    assert get_hold(staff["hold_id"])["status"] == "WAITING"
    with pytest.raises(LoanError):
        accept_hold(STAFF_1, staff["hold_id"])


#=============================================================================================
#test_staff_reader.py
#=============================================================================================

#tests that staff can open an item they borrowed
def test_staff_can_open_borrowed_item():
    lit_id = add_literature(title="Staff Book")
    borrow_literature(STAFF, lit_id)

    assert open_literature(STAFF, lit_id) == "staff-book.txt"
    assert loan_due_at(STAFF, lit_id) == NO_DUE_DATE

#tests that staff can still read long after a student loan would have ended
def test_staff_can_still_read_after_a_year():
    lit_id = add_literature()
    borrow_literature(STAFF, lit_id)
    skip(days=365)

    assert open_literature(STAFF, lit_id) == "test-book.txt"

#tests that a student is still locked out after 14 days
def test_student_still_locked_out_after_14_days():
    lit_id = add_literature()
    borrow_literature(STUDENT, lit_id)

    skip(days=13)
    open_literature(STUDENT, lit_id)
    skip(days=2)
    with pytest.raises(LoanError):
        open_literature(STUDENT, lit_id)

#tests that the automatic return leaves staff loans alone
def test_auto_return_skips_staff_loans():
    lit_id = add_literature()
    borrow_literature(STAFF, lit_id)
    borrow_literature(STUDENT, lit_id)
    skip(days=30)

    library.check_due_items()

    returned = run("SELECT lu.university_id FROM loan lo JOIN library_user lu ON lu.user_id = lo.user_id "
                   "WHERE lo.return_type = 'AUTO'")
    assert [loan["university_id"] for loan in returned] == [STUDENT]
    assert loan_due_at(STAFF, lit_id) == NO_DUE_DATE

#tests that staff can't read once they hand the item back
def test_staff_cannot_read_after_returning():
    lit_id = add_literature()
    loan = borrow_literature(STAFF, lit_id)
    skip(days=100)
    return_loan(STAFF, loan["loan_id"])

    with pytest.raises(LoanError):
        open_literature(STAFF, lit_id)

#tests that being staff isn't enough, they still need their own loan
def test_staff_need_their_own_loan():
    lit_id = add_literature()
    borrow_literature(OTHER_STAFF, lit_id)

    with pytest.raises(LoanError):
        open_literature(STAFF, lit_id)

#tests the text shown on the loans page instead of the far away date
def test_no_due_date_text():
    lit_id = add_literature()
    staff_loan = borrow_literature(STAFF, lit_id)
    student_loan = borrow_literature(STUDENT, lit_id)

    assert due_text(staff_loan["due_at"]) == "No due date"
    assert time_left_text(staff_loan["due_at"]) == "Keep as long as you need"
    assert due_text(student_loan["due_at"]) == student_loan["due_at"]
    borrowed = as_time(one("SELECT borrowed_at FROM loan WHERE loan_id = %s", (student_loan["loan_id"],))["borrowed_at"])
    assert time_left_text(student_loan["due_at"], now=borrowed) == "14d 0h 0m 0s"


#=============================================================================================
#Also checked now that library.py uses the staff files
#=============================================================================================

#the Personal Library shows the staff wording and no countdown
def test_personal_library_shows_staff_loans():
    lit_id = add_literature()
    borrow_literature(STAFF, lit_id)
    [loan] = library.my_loans(library.user_id_for(STAFF))
    assert loan["no_due_date"] is True
    assert loan["time_left"] == "Keep as long as you need"

#a faculty loan has nothing to renew
def test_staff_loan_renew_is_refused_with_reason():
    lit_id = add_literature()
    loan = borrow_literature(STAFF, lit_id)
    with pytest.raises(LoanError, match="no due date"):
        library.renew(library.user_id_for(STAFF), loan["loan_id"])

#a slot freed by cancelling a READY hold also goes to staff first (library.cancel_hold -> offer_next_hold)
def test_cancelled_offer_goes_to_staff_first():
    lit_id, loan_id = add_full_literature()
    first = place_hold(STUDENT_1, lit_id)
    return_loan(STUDENT_3, loan_id)  # STUDENT_1 gets the offer
    student = place_hold(STUDENT_2, lit_id)
    skip(hours=1)
    staff = place_hold(STAFF_1, lit_id)
    library.cancel_hold(library.user_id_for(STUDENT_1), first["hold_id"])
    assert get_hold(staff["hold_id"])["status"] == "READY"
    assert get_hold(student["hold_id"])["status"] == "WAITING"
