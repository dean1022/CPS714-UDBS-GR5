from database import connect, setup_database

BASE_QUERY = """
    SELECT literature.title, author.first_name, author.last_name, literature.published_year,
           literature.summary, literature.total_slots, literature.available_slots
    FROM literature
    JOIN author ON literature.author_id = author.author_id
"""


def get_order_by(sort_by):
    if sort_by == "author":
        return " ORDER BY author.last_name, author.first_name, literature.title"
    return " ORDER BY literature.title"


def get_all_books(sort_by):
    connection = connect()
    cursor = connection.cursor()
    cursor.execute(BASE_QUERY + get_order_by(sort_by))
    books = cursor.fetchall()
    connection.close()
    return books


def search_books(search_text, sort_by):
    connection = connect()
    cursor = connection.cursor()
    pattern = "%" + search_text + "%"
    cursor.execute(BASE_QUERY + """
        WHERE literature.title LIKE ?
           OR author.first_name LIKE ?
           OR author.last_name LIKE ?
           OR literature.category LIKE ?
           OR literature.keywords LIKE ?
    """ + get_order_by(sort_by), (pattern, pattern, pattern, pattern, pattern))
    books = cursor.fetchall()
    connection.close()
    return books


def get_action(available_slots):
    # the interface shows Borrow if a slot is free, otherwise Hold
    if available_slots > 0:
        return "Borrow"
    return "Hold"


def display_books(books):
    if len(books) == 0:
        print("\nNo books found.")
        return
    print("\nFound " + str(len(books)) + " book(s):")
    for book in books:
        title, first_name, last_name, year, summary, total, available = book
        print("-" * 60)
        print("Title:        " + title)
        print("Author:       " + first_name + " " + last_name)
        print("Published:    " + str(year))
        print("Summary:      " + summary)
        print("Availability: " + str(available) + " of " + str(total) + " available  [" + get_action(available) + "]")
    print("-" * 60)


def ask_sort():
    choice = input("Sort by 1) Title or 2) Author: ")
    if choice == "2":
        return "author"
    return "title"


def main():
    setup_database()
    running = True
    while running:
        print("\n===== University E-Library Catalogue =====")
        print("1. View all books")
        print("2. Search books")
        print("3. Exit")
        choice = input("Choose an option (1-3): ")

        if choice == "1":
            display_books(get_all_books(ask_sort()))
        elif choice == "2":
            search_text = input("Search by title, author, category or keyword: ")
            if search_text.strip() == "":
                print("Please type something to search for.")
            else:
                display_books(search_books(search_text, ask_sort()))
        elif choice == "3":
            print("Goodbye!")
            running = False
        else:
            print("Please enter 1, 2 or 3.")


main()
