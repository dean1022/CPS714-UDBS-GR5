#run pytest test_loans.py -v
from datetime import datetime, timedelta

import pytest
import database

from auth import TIME_FORMAT
from database import get_connection, init_db
from seed_users import seed
from loans import init_loan_tables, return_loan, process_expired_loans, available_slots, LoanError

#creates a temp database for every test so library.db isn't changed
@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    init_db()
    init_loan_tables()
    seed()

#helper function to add a literature item with a given number of access slots
def add_literature(total_slots=15, file_url="sample.txt"):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO literature (title, file_url, total_access_slots) VALUES (?, ?, ?)",
        ("Test Book", file_url, total_slots),
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

#helper function to add a hold that has been offered a slot 
def add_ready_hold(university_id, literature_id):
    conn = get_connection()
    conn.execute(
        "INSERT INTO hold (university_id, literature_id, status) VALUES (?, ?, 'READY')",
        (university_id, literature_id),
    )
    conn.commit()
    conn.close()

#helper function to read one loan row back from the database
def get_loan(loan_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT status, return_type, returned_at FROM loan WHERE loan_id = ?",
        (loan_id,),
    ).fetchone()
    conn.close()
    return row

#tests that an early return marks the loan as returned
def test_early_return():
    university_id = "501000001"
    lit_id = add_literature()
    loan_id = add_loan(university_id, lit_id)

    result = return_loan(university_id, loan_id)

    assert result["message"] == "Loan returned."
    assert get_loan(loan_id)["status"] == "RETURNED"

#tests that an early return is recorded as EARLY with a return time
def test_early_return_records_type_and_time():
    university_id = "501000001"
    lit_id = add_literature()
    loan_id = add_loan(university_id, lit_id)

    return_loan(university_id, loan_id)

    loan = get_loan(loan_id)

    assert loan["return_type"] == "EARLY"
    assert loan["returned_at"] is not None

#tests that returning a loan frees up an access slot
def test_early_return_frees_slot():
    university_id = "501000001"
    lit_id = add_literature()
    loan_id = add_loan(university_id, lit_id)

    assert available_slots(lit_id) == 14

    result = return_loan(university_id, loan_id)

    assert result["available_slots"] == 15
    assert available_slots(lit_id) == 15

#tests that returning one loan does not affect the user's other loans
def test_early_return_only_affects_that_loan():
    university_id = "501000001"
    lit_id = add_literature()
    loan1 = add_loan(university_id, lit_id)
    loan2 = add_loan(university_id, lit_id)

    return_loan(university_id, loan1)

    assert get_loan(loan1)["status"] == "RETURNED"
    assert get_loan(loan2)["status"] == "ACTIVE"
    assert available_slots(lit_id) == 14

#tests that a loan cannot be returned twice
def test_return_twice_fails():
    university_id = "501000001"
    lit_id = add_literature()
    loan_id = add_loan(university_id, lit_id)

    return_loan(university_id, loan_id)

    with pytest.raises(LoanError):
        return_loan(university_id, loan_id)

#tests that a second return attempt does not free a second slot
def test_return_twice_does_not_free_extra_slot():
    university_id = "501000001"
    lit_id = add_literature()
    loan_id = add_loan(university_id, lit_id)

    return_loan(university_id, loan_id)

    with pytest.raises(LoanError):
        return_loan(university_id, loan_id)

    assert available_slots(lit_id) == 15

#tests that a user cannot return someone else's loan
def test_return_other_users_loan_fails():
    university_id = "501000001"
    other_uid = "501000002"
    lit_id = add_literature()
    loan_id = add_loan(university_id, lit_id)

    with pytest.raises(LoanError):
        return_loan(other_uid, loan_id)

#tests that a failed return by another user leaves the loan active
def test_return_other_users_loan_leaves_loan_active():
    university_id = "501000001"
    other_uid = "501000002"
    lit_id = add_literature()
    loan_id = add_loan(university_id, lit_id)

    with pytest.raises(LoanError):
        return_loan(other_uid, loan_id)

    assert get_loan(loan_id)["status"] == "ACTIVE"
    assert available_slots(lit_id) == 14

#tests that an expired loan can't be returned early
def test_return_expired_loan_fails():
    university_id = "501000001"
    lit_id = add_literature()
    loan_id = add_loan(university_id, lit_id, due_in=timedelta(minutes=-5))

    with pytest.raises(LoanError):
        return_loan(university_id, loan_id)

#tests invalid or missing loan IDs
@pytest.mark.parametrize("loan_id", [None, "", 99999])
def test_return_invalid_loan_id(loan_id):
    university_id = "501000001"

    with pytest.raises(LoanError):
        return_loan(university_id, loan_id)

#tests that a slot reserved for a pending hold isn't counted as available
def test_reserved_slot_not_available():
    university_id = "501000001"
    other_uid = "501000002"
    lit_id = add_literature()
    add_loan(university_id, lit_id)
    add_ready_hold(other_uid, lit_id)

    #15 total - 1 active loan - 1 reserved for the hold
    assert available_slots(lit_id) == 13

#tests that an expired loan is automatically returned
def test_auto_return_expired_loan():
    university_id = "501000001"
    lit_id = add_literature()
    loan_id = add_loan(university_id, lit_id, due_in=timedelta(minutes=-5))

    returned = process_expired_loans()

    assert len(returned) == 1
    assert returned[0]["loan_id"] == loan_id
    assert get_loan(loan_id)["status"] == "RETURNED"

#tests that an automatic return is recorded as AUTO with a return time
def test_auto_return_records_type_and_time():
    university_id = "501000001"
    lit_id = add_literature()
    loan_id = add_loan(university_id, lit_id, due_in=timedelta(minutes=-5))

    process_expired_loans()

    loan = get_loan(loan_id)

    assert loan["return_type"] == "AUTO"
    assert loan["returned_at"] is not None

#tests that an automatic return frees up an access slot
def test_auto_return_frees_slot():
    university_id = "501000001"
    lit_id = add_literature()
    add_loan(university_id, lit_id, due_in=timedelta(minutes=-5))

    assert available_slots(lit_id) == 14

    process_expired_loans()

    assert available_slots(lit_id) == 15

#tests that loans that haven't expired yet are left alone
def test_auto_return_ignores_active_loan():
    university_id = "501000001"
    lit_id = add_literature()
    loan_id = add_loan(university_id, lit_id)

    returned = process_expired_loans()

    assert returned == []
    assert get_loan(loan_id)["status"] == "ACTIVE"
    assert available_slots(lit_id) == 14

#tests that only the expired loans are returned when there's a mix
def test_auto_return_only_expired_loans():
    university_id = "501000001"
    other_uid = "501000002"
    lit_id = add_literature()
    expired = add_loan(university_id, lit_id, due_in=timedelta(minutes=-5))
    still_active = add_loan(university_id, lit_id)
    other_users_active = add_loan(other_uid, lit_id)

    process_expired_loans()

    assert get_loan(expired)["status"] == "RETURNED"
    assert get_loan(still_active)["status"] == "ACTIVE"
    assert get_loan(other_users_active)["status"] == "ACTIVE"
    assert available_slots(lit_id) == 13

#tests that a loan is returned once its due time passes, using a custom time
def test_auto_return_at_due_time():
    university_id = "501000001"
    lit_id = add_literature()
    loan_id = add_loan(university_id, lit_id)

    process_expired_loans(now=datetime.now() + timedelta(days=13))
    assert get_loan(loan_id)["status"] == "ACTIVE"

    process_expired_loans(now=datetime.now() + timedelta(days=15))
    assert get_loan(loan_id)["status"] == "RETURNED"

#tests that running the check twice doesn't return a loan twice
def test_auto_return_twice_does_nothing():
    university_id = "501000001"
    lit_id = add_literature()
    add_loan(university_id, lit_id, due_in=timedelta(minutes=-5))

    first = process_expired_loans()
    second = process_expired_loans()

    assert len(first) == 1
    assert second == []
    assert available_slots(lit_id) == 15

#tests that a loan already returned early isn't returned again by the auto check
def test_auto_return_skips_early_returned_loan():
    university_id = "501000001"
    lit_id = add_literature()
    loan_id = add_loan(university_id, lit_id)

    return_loan(university_id, loan_id)

    returned = process_expired_loans(now=datetime.now() + timedelta(days=15))

    assert returned == []
    assert get_loan(loan_id)["return_type"] == "EARLY"

#tests that an early return fails once the loan has been automatically returned
def test_early_return_after_auto_return_fails():
    university_id = "501000001"
    lit_id = add_literature()
    loan_id = add_loan(university_id, lit_id, due_in=timedelta(minutes=-5))

    process_expired_loans()

    with pytest.raises(LoanError):
        return_loan(university_id, loan_id)

#tests that nothing happens when there are no loans at all
def test_auto_return_with_no_loans():
    assert process_expired_loans() == []