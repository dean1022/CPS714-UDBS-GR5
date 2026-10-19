import hashlib
import secrets
from datetime import datetime, timedelta
from database import get_connection

SESSION_HOURS = 8  # how long a login lasts
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"  # how we save times in the database

#for authentication errors
class AuthError(Exception):
    pass

#passwords
def make_hash(password, salt):
    # add the salt to the password before hashing
    # makes pwd harder to guess
    return hashlib.sha256((salt + password).encode()).hexdigest()

def hash_password(password):
    # generate random salt for each pwd
    # user with same pwd will have different hashes
    salt = secrets.token_hex(8)
    return salt + "$" + make_hash(password, salt)

def verify_password(password, stored_hash):

    # stored_hash looks like "salt$hash"
    if "$" not in stored_hash:
        return False
    #separate salt from pwd hash
    salt, real_hash = stored_hash.split("$", 1)

    # hash the entered pwd using the same salt 
    # if result matches stored hash, the pwd is correct
    return secrets.compare_digest(make_hash(password, salt), real_hash)

#login
def login(identifier, password):
    # checks the login and returns a session token
    identifier = (identifier or "").strip()
    # make sure both use and pwd are entered
    if identifier == "" or not password:
        raise AuthError("Please enter your university ID or email and your password.")

    conn = get_connection()
    # find user by uni ID or email
    user = conn.execute(
        "SELECT university_id, password_hash FROM users WHERE university_id = ? OR email = ?",
        (identifier, identifier),
    ).fetchone()

    # same message for both problems so nobody can tell which IDs exist
    if user is None or not verify_password(password, user["password_hash"]):
        conn.close()
        raise AuthError("Invalid university ID/email or password.")

    # Link the university identity to the existing lending schema.
    identity = conn.execute("SELECT * FROM users WHERE university_id=?", (user["university_id"],)).fetchone()
    conn.execute("""INSERT INTO library_user (university_id, first_name, last_name, email, created_at, max_loans, max_holds)
        VALUES (?, ?, ?, ?, ?, 30, 15) ON CONFLICT(university_id) DO UPDATE SET
        first_name=excluded.first_name, last_name=excluded.last_name, email=excluded.email""",
        (identity["university_id"], identity["first_name"], identity["last_name"], identity["email"], datetime.now().strftime(TIME_FORMAT)))
    # create session that lasts 8 hrs
    now = datetime.now()
    expires = now + timedelta(hours=SESSION_HOURS)
    # generate random token to identify login session
    token = secrets.token_urlsafe(32)

    conn.execute(
        "INSERT INTO sessions (token, university_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, user["university_id"], now.strftime(TIME_FORMAT), expires.strftime(TIME_FORMAT)),
    )
    conn.commit()
    conn.close()
    # give token to app so it knows user logged in
    return token

#check who is logged in 
def get_current_user(token):
    #returns the user info or None if not logged in
    if not token:
        return None

    conn = get_connection()
    # find session and get the user's info
    row = conn.execute(
        """SELECT u.university_id, u.email, u.first_name, u.last_name,
                  u.display_name, u.pronouns, u.status, p.user_id, p.phone, p.address, p.max_loans, p.max_holds, s.expires_at
           FROM sessions s JOIN users u ON u.university_id = s.university_id
           JOIN library_user p ON p.university_id = u.university_id
           WHERE s.token = ?""",
        (token,),
    ).fetchone()

    # token doesn't match existing session
    if row is None:
        conn.close()
        return None

    # session ran out so delete it
    if row["expires_at"] <= datetime.now().strftime(TIME_FORMAT):
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return None

    conn.close()

    #convert db row into dictionary
    user = dict(row)

    #expiration time is only used for checking session
    del user["expires_at"]
    return user

#logout
def logout(token):
    #delete session so user isn't logged in anymore
    if token:
        conn = get_connection()
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()