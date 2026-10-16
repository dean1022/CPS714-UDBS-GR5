#run pytest test_reader.py -v
from datetime import datetime, timedelta

import pytest
import database

from auth import TIME_FORMAT
from database import get_connection, init_db
from seed_users import seed
from loans import init_loan_tables, return_loan, process_expired_loans, LoanError
from reader import open_literature

#creates a temp database for every test so library.db isn't changed
@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    init_db()
    init_loan_tables()
    seed()

#helper function to add a literature item
def add_literature(file_url="sample.txt"):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO literature (title, file_url, total_access_slots) VALUES (?, ?, 15)",
        ("Test Book", file_url),
    )
    conn.commit()
    lit_id = cur.lastrowid
    conn.close()
    return lit_id

#helper function to add a loan that expires due_in from now
def add_loan(university_id, literature_id, due_in=timedelta(days=14)):
    conn = get_connection()
    now = datetime.now()
    cur = conn.execute(
        "INSERT INTO loan (university_id, literature_id, borrowed_at, due_at, status) "
        "VALUES (?, ?, ?, ?, 'ACTIVE')",
        (
            university_id,
            literature_id,
            now.strftime(TIME_FORMAT),
            (now + due_in).strftime(TIME_FORMAT),
        ),
    )
    conn.commit()
    loan_id = cur.lastrowid
    conn.close()
    return loan_id

#tests that a user with an active loan can open the literature
def test_open_literature_with_active_loan():
    university_id = "501000001"
    lit_id = add_literature()
    add_loan(university_id, lit_id)

    result = open_literature(university_id, lit_id)

    assert result["title"] == "Test Book"
    assert result["file_url"] == "sample.txt"

#tests that a user with no loan can't open the literature
def test_open_literature_without_loan_fails():
    university_id = "501000001"
    lit_id = add_literature()

    with pytest.raises(LoanError):
        open_literature(university_id, lit_id)

#tests that a loan for a different title doesn't give access to this one
def test_open_literature_needs_loan_for_that_title():
    university_id = "501000001"
    borrowed = add_literature()
    other = add_literature()
    add_loan(university_id, borrowed)

    with pytest.raises(LoanError):
        open_literature(university_id, other)

#tests that another user's loan doesn't give you access
def test_open_literature_other_users_loan_fails():
    university_id = "501000001"
    other_uid = "501000002"
    lit_id = add_literature()
    add_loan(university_id, lit_id)

    with pytest.raises(LoanError):
        open_literature(other_uid, lit_id)

#tests that access ends after an early return
def test_open_literature_after_early_return_fails():
    university_id = "501000001"
    lit_id = add_literature()
    loan_id = add_loan(university_id, lit_id)

    assert open_literature(university_id, lit_id) is not None

    return_loan(university_id, loan_id)

    with pytest.raises(LoanError):
        open_literature(university_id, lit_id)

#tests that access ends after an automatic return
def test_open_literature_after_auto_return_fails():
    university_id = "501000001"
    lit_id = add_literature()
    add_loan(university_id, lit_id, due_in=timedelta(minutes=-5))

    process_expired_loans()

    with pytest.raises(LoanError):
        open_literature(university_id, lit_id)

#tests that an expired loan is blocked even if the automatic return hasn't run yet
def test_open_literature_expired_loan_not_yet_returned_fails():
    university_id = "501000001"
    lit_id = add_literature()
    add_loan(university_id, lit_id, due_in=timedelta(minutes=-5))

    with pytest.raises(LoanError):
        open_literature(university_id, lit_id)

#tests that a loan that is about to expire still works
def test_open_literature_just_before_expiry():
    university_id = "501000001"
    lit_id = add_literature()
    add_loan(university_id, lit_id, due_in=timedelta(minutes=1))

    assert open_literature(university_id, lit_id) is not None

#tests that access is blocked once the due time passes, using a custom time
def test_open_literature_stops_at_due_time():
    university_id = "501000001"
    lit_id = add_literature()
    add_loan(university_id, lit_id)

    assert open_literature(university_id, lit_id, now=datetime.now() + timedelta(days=13)) is not None

    with pytest.raises(LoanError):
        open_literature(university_id, lit_id, now=datetime.now() + timedelta(days=15))

#tests invalid or missing literature IDs
@pytest.mark.parametrize("lit_id", [None, "", 99999])
def test_open_literature_invalid_id(lit_id):
    with pytest.raises(LoanError):
        open_literature("501000001", lit_id)
