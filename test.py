#login page -> account page -> logout -> login page
#run this file to test the login python test.py

from getpass import getpass
from auth import AuthError, get_current_user, login, logout
from database import get_connection, init_db

def ensure_demo_users():
    init_db()
    conn = get_connection()
    n = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    if n == 0:
        from seed_users import seed
        seed()
        print()

def ask_password():
    try:
        return getpass("Password: ")
    except Exception:
        return input("Password: ")

def login_page():
    #returns a session token, or None if the user quits
    while True:
        print("   -_-_-_- University Digital Borrowing System -_-_-_-")
        print("               LOG IN")
        print("(type 'q' as the ID to quit)\n")
        identifier = input("University ID or email: ").strip()
        if identifier.lower() == "q":
            return None
        password = ask_password()
        try:
            return login(identifier, password)
        except AuthError as e:
            print(f"\n[!] {e}\n")

def account_page(token):
    #Shows the account info. Returns when the user logs out
    user = get_current_user(token)
    if user is None:
        print("\nYour session has expired. Please log in again.\n")
        return
    print(f"   Welcome, {user['display_name']}!")
    print(f"  University ID : {user['university_id']}")
    print(f"  Name          : {user['first_name']} {user['last_name']}")
    print(f"  Email         : {user['email']}")
    print(f"  Pronouns      : {user['pronouns']}")
    print(f"  Status        : {user['status'].capitalize()}")

    while True:
        choice = input("\nType 'logout' to log out: ").strip().lower()
        if choice in ("logout", "l", "log out"):
            logout(token)
            print("\nYou have been logged out.\n")
            return
        print("Unknown command.")

def main():
    ensure_demo_users()
    print("Demo password for all accounts: Library2026!")
    print("Try 501000001 (student) or 700000001 (faculty)\n")
    while True:
        token = login_page()
        if token is None:
            print("Exit")
            break
        account_page(token)

if __name__ == "__main__":
    main()