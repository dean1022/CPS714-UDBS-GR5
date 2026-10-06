#run pytest autotest.py -v
from datetime import datetime, timedelta

import pytest
import database

from auth import (
    login,
    logout,
    get_current_user,
    AuthError,
    TIME_FORMAT,
)
from database import get_connection, init_db
from seed_users import seed, DEMO_PASSWORD

#creates a temp database for every test so library.db isn't changed
@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    init_db()
    seed()

#helper function to count active sessions
def count_sessions():
    conn = get_connection()
    n = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    conn.close()
    return n

#tests successful login using a uni ID
def test_login_with_university_id():
    token = login("501000001", DEMO_PASSWORD)

    assert token is not None

    user = get_current_user(token)

    assert user is not None
    assert user["university_id"] == "501000001"

#tests that an incorrect password stops login
def test_login_wrong_password():
    with pytest.raises(AuthError):
        login("501000001", "WrongPassword123")

#tests that failed logins don't create sessions
def test_login_wrong_password_creates_no_session():
    with pytest.raises(AuthError):
        login("501000001", "WrongPassword123")

    assert count_sessions() == 0

#tests login with a user that doesn't exist
def test_login_unknown_user():
    with pytest.raises(AuthError):
        login("999999999", DEMO_PASSWORD)

#tests invalid or missing user/pwd
@pytest.mark.parametrize("identifier, password", [
    ("", DEMO_PASSWORD),
    ("   ", DEMO_PASSWORD),
    (None, DEMO_PASSWORD),
    ("501000001", ""),
    ("501000001", None),
])
def test_login_empty_inputs(identifier, password):
    with pytest.raises(AuthError):
        login(identifier, password)

#tests successful login using an email address
def test_login_with_email():
    token = login("ava.chen@torontomu.ca", DEMO_PASSWORD)

    assert token is not None

    user = get_current_user(token)

    assert user is not None
    assert user["email"] == "ava.chen@torontomu.ca"

#tests that email login fails with an incorrect pwd
def test_login_with_email_wrong_password():
    with pytest.raises(AuthError):
        login("ava.chen@torontomu.ca", "WrongPassword123")

#tests that logout removes the user's session
def test_logout():
    token = login("501000001", DEMO_PASSWORD)

    assert get_current_user(token) is not None

    logout(token)

    assert get_current_user(token) is None

#tests that logging out one session does not affect other sessions
def test_logout_only_affects_that_session():
    token1 = login("501000001", DEMO_PASSWORD)
    token2 = login("501000001", DEMO_PASSWORD)

    logout(token1)

    assert get_current_user(token1) is None
    assert get_current_user(token2) is not None

#tests that logout handles invalid tokens safely
@pytest.mark.parametrize("token", [None, "", "fake-token"])
def test_logout_with_bad_token_does_not_crash(token):
    logout(token)

#tests that expired sessions are treated as invalid
def test_expired_session():
    token = login("501000001", DEMO_PASSWORD)

    conn = get_connection()

    expired_time = (
        datetime.now() - timedelta(hours=1)
    ).strftime(TIME_FORMAT)

    conn.execute(
        "UPDATE sessions SET expires_at = ? WHERE token = ?",
        (expired_time, token),
    )

    conn.commit()
    conn.close()

    assert get_current_user(token) is None


#tests that expired sessions are automatically removed from the database
def test_expired_session_is_deleted():
    token = login("501000001", DEMO_PASSWORD)

    conn = get_connection()

    expired_time = (
        datetime.now() - timedelta(hours=1)
    ).strftime(TIME_FORMAT)

    conn.execute(
        "UPDATE sessions SET expires_at = ? WHERE token = ?",
        (expired_time, token),
    )

    conn.commit()
    conn.close()

    get_current_user(token)

    assert count_sessions() == 0