#Tests for the University Digital Borrowing System, Sprints 1 to 3
#checks backend/library.py and backend/auth.py against the user stories, business rules (BR)
#and non-functional requirements (NFR) in the UDBS project outline
#
#Sprint 1: log in and out (US-01), search (US-02), literature details (US-04), personal info (US-15)
#Sprint 2: borrow (US-06), remaining time (US-07), read (US-03), automatic return (US-05),
#          early return (US-09), shortened demo loans (NFR-05)
#Sprint 3: holds and the hold queue (US-10), the holds page (US-11), the decision window (US-12),
#          cancelling holds (US-13), passing freed slots to the queue (BR-15), renewing loans (US-08),
#          shortened demo hold windows (NFR-05)
#
#how to run (from the backend folder):
#   pip install pytest
#   set TEST_DATABASE_URL to a postgres connection string, then run: pytest test_udbs.py -v
#
#every test builds its own tables inside a schema called udbs_test and deletes it afterwards,
#so the normal tables are never touched. it's still safest to point TEST_DATABASE_URL at a
#separate test database (or a local postgres) instead of the live one

import os
import pathlib
from datetime import datetime, timedelta

import pytest

TEST_URL = os.environ.get("TEST_DATABASE_URL", "")
if not TEST_URL:
    pytest.skip("Set TEST_DATABASE_URL to run the UDBS tests.", allow_module_level=True)

#database.py reads DATABASE_URL, so point it at the test database before anything connects
os.environ["DATABASE_URL"] = TEST_URL
os.environ.pop("UDBS_DEMO_LOAN_MINUTES", None)  # use the normal 14 day loans in every test
os.environ.pop("UDBS_DEMO_HOLD_MINUTES", None)  # and the normal 72 hour hold window

import auth
import database
import library
from library import LibraryError

SCHEMA_FILE = pathlib.Path(__file__).resolve().parent.parent / "supabase" / "schema.sql"
TIME = "%Y-%m-%d %H:%M"  # how library.py saves times


#setup

@pytest.fixture(autouse=True)
def db(monkeypatch):
    #fresh tables for every test, opened the same way api.py opens them for a request
    raw = database.open_db()
    token = database._current.set(raw)
    try:
        for sql in ("DROP SCHEMA IF EXISTS udbs_test CASCADE", "CREATE SCHEMA udbs_test", "SET search_path TO udbs_test"):
            run(sql)
        for statement in schema_statements():
            run(statement)
        run("INSERT INTO category (name) VALUES ('Test Category')")
        raw.commit()

        #normal rules instead of the small Sprint 2 testing caps
        monkeypatch.setattr(library, "TEST_MAX_LOANS", 30)  # BR-02
        monkeypatch.setattr(library, "TEST_CONCURRENT_LOANS", 15)  # BR-03
        monkeypatch.setattr(library, "skipped_time", timedelta())
        yield
    finally:
        raw.rollback()
        run("DROP SCHEMA IF EXISTS udbs_test CASCADE")
        raw.commit()
        database._current.reset(token)
        raw.close()


def schema_statements():
    #schema.sql split into single statements, with the -- comments taken out
    lines = [line.split("--")[0] for line in SCHEMA_FILE.read_text(encoding="utf-8").splitlines()]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


#helpers

def run(sql, params=()):
    #runs one statement through the same connection library.py uses
    return database.conn.execute(sql, params).fetchall()


def one(sql, params=()):
    rows = run(sql, params)
    return rows[0] if rows else None


def add_user(max_holds=3, max_loans=150):
    #adds a library user and returns their user_id
    n = one("SELECT COUNT(*) AS n FROM library_user")["n"] + 1
    run(
        "INSERT INTO library_user (university_id, first_name, last_name, email, created_at, max_loans, max_holds) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (f"50100000{n}", "Test", f"User{n}", f"user{n}@test.ca", "2026-11-01 09:00", max_loans, max_holds),
    )
    return one("SELECT user_id FROM library_user WHERE university_id = %s", (f"50100000{n}",))["user_id"]


def add_book(slots=1, title="Test Book", authors=(), keywords=(), category="Test Category"):
    #adds a book with the given number of access slots and returns its literature_id
    run("INSERT INTO category (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (category,))
    run(
        "INSERT INTO literature (category_id, title, file_url, total_access_slots) "
        "VALUES ((SELECT category_id FROM category WHERE name = %s), %s, %s, %s)",
        (category, title, title.lower().replace(" ", "-") + ".txt", slots),
    )
    book = one("SELECT MAX(literature_id) AS id FROM literature")["id"]
    for name in authors:
        run("INSERT INTO author (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (name,))
        run("INSERT INTO literature_author (literature_id, author_id) VALUES (%s, (SELECT author_id FROM author WHERE name = %s))", (book, name))
    for word in keywords:
        run("INSERT INTO keyword (word) VALUES (%s) ON CONFLICT (word) DO NOTHING", (word,))
        run("INSERT INTO literature_keyword (literature_id, keyword_id) VALUES (%s, (SELECT keyword_id FROM keyword WHERE word = %s))", (book, word))
    return book


def add_university_user(university_id="501000001", email="student@torontomu.ca", password="Library2026!"):
    #adds a university account (the users table) that can log in
    run(
        "INSERT INTO users (university_id, email, password_hash, first_name, last_name, display_name, pronouns, status) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (university_id, email, auth.hash_password(password), "Test", "Student", "Test Student", "they/them", "student"),
    )


def hold_of(user_id, book_id):
    return one("SELECT * FROM hold WHERE user_id = %s AND literature_id = %s ORDER BY hold_id DESC", (user_id, book_id))


def hold_row(hold_id):
    return one("SELECT * FROM hold WHERE hold_id = %s", (hold_id,))


def loan_of(user_id, book_id):
    return one("SELECT * FROM loan WHERE user_id = %s AND literature_id = %s ORDER BY loan_id DESC", (user_id, book_id))


def notes(user_id, kind):
    return run("SELECT * FROM notification WHERE user_id = %s AND type = %s", (user_id, kind))


def as_time(text):
    return datetime.strptime(text, TIME)


def skip(**amount):
    #moves the library clock forward, the same way the demo "skip ahead" does
    library.skipped_time += timedelta(**amount)


def full_book_with_queue(holders):
    #a book with 1 slot borrowed by an owner, and the given users waiting in that order
    owner = add_user()
    book = add_book(1)
    library.borrow(owner, book)
    for user in holders:
        library.place_hold(user, book)
    return owner, book


def free_the_slot(owner, book):
    #the owner returns the book early, which offers the slot to the queue
    library.return_book(owner, loan_of(owner, book)["loan_id"])


#=============================================================================================
#Sprint 1
#=============================================================================================

#US-01: log in and log out

def test_login_with_university_id():
    add_university_user()
    token = auth.login("501000001", "Library2026!")
    user = auth.get_current_user(token)
    assert user["university_id"] == "501000001"
    assert user["display_name"] == "Test Student"


def test_login_with_email():
    add_university_user()
    token = auth.login("student@torontomu.ca", "Library2026!")
    assert auth.get_current_user(token)["university_id"] == "501000001"


def test_login_wrong_password_fails():
    add_university_user()
    with pytest.raises(auth.AuthError):
        auth.login("501000001", "wrong password")
    assert one("SELECT COUNT(*) AS n FROM sessions")["n"] == 0


def test_login_unknown_user_gets_same_message_as_wrong_password():
    #the same message for both so nobody can tell which IDs exist
    add_university_user()
    with pytest.raises(auth.AuthError) as unknown:
        auth.login("999999999", "Library2026!")
    with pytest.raises(auth.AuthError) as wrong:
        auth.login("501000001", "nope")
    assert str(unknown.value) == str(wrong.value)


@pytest.mark.parametrize("identifier, password", [("", "Library2026!"), ("501000001", ""), ("   ", "Library2026!"), (None, None)])
def test_login_empty_inputs_fail(identifier, password):
    add_university_user()
    with pytest.raises(auth.AuthError):
        auth.login(identifier, password)


def test_first_login_creates_library_account_with_rule_limits():
    #BR-02 and BR-04: 30 loans and 15 holds
    add_university_user()
    user = auth.get_current_user(auth.login("501000001", "Library2026!"))
    account = one("SELECT * FROM library_user WHERE user_id = %s", (user["user_id"],))
    assert (account["max_loans"], account["max_holds"]) == (30, 15)


def test_logout_ends_session():
    add_university_user()
    token = auth.login("501000001", "Library2026!")
    auth.logout(token)
    assert auth.get_current_user(token) is None


def test_logout_only_ends_that_session():
    add_university_user()
    laptop = auth.login("501000001", "Library2026!")
    phone = auth.login("501000001", "Library2026!")
    auth.logout(laptop)
    assert auth.get_current_user(phone) is not None


def test_expired_session_is_refused_and_deleted():
    add_university_user()
    token = auth.login("501000001", "Library2026!")
    run("UPDATE sessions SET expires_at = %s WHERE token = %s", ("2000-01-01 00:00:00", token))
    assert auth.get_current_user(token) is None
    assert one("SELECT COUNT(*) AS n FROM sessions WHERE token = %s", (token,))["n"] == 0


@pytest.mark.parametrize("token", [None, "", "not-a-real-token"])
def test_bad_token_is_not_logged_in(token):
    assert auth.get_current_user(token) is None


def test_password_is_not_stored_as_plain_text():
    add_university_user()
    stored = one("SELECT password_hash FROM users WHERE university_id = '501000001'")["password_hash"]
    assert "Library2026!" not in stored
    assert auth.verify_password("Library2026!", stored)


#US-02: search by title, author, category or keyword

@pytest.fixture
def catalogue():
    return {
        "db": add_book(15, "Database System Concepts", ["Abraham Silberschatz"], ["databases", "sql"], "Computer Science"),
        "algo": add_book(15, "Introduction to Algorithms", ["Thomas Cormen"], ["algorithms"], "Computer Science"),
        "time": add_book(15, "A Brief History of Time", ["Stephen Hawking"], ["space", "black holes"], "Physics"),
    }


def found(text):
    return {b["literature_id"] for b in library.search(text)}


def test_search_by_title(catalogue):
    assert found("Algorithms") == {catalogue["algo"]}


def test_search_by_author(catalogue):
    assert found("Hawking") == {catalogue["time"]}


def test_search_by_category(catalogue):
    assert found("Computer Science") == {catalogue["db"], catalogue["algo"]}


def test_search_by_keyword(catalogue):
    assert found("black holes") == {catalogue["time"]}


def test_search_ignores_upper_and_lower_case(catalogue):
    assert found("dAtAbAsE") == {catalogue["db"]}


def test_search_matches_part_of_a_word(catalogue):
    assert found("Silber") == {catalogue["db"]}


def test_search_lists_each_book_once(catalogue):
    #Database System Concepts has two keywords that both contain an s
    ids = [b["literature_id"] for b in library.search("s")]
    assert len(ids) == len(set(ids))


def test_search_with_no_match_is_empty(catalogue):
    assert library.search("zzzz no such book") == []


def test_empty_search_shows_whole_catalogue(catalogue):
    assert found("") == set(catalogue.values())


def test_search_results_show_free_slots(catalogue):
    library.borrow(add_user(), catalogue["db"])
    result = [b for b in library.search("Database") if b["literature_id"] == catalogue["db"]][0]
    assert result["free_slots"] == 14


#US-04: literature details and availability

def test_details_show_title_author_and_keywords():
    book = add_book(15, "Clean Code", ["Robert Martin"], ["programming"], "Software Engineering")
    details = library.book_details(book)
    assert details["title"] == "Clean Code"
    assert details["authors"] == ["Robert Martin"]
    assert details["keywords"] == ["programming"]
    assert details["total_access_slots"] == 15


def test_details_show_free_slots_and_queue():
    b = add_user()
    owner, book = full_book_with_queue([b])
    details = library.book_details(book)
    assert details["free_slots"] == 0
    assert details["people_waiting"] == 1


def test_details_free_slots_go_down_when_borrowed():
    book = add_book(15)
    library.borrow(add_user(), book)
    assert library.book_details(book)["free_slots"] == 14


def test_details_for_missing_book_fail():
    with pytest.raises(LibraryError):
        library.book_details(99999)


#US-15: view and edit personal information

def logged_in_user():
    add_university_user()
    return auth.get_current_user(auth.login("501000001", "Library2026!"))["user_id"]


def test_profile_shows_personal_info():
    profile = library.get_profile(logged_in_user())
    assert profile["university_id"] == "501000001"
    assert profile["email"] == "student@torontomu.ca"
    assert (profile["first_name"], profile["last_name"]) == ("Test", "Student")
    assert profile["display_name"] == "Test Student"
    assert profile["pronouns"] == "they/them"
    assert profile["status"] == "student"


def test_preferred_name_and_pronouns_can_be_changed():
    user_id = logged_in_user()
    library.update_profile(user_id, "  Tess  ", "she/her")
    profile = library.get_profile(user_id)
    assert (profile["display_name"], profile["pronouns"]) == ("Tess", "she/her")


def test_legal_name_id_email_and_status_stay_the_same():
    user_id = logged_in_user()
    before = library.get_profile(user_id)
    library.update_profile(user_id, "Tess", "she/her")
    after = library.get_profile(user_id)
    for field in ("university_id", "first_name", "last_name", "email", "status"):
        assert after[field] == before[field]


def test_new_preferred_name_shows_after_logging_in_again():
    user_id = logged_in_user()
    library.update_profile(user_id, "Tess", None)
    assert auth.get_current_user(auth.login("501000001", "Library2026!"))["display_name"] == "Tess"


def test_pronouns_can_be_cleared():
    user_id = logged_in_user()
    library.update_profile(user_id, "Tess", "  ")
    assert library.get_profile(user_id)["pronouns"] is None


@pytest.mark.parametrize("name, pronouns", [("", "she/her"), ("   ", None), ("x" * 51, None), ("Tess", "x" * 31)])
def test_bad_profile_changes_are_refused(name, pronouns):
    user_id = logged_in_user()
    with pytest.raises(LibraryError):
        library.update_profile(user_id, name, pronouns)
    assert library.get_profile(user_id)["display_name"] == "Test Student"


#=============================================================================================
#Sprint 2
#=============================================================================================

#US-06: borrow available literature

def test_borrow_adds_loan_to_personal_library():
    a = add_user()
    book = add_book(15)
    library.borrow(a, book)
    loans = library.my_loans(a)
    assert [l["literature_id"] for l in loans] == [book]


def test_borrow_records_time_and_14_day_due_date():
    #BR-01 and FR-10
    a = add_user()
    book = add_book(15)
    library.borrow(a, book)
    loan = loan_of(a, book)
    assert loan["status"] == "ACTIVE"
    assert as_time(loan["due_at"]) - as_time(loan["borrowed_at"]) == timedelta(days=14)


def test_borrow_lowers_free_slots():
    book = add_book(15)
    library.borrow(add_user(), book)
    assert library.free_slots(book) == 14


def test_borrow_same_book_twice_fails():
    a = add_user()
    book = add_book(15)
    library.borrow(a, book)
    with pytest.raises(LibraryError):
        library.borrow(a, book)
    assert library.free_slots(book) == 14


def test_borrow_blocked_at_30_loans():
    #BR-02
    a = add_user(max_loans=30)
    for n in range(30):
        library.borrow(a, add_book(15, f"Book {n}"))
    with pytest.raises(LibraryError):
        library.borrow(a, add_book(15, "Book 31"))
    assert library.active_loan_count(a) == 30


def test_borrow_blocked_when_all_15_slots_are_taken():
    #BR-03 and BR-05
    book = add_book(15)
    for _ in range(15):
        library.borrow(add_user(), book)
    late = add_user()
    with pytest.raises(LibraryError):
        library.borrow(late, book)
    assert library.free_slots(book) == 0
    assert loan_of(late, book) is None


def test_borrow_missing_book_fails():
    with pytest.raises(LibraryError):
        library.borrow(add_user(), 99999)


#US-07: remaining loan time

def test_loans_show_borrow_date_due_date_and_time_left():
    a = add_user()
    library.borrow(a, add_book(15))
    loan = library.my_loans(a)[0]
    assert loan["due_at"] is not None
    assert loan["time_left"].startswith("13 days") or loan["time_left"].startswith("14 days")


def test_time_left_goes_down_over_time():
    a = add_user()
    library.borrow(a, add_book(15))
    skip(days=10)
    assert library.my_loans(a)[0]["time_left"].startswith("3 days") or library.my_loans(a)[0]["time_left"].startswith("4 days")


def test_loans_listed_soonest_due_first():
    a = add_user()
    first = add_book(15, "First")
    library.borrow(a, first)
    skip(days=1)
    library.borrow(a, add_book(15, "Second"))
    assert library.my_loans(a)[0]["literature_id"] == first


def test_loans_only_show_own_active_loans():
    a, b = add_user(), add_user()
    book = add_book(15)
    library.borrow(a, book)
    library.borrow(b, add_book(15, "Other"))
    library.return_book(a, loan_of(a, book)["loan_id"])
    assert library.my_loans(a) == []


#US-03 and NFR-04: read borrowed literature

def test_read_works_with_active_loan():
    a = add_user()
    book = add_book(15, "Clean Code")
    library.borrow(a, book)
    assert library.read_book(a, book) == "clean-code.txt"


def test_read_blocked_without_loan():
    with pytest.raises(LibraryError):
        library.read_book(add_user(), add_book(15))


def test_read_blocked_after_early_return():
    a = add_user()
    book = add_book(15)
    library.borrow(a, book)
    library.return_book(a, loan_of(a, book)["loan_id"])
    with pytest.raises(LibraryError):
        library.read_book(a, book)


def test_read_blocked_after_loan_expires():
    #the /api/read route returns expired loans first, then opens the book
    a = add_user()
    book = add_book(15)
    library.borrow(a, book)
    skip(days=14)
    library.check_due_items()
    with pytest.raises(LibraryError):
        library.read_book(a, book)


def test_read_blocked_for_someone_elses_loan():
    a, b = add_user(), add_user()
    book = add_book(15)
    library.borrow(a, book)
    with pytest.raises(LibraryError):
        library.read_book(b, book)


#US-05: automatic return

def test_loan_returns_automatically_when_due():
    a = add_user()
    book = add_book(15)
    library.borrow(a, book)
    skip(days=14)
    library.check_due_items()
    loan = loan_of(a, book)
    assert (loan["status"], loan["return_type"]) == ("RETURNED", "AUTO")
    assert loan["returned_at"] is not None
    assert library.my_loans(a) == []


def test_loan_not_returned_before_due():
    a = add_user()
    book = add_book(15)
    library.borrow(a, book)
    skip(days=13, hours=23)
    library.check_due_items()
    assert loan_of(a, book)["status"] == "ACTIVE"


def test_auto_return_frees_slot_when_nobody_is_waiting():
    a = add_user()
    book = add_book(15)
    library.borrow(a, book)
    skip(days=14)
    library.check_due_items()
    assert library.free_slots(book) == 15


def test_auto_return_only_returns_expired_loans():
    a = add_user()
    old, new = add_book(15, "Old"), add_book(15, "New")
    library.borrow(a, old)
    skip(days=7)
    library.borrow(a, new)
    skip(days=7)
    library.check_due_items()
    assert loan_of(a, old)["status"] == "RETURNED"
    assert loan_of(a, new)["status"] == "ACTIVE"


def test_auto_return_running_twice_does_nothing_more():
    a = add_user()
    book = add_book(15)
    library.borrow(a, book)
    skip(days=14)
    library.check_due_items()
    library.check_due_items()
    assert len(notes(a, "LOAN_RETURNED")) == 1
    assert library.free_slots(book) == 15


#US-09: early return

def test_early_return():
    a = add_user()
    book = add_book(15)
    library.borrow(a, book)
    library.return_book(a, loan_of(a, book)["loan_id"])
    loan = loan_of(a, book)
    assert (loan["status"], loan["return_type"]) == ("RETURNED", "EARLY")
    assert loan["returned_at"] is not None
    assert library.free_slots(book) == 15
    assert library.my_loans(a) == []


def test_early_return_sends_loan_returned_notification():
    a = add_user()
    book = add_book(15)
    library.borrow(a, book)
    library.return_book(a, loan_of(a, book)["loan_id"])
    assert len(notes(a, "LOAN_RETURNED")) == 1


def test_early_return_only_affects_that_loan():
    a = add_user()
    one_book, other = add_book(15, "One"), add_book(15, "Other")
    library.borrow(a, one_book)
    library.borrow(a, other)
    library.return_book(a, loan_of(a, one_book)["loan_id"])
    assert loan_of(a, other)["status"] == "ACTIVE"


def test_return_twice_fails_and_frees_only_one_slot():
    a = add_user()
    book = add_book(15)
    library.borrow(a, book)
    loan_id = loan_of(a, book)["loan_id"]
    library.return_book(a, loan_id)
    with pytest.raises(LibraryError):
        library.return_book(a, loan_id)
    assert library.free_slots(book) == 15


def test_return_someone_elses_loan_fails():
    a, b = add_user(), add_user()
    book = add_book(15)
    library.borrow(a, book)
    with pytest.raises(LibraryError):
        library.return_book(b, loan_of(a, book)["loan_id"])
    assert loan_of(a, book)["status"] == "ACTIVE"


def test_return_missing_loan_fails():
    with pytest.raises(LibraryError):
        library.return_book(add_user(), 99999)


#NFR-05: shortened loans for demos

def test_demo_loan_minutes_shortens_new_loans(monkeypatch):
    monkeypatch.setenv("UDBS_DEMO_LOAN_MINUTES", "3")
    a = add_user()
    book = add_book(15)
    library.borrow(a, book)
    loan = loan_of(a, book)
    assert as_time(loan["due_at"]) - as_time(loan["borrowed_at"]) == timedelta(minutes=3)


def test_short_demo_loan_returns_automatically(monkeypatch):
    monkeypatch.setenv("UDBS_DEMO_LOAN_MINUTES", "3")
    a = add_user()
    book = add_book(15)
    library.borrow(a, book)
    skip(minutes=3)
    library.check_due_items()
    assert loan_of(a, book)["return_type"] == "AUTO"


@pytest.mark.parametrize("value", ["0", "-5", "abc", "525601"])
def test_bad_demo_loan_minutes_are_refused(monkeypatch, value):
    monkeypatch.setenv("UDBS_DEMO_LOAN_MINUTES", value)
    a = add_user()
    book = add_book(15)
    with pytest.raises(LibraryError):
        library.borrow(a, book)
    assert loan_of(a, book) is None


#=============================================================================================
#Sprint 3
#=============================================================================================

#US-10: place a hold and join the queue

def test_hold_placed_when_no_free_slot():
    b = add_user()
    _, book = full_book_with_queue([b])
    hold = hold_of(b, book)
    assert hold["status"] == "WAITING"
    assert hold["queue_position"] == 1
    assert hold["placed_at"] is not None


def test_queue_positions_go_in_order():
    b, c, d = add_user(), add_user(), add_user()
    _, book = full_book_with_queue([b, c, d])
    assert [hold_of(u, book)["queue_position"] for u in (b, c, d)] == [1, 2, 3]
    assert library.people_waiting(book) == 3


def test_hold_refused_when_slot_is_free():
    a = add_user()
    book = add_book(1)
    with pytest.raises(LibraryError):
        library.place_hold(a, book)
    assert hold_of(a, book) is None


def test_hold_refused_when_already_on_loan():
    a = add_user()
    book = add_book(1)
    library.borrow(a, book)
    with pytest.raises(LibraryError):
        library.place_hold(a, book)


def test_hold_refused_twice_for_same_book():
    b = add_user()
    _, book = full_book_with_queue([b])
    with pytest.raises(LibraryError):
        library.place_hold(b, book)
    assert library.people_waiting(book) == 1


def test_hold_limit_is_enforced():
    b = add_user(max_holds=2)
    for _ in range(2):
        full_book_with_queue([b])
    _, third = full_book_with_queue([])
    with pytest.raises(LibraryError):
        library.place_hold(b, third)


def test_hold_limit_of_15():
    #BR-04
    b = add_user(max_holds=15)
    for _ in range(15):
        full_book_with_queue([b])
    _, extra = full_book_with_queue([])
    with pytest.raises(LibraryError):
        library.place_hold(b, extra)
    assert one("SELECT COUNT(*) AS n FROM hold WHERE user_id = %s", (b,))["n"] == 15


def test_ready_hold_counts_towards_limit():
    b = add_user(max_holds=1)
    owner, book = full_book_with_queue([b])
    free_the_slot(owner, book)
    assert hold_of(b, book)["status"] == "READY"
    _, other = full_book_with_queue([])
    with pytest.raises(LibraryError):
        library.place_hold(b, other)


def test_hold_on_missing_book_fails():
    a = add_user()
    with pytest.raises(LibraryError):
        library.place_hold(a, 99999)


def test_borrow_blocked_while_slot_is_saved_for_queue():
    #BR-07: people in line go first, so nobody can jump ahead of a READY hold
    b, c = add_user(), add_user()
    owner, book = full_book_with_queue([b])
    free_the_slot(owner, book)
    with pytest.raises(LibraryError):
        library.borrow(c, book)
    assert loan_of(c, book) is None


#US-11: holds page data

def test_my_holds_shows_title_status_and_position():
    b, c = add_user(), add_user()
    _, book = full_book_with_queue([b, c])
    holds = library.my_holds(c)
    assert len(holds) == 1
    assert holds[0]["title"] == "Test Book"
    assert holds[0]["status"] == "WAITING"
    assert holds[0]["queue_position"] == 2


def test_my_holds_shows_queue_length_and_book():
    b, c, d = add_user(), add_user(), add_user()
    _, book = full_book_with_queue([b, c, d])
    hold = library.my_holds(c)[0]
    assert hold["literature_id"] == book
    assert (hold["queue_position"], hold["queue_length"]) == (2, 3)


def test_hold_queue_preview_shows_positions_without_names():
    #US-10: the current queue is shown before a hold is confirmed
    b, c = add_user(), add_user()
    _, book = full_book_with_queue([b, c])
    queue = library.hold_queue(book)
    assert [spot["position"] for spot in queue] == [1, 2]
    assert all(set(spot) == {"position", "placed_at"} for spot in queue)


def test_hold_queue_preview_for_missing_book_fails():
    with pytest.raises(LibraryError):
        library.hold_queue(99999)


def test_my_holds_shows_deadline_for_ready_hold():
    b = add_user()
    owner, book = full_book_with_queue([b])
    free_the_slot(owner, book)
    hold = library.my_holds(b)[0]
    assert hold["status"] == "READY"
    assert hold["queue_position"] is None
    assert hold["decision_deadline"] is not None


def test_my_holds_only_shows_own_open_holds():
    b, c = add_user(), add_user()
    _, book1 = full_book_with_queue([b, c])
    _, book2 = full_book_with_queue([b])
    library.cancel_hold(b, hold_of(b, book2)["hold_id"])
    holds = library.my_holds(b)
    assert [h["hold_id"] for h in holds] == [hold_of(b, book1)["hold_id"]]


def test_my_holds_oldest_first():
    b = add_user()
    _, first = full_book_with_queue([b])
    skip(minutes=5)
    _, second = full_book_with_queue([b])
    assert [h["hold_id"] for h in library.my_holds(b)] == [hold_of(b, first)["hold_id"], hold_of(b, second)["hold_id"]]


def test_my_holds_empty_when_no_holds():
    assert library.my_holds(add_user()) == []


#US-13: cancel a hold

def test_cancel_waiting_hold():
    b = add_user()
    _, book = full_book_with_queue([b])
    hold_id = hold_of(b, book)["hold_id"]
    library.cancel_hold(b, hold_id)
    assert hold_row(hold_id)["status"] == "CANCELLED"
    assert library.my_holds(b) == []
    assert library.people_waiting(book) == 0


def test_cancel_moves_everyone_behind_up():
    b, c, d = add_user(), add_user(), add_user()
    _, book = full_book_with_queue([b, c, d])
    library.cancel_hold(b, hold_of(b, book)["hold_id"])
    assert hold_of(c, book)["queue_position"] == 1
    assert hold_of(d, book)["queue_position"] == 2


def test_cancel_ready_hold_passes_slot_to_next_person():
    b, c = add_user(), add_user()
    owner, book = full_book_with_queue([b, c])
    free_the_slot(owner, book)
    library.cancel_hold(b, hold_of(b, book)["hold_id"])
    assert hold_of(c, book)["status"] == "READY"


def test_cancel_ready_hold_with_empty_queue_frees_slot():
    b = add_user()
    owner, book = full_book_with_queue([b])
    free_the_slot(owner, book)
    library.cancel_hold(b, hold_of(b, book)["hold_id"])
    assert library.free_slots(book) == 1


def test_cancel_other_users_hold_fails():
    b, c = add_user(), add_user()
    _, book = full_book_with_queue([b])
    hold_id = hold_of(b, book)["hold_id"]
    with pytest.raises(LibraryError):
        library.cancel_hold(c, hold_id)
    assert hold_row(hold_id)["status"] == "WAITING"


def test_cancel_twice_fails():
    b = add_user()
    _, book = full_book_with_queue([b])
    hold_id = hold_of(b, book)["hold_id"]
    library.cancel_hold(b, hold_id)
    with pytest.raises(LibraryError):
        library.cancel_hold(b, hold_id)


def test_cancel_missing_hold_fails():
    with pytest.raises(LibraryError):
        library.cancel_hold(add_user(), 99999)


def test_cancel_frees_up_hold_limit():
    b = add_user(max_holds=1)
    _, book1 = full_book_with_queue([b])
    library.cancel_hold(b, hold_of(b, book1)["hold_id"])
    _, book2 = full_book_with_queue([b])
    assert hold_of(b, book2)["status"] == "WAITING"


#US-12 and BR-15: a freed slot is offered to the queue

def test_return_offers_slot_to_first_in_line():
    b, c = add_user(), add_user()
    owner, book = full_book_with_queue([b, c])
    free_the_slot(owner, book)
    assert hold_of(b, book)["status"] == "READY"
    assert hold_of(c, book)["status"] == "WAITING"
    assert hold_of(c, book)["queue_position"] == 1


def test_offer_gives_72_hours():
    b = add_user()
    owner, book = full_book_with_queue([b])
    free_the_slot(owner, book)
    hold = hold_of(b, book)
    assert as_time(hold["decision_deadline"]) - as_time(hold["ready_at"]) == timedelta(hours=72)


def test_saved_slot_is_not_available_to_others():
    b = add_user()
    owner, book = full_book_with_queue([b])
    free_the_slot(owner, book)
    assert library.free_slots(book) == 0


def test_return_with_no_queue_leaves_slot_free():
    owner, book = full_book_with_queue([])
    free_the_slot(owner, book)
    assert library.free_slots(book) == 1


def test_auto_return_offers_slot_to_queue():
    b = add_user()
    _, book = full_book_with_queue([b])
    skip(days=14)
    library.check_due_items()
    assert hold_of(b, book)["status"] == "READY"


def test_two_returns_make_two_offers():
    owner1, owner2 = add_user(), add_user()
    b, c, d = add_user(), add_user(), add_user()
    book = add_book(2)
    library.borrow(owner1, book)
    library.borrow(owner2, book)
    for user in (b, c, d):
        library.place_hold(user, book)
    skip(days=14)
    library.check_due_items()
    assert [hold_of(u, book)["status"] for u in (b, c, d)] == ["READY", "READY", "WAITING"]


#US-12: accept

def test_accept_creates_loan_from_hold():
    b = add_user()
    owner, book = full_book_with_queue([b])
    free_the_slot(owner, book)
    hold_id = hold_of(b, book)["hold_id"]
    library.accept_hold(b, hold_id)
    loan = loan_of(b, book)
    assert loan["status"] == "ACTIVE"
    assert loan["hold_id"] == hold_id
    assert hold_row(hold_id)["status"] == "ACCEPTED"


def test_accepted_loan_lasts_14_days():
    b = add_user()
    owner, book = full_book_with_queue([b])
    free_the_slot(owner, book)
    library.accept_hold(b, hold_of(b, book)["hold_id"])
    loan = loan_of(b, book)
    assert as_time(loan["due_at"]) - as_time(loan["borrowed_at"]) == timedelta(days=14)


def test_accept_keeps_next_person_waiting():
    b, c = add_user(), add_user()
    owner, book = full_book_with_queue([b, c])
    free_the_slot(owner, book)
    library.accept_hold(b, hold_of(b, book)["hold_id"])
    assert hold_of(c, book)["status"] == "WAITING"
    assert library.free_slots(book) == 0


def test_accept_twice_fails():
    b = add_user()
    owner, book = full_book_with_queue([b])
    free_the_slot(owner, book)
    hold_id = hold_of(b, book)["hold_id"]
    library.accept_hold(b, hold_id)
    with pytest.raises(LibraryError):
        library.accept_hold(b, hold_id)
    assert one("SELECT COUNT(*) AS n FROM loan WHERE user_id = %s", (b,))["n"] == 1


def test_accept_other_users_hold_fails():
    b, c = add_user(), add_user()
    owner, book = full_book_with_queue([b])
    free_the_slot(owner, book)
    with pytest.raises(LibraryError):
        library.accept_hold(c, hold_of(b, book)["hold_id"])
    assert hold_of(b, book)["status"] == "READY"


def test_accept_waiting_hold_fails():
    b = add_user()
    _, book = full_book_with_queue([b])
    with pytest.raises(LibraryError):
        library.accept_hold(b, hold_of(b, book)["hold_id"])


def test_accept_at_loan_limit_fails_and_offer_stays_open():
    b = add_user(max_loans=1)
    owner, book = full_book_with_queue([b])
    library.borrow(b, add_book(1, "Another Book"))
    free_the_slot(owner, book)
    with pytest.raises(LibraryError):
        library.accept_hold(b, hold_of(b, book)["hold_id"])
    assert hold_of(b, book)["status"] == "READY"


def test_accept_at_deadline_fails_and_passes_slot_on():
    b, c = add_user(), add_user()
    owner, book = full_book_with_queue([b, c])
    free_the_slot(owner, book)
    skip(hours=72)
    with pytest.raises(LibraryError):
        library.accept_hold(b, hold_of(b, book)["hold_id"])
    assert hold_of(b, book)["status"] == "EXPIRED"
    assert hold_of(c, book)["status"] == "READY"
    assert loan_of(b, book) is None


def test_accept_just_before_deadline_works():
    b = add_user()
    owner, book = full_book_with_queue([b])
    free_the_slot(owner, book)
    skip(hours=71)
    library.accept_hold(b, hold_of(b, book)["hold_id"])
    assert loan_of(b, book)["status"] == "ACTIVE"


#US-12: decline

def test_decline_passes_slot_to_next_person():
    b, c = add_user(), add_user()
    owner, book = full_book_with_queue([b, c])
    free_the_slot(owner, book)
    library.decline_hold(b, hold_of(b, book)["hold_id"])
    assert hold_of(b, book)["status"] == "DECLINED"
    assert hold_of(c, book)["status"] == "READY"


def test_decline_gives_next_person_a_new_72_hours():
    b, c = add_user(), add_user()
    owner, book = full_book_with_queue([b, c])
    free_the_slot(owner, book)
    skip(hours=10)
    library.decline_hold(b, hold_of(b, book)["hold_id"])
    hold = hold_of(c, book)
    assert as_time(hold["decision_deadline"]) - as_time(hold["ready_at"]) == timedelta(hours=72)
    assert as_time(hold["decision_deadline"]) > as_time(hold_of(b, book)["decision_deadline"])


def test_decline_with_empty_queue_frees_slot():
    b = add_user()
    owner, book = full_book_with_queue([b])
    free_the_slot(owner, book)
    library.decline_hold(b, hold_of(b, book)["hold_id"])
    assert library.free_slots(book) == 1


def test_decline_other_users_hold_fails():
    b, c = add_user(), add_user()
    owner, book = full_book_with_queue([b])
    free_the_slot(owner, book)
    with pytest.raises(LibraryError):
        library.decline_hold(c, hold_of(b, book)["hold_id"])
    assert hold_of(b, book)["status"] == "READY"


def test_decline_waiting_hold_fails():
    b = add_user()
    _, book = full_book_with_queue([b])
    with pytest.raises(LibraryError):
        library.decline_hold(b, hold_of(b, book)["hold_id"])


#US-12: the 72 hour window running out

def test_nothing_expires_before_deadline():
    b = add_user()
    owner, book = full_book_with_queue([b])
    free_the_slot(owner, book)
    skip(hours=71)
    library.check_due_items()
    assert hold_of(b, book)["status"] == "READY"


def test_hold_expires_at_deadline_and_passes_on():
    b, c = add_user(), add_user()
    owner, book = full_book_with_queue([b, c])
    free_the_slot(owner, book)
    skip(hours=72)
    library.check_due_items()
    assert hold_of(b, book)["status"] == "EXPIRED"
    assert hold_of(c, book)["status"] == "READY"


def test_expired_hold_with_empty_queue_frees_slot():
    b = add_user()
    owner, book = full_book_with_queue([b])
    free_the_slot(owner, book)
    skip(hours=72)
    library.check_due_items()
    assert library.free_slots(book) == 1


def test_accepted_hold_never_expires():
    b = add_user()
    owner, book = full_book_with_queue([b])
    free_the_slot(owner, book)
    hold_id = hold_of(b, book)["hold_id"]
    library.accept_hold(b, hold_id)
    skip(hours=73)
    library.check_due_items()
    assert hold_row(hold_id)["status"] == "ACCEPTED"


def test_queue_runs_through_in_order():
    b, c, d = add_user(), add_user(), add_user()
    owner, book = full_book_with_queue([b, c, d])
    free_the_slot(owner, book)
    library.decline_hold(b, hold_of(b, book)["hold_id"])  # b says no, c is next
    assert hold_of(c, book)["status"] == "READY"
    skip(hours=72)
    library.check_due_items()  # c runs out of time, d is next
    assert hold_of(c, book)["status"] == "EXPIRED"
    assert hold_of(d, book)["status"] == "READY"
    library.accept_hold(d, hold_of(d, book)["hold_id"])  # d takes it
    assert loan_of(d, book)["status"] == "ACTIVE"


def test_each_book_has_its_own_queue():
    b, c = add_user(), add_user()
    owner1, book1 = full_book_with_queue([b])
    _, book2 = full_book_with_queue([c])
    free_the_slot(owner1, book1)
    assert hold_of(b, book1)["status"] == "READY"
    assert hold_of(c, book2)["status"] == "WAITING"


#US-08: renew a loan

def renew_like_the_api(user_id, loan_id):
    #the /api/renew route returns expired loans first, then renews
    library.check_due_items()
    library.renew(user_id, loan_id)


def test_renew_adds_14_days():
    a = add_user()
    book = add_book(1)
    library.borrow(a, book)
    loan = loan_of(a, book)
    renew_like_the_api(a, loan["loan_id"])
    renewed = loan_of(a, book)
    assert as_time(renewed["due_at"]) - as_time(loan["due_at"]) == timedelta(days=14)
    assert renewed["renewal_count"] == 1


def test_renew_blocked_after_two_renewals():
    a = add_user()
    book = add_book(1)
    library.borrow(a, book)
    loan_id = loan_of(a, book)["loan_id"]
    renew_like_the_api(a, loan_id)
    renew_like_the_api(a, loan_id)
    with pytest.raises(LibraryError):
        renew_like_the_api(a, loan_id)
    assert loan_of(a, book)["renewal_count"] == 2


def test_renew_blocked_when_someone_is_waiting():
    b = add_user()
    owner, book = full_book_with_queue([b])
    loan = loan_of(owner, book)
    with pytest.raises(LibraryError):
        renew_like_the_api(owner, loan["loan_id"])
    assert loan_of(owner, book)["due_at"] == loan["due_at"]


def test_renew_blocked_when_another_user_has_ready_hold():
    #BR-12: a hold that's been offered (READY) also blocks renewing
    owner1, owner2 = add_user(), add_user()
    b = add_user()
    book = add_book(2)
    library.borrow(owner1, book)
    library.borrow(owner2, book)
    library.place_hold(b, book)
    free_the_slot(owner2, book)  # b now has a READY offer, owner1 still has a loan
    assert hold_of(b, book)["status"] == "READY"
    with pytest.raises(LibraryError):
        renew_like_the_api(owner1, loan_of(owner1, book)["loan_id"])


def test_renew_allowed_when_holds_are_finished():
    b = add_user()
    owner, book = full_book_with_queue([b])
    library.cancel_hold(b, hold_of(b, book)["hold_id"])
    renew_like_the_api(owner, loan_of(owner, book)["loan_id"])
    assert loan_of(owner, book)["renewal_count"] == 1


def test_renew_blocked_for_expired_loan():
    a = add_user()
    book = add_book(1)
    library.borrow(a, book)
    loan_id = loan_of(a, book)["loan_id"]
    skip(days=14)
    with pytest.raises(LibraryError):
        renew_like_the_api(a, loan_id)
    assert loan_of(a, book)["status"] == "RETURNED"


def test_renew_blocked_for_expired_loan_before_auto_return_runs():
    #BR-11 is checked inside renew() too, not only by the automatic return
    a = add_user()
    book = add_book(1)
    library.borrow(a, book)
    skip(days=14)
    with pytest.raises(LibraryError):
        library.renew(a, loan_of(a, book)["loan_id"])
    assert loan_of(a, book)["renewal_count"] == 0


def test_renew_blocked_for_returned_loan():
    a = add_user()
    book = add_book(1)
    library.borrow(a, book)
    loan_id = loan_of(a, book)["loan_id"]
    library.return_book(a, loan_id)
    with pytest.raises(LibraryError):
        renew_like_the_api(a, loan_id)


def test_renew_other_users_loan_fails():
    a, b = add_user(), add_user()
    book = add_book(1)
    library.borrow(a, book)
    with pytest.raises(LibraryError):
        renew_like_the_api(b, loan_of(a, book)["loan_id"])
    assert loan_of(a, book)["renewal_count"] == 0


def test_renew_missing_loan_fails():
    with pytest.raises(LibraryError):
        renew_like_the_api(add_user(), 99999)


def test_my_loans_shows_renewal_count():
    a = add_user()
    book = add_book(1)
    library.borrow(a, book)
    renew_like_the_api(a, loan_of(a, book)["loan_id"])
    assert library.my_loans(a)[0]["renewal_count"] == 1


#NFR-05: shortened hold window for demos

def test_demo_hold_minutes_shortens_the_window(monkeypatch):
    monkeypatch.setenv("UDBS_DEMO_HOLD_MINUTES", "5")
    b = add_user()
    owner, book = full_book_with_queue([b])
    free_the_slot(owner, book)
    hold = hold_of(b, book)
    assert as_time(hold["decision_deadline"]) - as_time(hold["ready_at"]) == timedelta(minutes=5)


def test_short_demo_hold_window_expires(monkeypatch):
    monkeypatch.setenv("UDBS_DEMO_HOLD_MINUTES", "5")
    b, c = add_user(), add_user()
    owner, book = full_book_with_queue([b, c])
    free_the_slot(owner, book)
    skip(minutes=5)
    library.check_due_items()
    assert hold_of(b, book)["status"] == "EXPIRED"
    assert hold_of(c, book)["status"] == "READY"


@pytest.mark.parametrize("value", ["0", "-5", "abc", "525601"])
def test_bad_demo_hold_minutes_are_refused(monkeypatch, value):
    b = add_user()
    owner, book = full_book_with_queue([b])
    monkeypatch.setenv("UDBS_DEMO_HOLD_MINUTES", value)
    with pytest.raises(LibraryError):
        free_the_slot(owner, book)
