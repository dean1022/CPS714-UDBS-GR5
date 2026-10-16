#login page -> catalogue -> book page -> my loans -> logout
#run this file to try borrowing python library_app.py

import os
import time
from getpass import getpass

from database import get_connection, init_db
from auth import AuthError, login, logout, get_current_user
from catalogue import init_catalogue_tables, seed_literature, get_all_books, search_books, get_book
from loans import init_loan_tables, process_expired_loans, LoanError
from borrow import borrow_literature
from loan_time import get_active_loans, remaining_time

def setup():
    #make all the tables, catalogue has to go before the loan tables
    init_db()
    init_catalogue_tables()
    init_loan_tables()

    #add demo users if there aren't any
    conn = get_connection()
    n = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    if n == 0:
        from seed_users import seed
        seed()

    seed_literature()

def ask_password():
    try:
        return getpass("Password: ")
    except Exception:
        return input("Password: ")

def login_page():
    #returns a session token, or None if the user quits
    while True:
        print("\n   -_-_-_- University Digital Borrowing System -_-_-_-")
        print("               LOG IN")
        print("(type 'q' as the ID to quit)\n")
        identifier = input("University ID or email: ").strip()
        if identifier.lower() == "q":
            return None
        password = ask_password()
        try:
            return login(identifier, password)
        except AuthError as e:
            print(f"\n[!] {e}")

def get_action(available):
    #borrow if there's a free slot, otherwise hold
    if available > 0:
        return "Borrow"
    return "Hold"

def ask_sort():
    if input("Sort by 1) Title or 2) Author: ").strip() == "2":
        return "author"
    return "title"

def show_books(books):
    if len(books) == 0:
        print("\nNo books found.")
        return
    print()
    for book in books:
        print(f"[{book['literature_id']}] {book['title']} - {book['first_name']} {book['last_name']}  "
              f"({book['available_slots']} of {book['total_access_slots']} available)")

def book_page(user, literature_id):
    #shows one book's info and lets the user borrow it
    book = get_book(literature_id)
    if book is None:
        print("\nNo book with that ID.")
        return

    action = get_action(book["available_slots"])
    print("\n" + "-" * 60)
    print(f"Title        : {book['title']}")
    print(f"Author       : {book['first_name']} {book['last_name']}")
    print(f"Published    : {book['published_year']}")
    print(f"Summary      : {book['summary']}")
    print(f"Availability : {book['available_slots']} of {book['total_access_slots']} available  [{action}]")
    print("-" * 60)

    #holds aren't done yet (sprint 3)
    if action == "Hold":
        print("No access slots free right now. Holds are coming in sprint 3.")
        input("Press Enter to go back.")
        return

    choice = input("Type 'b' to borrow or press Enter to go back: ").strip().lower()
    if choice == "b":
        try:
            result = borrow_literature(user["university_id"], literature_id)
            print(f"\n{result['message']}")
            print(f"Due: {result['due_at']}  ({remaining_time(result['due_at'])} left)")
        except LoanError as e:
            print(f"\n[!] {e}")

def pick_book(user, books):
    show_books(books)
    if len(books) == 0:
        return
    choice = input("\nEnter a book ID to open it or press Enter to go back: ").strip()
    if choice.isdigit():
        book_page(user, int(choice))

def my_loans_page(user):
    #shows time left on each loan and updates every sec
    #ctrl+c goes back to the menu
    try:
        while True:
            #return any loans that just ran out
            process_expired_loans()
            loans = get_active_loans(user["university_id"])

            #clear the screen so it looks like it's updating live
            os.system("cls" if os.name == "nt" else "clear")
            print(f"   {user['display_name']}'s loans   (press Ctrl+C to go back)\n")

            if len(loans) == 0:
                print("You have no active loans.")
            for loan in loans:
                print(loan["title"])
                print(f"   Borrowed : {loan['borrowed_at']}   Due : {loan['due_at']}")
                print(f"   Time left: {remaining_time(loan['due_at'])}\n")
            time.sleep(1)
    except KeyboardInterrupt:
        print()

def catalogue_page(token):
    #main menu, returns when the user logs out
    while True:
        user = get_current_user(token)
        if user is None:
            print("\nYour session has expired. Please log in again.")
            return
        process_expired_loans()

        print(f"\n===== University E-Library Catalogue =====   (logged in as {user['display_name']})")
        print("1. View all books")
        print("2. Search books")
        print("3. My loans")
        print("4. Log out")
        choice = input("Choose an option (1-4): ").strip()

        if choice == "1":
            pick_book(user, get_all_books(ask_sort()))
        elif choice == "2":
            text = input("Search by title, author, category, keyword or summary: ").strip()
            if text == "":
                print("Please type something to search for.")
            else:
                pick_book(user, search_books(text, ask_sort()))
        elif choice == "3":
            my_loans_page(user)
        elif choice == "4":
            logout(token)
            print("\nYou have been logged out.")
            return
        else:
            print("Please enter 1, 2, 3 or 4.")

def main():
    setup()
    print("Demo password for all accounts: Library2026!")
    print("Try 501000001 (student) or 700000001 (faculty)")
    while True:
        token = login_page()
        if token is None:
            print("Exit")
            break
        catalogue_page(token)

if __name__ == "__main__":
    main()
