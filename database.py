import sqlite3

DATABASE_FILE = "library.db"


def connect():
    return sqlite3.connect(DATABASE_FILE)


def create_tables(connection):
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS university_user (
            user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            student_number TEXT NOT NULL UNIQUE,
            first_name     TEXT NOT NULL,
            last_name      TEXT NOT NULL,
            email          TEXT NOT NULL UNIQUE,
            role           TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS author (
            author_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name  TEXT NOT NULL
        )
    """)

    # total_slots = how many users can borrow it at once
    # available_slots = how many are free right now (decides Borrow or Hold)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS literature (
            literature_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT NOT NULL,
            author_id       INTEGER NOT NULL,
            published_year  INTEGER,
            category        TEXT,
            keywords        TEXT,
            summary         TEXT,
            total_slots     INTEGER NOT NULL,
            available_slots INTEGER NOT NULL,
            FOREIGN KEY (author_id) REFERENCES author(author_id)
        )
    """)

    connection.commit()


def add_author(connection, first_name, last_name):
    # reuse the author if they already exist
    cursor = connection.cursor()
    cursor.execute("SELECT author_id FROM author WHERE first_name = ? AND last_name = ?",
                   (first_name, last_name))
    row = cursor.fetchone()
    if row is not None:
        return row[0]
    cursor.execute("INSERT INTO author (first_name, last_name) VALUES (?, ?)", (first_name, last_name))
    return cursor.lastrowid


def add_sample_users(connection):
    users = [
        ("S1001", "Alice", "Nguyen", "alice.nguyen@uni.edu", "Student"),
        ("S1002", "Bob", "Martin", "bob.martin@uni.edu", "Student"),
        ("S1003", "Cara", "Diaz", "cara.diaz@uni.edu", "Student"),
        ("F2001", "David", "Okafor", "david.okafor@uni.edu", "Faculty"),
    ]
    for user in users:
        connection.execute("INSERT INTO university_user (student_number, first_name, last_name, email, role) "
                           "VALUES (?, ?, ?, ?, ?)", user)
    connection.commit()


def add_sample_books(connection):
    # title, author first, author last, year, category, keywords, summary, total slots, available slots
    books = [
        ("Database System Concepts", "Abraham", "Silberschatz", 2019, "Computer Science", "databases, sql, erd",
         "A textbook on how databases are designed, queried with SQL, and kept reliable.", 1, 0),
        ("Introduction to Algorithms", "Thomas", "Cormen", 2022, "Computer Science", "algorithms, sorting",
         "Covers common algorithms and how to measure how fast they run.", 2, 2),
        ("Clean Code", "Robert", "Martin", 2008, "Software Engineering", "programming, good habits",
         "Advice on writing code that is easy for other people to read and change.", 3, 1),
        ("A Brief History of Time", "Stephen", "Hawking", 1988, "Physics", "space, black holes, universe",
         "Explains big ideas about the universe, like black holes and the Big Bang, for regular readers.", 1, 1),
        ("Sapiens", "Yuval", "Harari", 2011, "History", "humans, evolution, society",
         "Tells the story of how humans went from small groups to a global society.", 2, 0),
        ("The Selfish Gene", "Richard", "Dawkins", 1976, "Biology", "genes, evolution",
         "Looks at evolution from the point of view of genes instead of whole animals.", 1, 1),
        ("Thinking, Fast and Slow", "Daniel", "Kahneman", 2011, "Psychology", "decisions, mind, bias",
         "Describes two ways people think and how they lead to good and bad decisions.", 2, 1),
        ("The River Between", "Ngugi", "wa Thiong'o", 1965, "Literature", "novel, africa, tradition",
         "A novel about two villages and a young man caught between old and new ways.", 1, 0),
    ]
    for book in books:
        title, first, last, year, category, keywords, summary, total, available = book
        author_id = add_author(connection, first, last)
        connection.execute("INSERT INTO literature (title, author_id, published_year, category, keywords, "
                           "summary, total_slots, available_slots) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (title, author_id, year, category, keywords, summary, total, available))
    connection.commit()


def setup_database():
    connection = connect()
    create_tables(connection)
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM literature")
    if cursor.fetchone()[0] == 0:  # only add sample data the first time
        add_sample_users(connection)
        add_sample_books(connection)
        print("Database created with sample data.")
    connection.close()
