#Literature catalogue (US-02, US-04) for the University Digital Borrowing System

from database import get_connection
from loans import available_slots

def init_catalogue_tables():
    #creates the author and literature tables
    #has to run before init_loan_tables() so literature gets all the catalogue columns
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS author (
                author_id  INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS literature (
                literature_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                title              TEXT NOT NULL,
                author_id          INTEGER REFERENCES author(author_id),
                published_year     INTEGER,
                category           TEXT,
                keywords           TEXT,
                summary            TEXT,
                file_url           TEXT,
                total_access_slots INTEGER NOT NULL DEFAULT 15
            );
            """
        )
        conn.commit()
    finally:
        conn.close()

def add_author(conn, first_name, last_name):
    #reuse the author if they're already in the db
    row = conn.execute(
        "SELECT author_id FROM author WHERE first_name = ? AND last_name = ?",
        (first_name, last_name),
    ).fetchone()

    if row is not None:
        return row[0]

    cur = conn.execute("INSERT INTO author (first_name, last_name) VALUES (?, ?)", (first_name, last_name))
    return cur.lastrowid

# (title, author first, author last, year, category, keywords, summary, file)
BOOKS = [
    ("Database System Concepts", "Abraham", "Silberschatz", 2019, "Computer Science", "databases, sql, erd",
     "A textbook on how databases are designed, queried with SQL, and kept reliable.", "database_system_concepts.txt"),
    ("Introduction to Algorithms", "Thomas", "Cormen", 2022, "Computer Science", "algorithms, sorting",
     "Covers common algorithms and how to measure how fast they run.", "introduction_to_algorithms.txt"),
    ("Clean Code", "Robert", "Martin", 2008, "Software Engineering", "programming, good habits",
     "Advice on writing code that is easy for other people to read and change.", "clean_code.txt"),
    ("A Brief History of Time", "Stephen", "Hawking", 1988, "Physics", "space, black holes, universe",
     "Explains big ideas about the universe, like black holes and the Big Bang, for regular readers.", "brief_history_of_time.txt"),
    ("Sapiens", "Yuval", "Harari", 2011, "History", "humans, evolution, society",
     "Tells the story of how humans went from small groups to a global society.", "sapiens.txt"),
    ("The Selfish Gene", "Richard", "Dawkins", 1976, "Biology", "genes, evolution",
     "Looks at evolution from the point of view of genes instead of whole animals.", "the_selfish_gene.txt"),
    ("Thinking, Fast and Slow", "Daniel", "Kahneman", 2011, "Psychology", "decisions, mind, bias",
     "Describes two ways people think and how they lead to good and bad decisions.", "thinking_fast_and_slow.txt"),
    ("The River Between", "Ngugi", "wa Thiong'o", 1965, "Literature", "novel, africa, tradition",
     "A novel about two villages and a young man caught between old and new ways.", "the_river_between.txt"),
]

def seed_literature():
    #adds the sample books, only the first time
    #every book gets 15 access slots (BR-03)
    conn = get_connection()
    try:
        if conn.execute("SELECT COUNT(*) FROM literature").fetchone()[0] > 0:
            return

        for title, first, last, year, category, keywords, summary, file_url in BOOKS:
            author_id = add_author(conn, first, last)
            conn.execute(
                "INSERT INTO literature (title, author_id, published_year, category, keywords, summary, file_url) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (title, author_id, year, category, keywords, summary, file_url),
            )
        conn.commit()
    finally:
        conn.close()

BASE_QUERY = """
    SELECT lit.literature_id, lit.title, a.first_name, a.last_name,
           lit.published_year, lit.summary, lit.total_access_slots
    FROM literature lit
    LEFT JOIN author a ON a.author_id = lit.author_id
"""

def get_order_by(sort_by):
    #sort a-z by title or by author's last name
    if sort_by == "author":
        return " ORDER BY a.last_name, a.first_name, lit.title"
    return " ORDER BY lit.title"

def run_query(sql, values=()):
    conn = get_connection()
    try:
        rows = conn.execute(sql, values).fetchall()
    finally:
        conn.close()

    #add the free slots to each book so the page knows to show borrow or hold
    books = []
    for row in rows:
        book = dict(row)
        book["available_slots"] = available_slots(book["literature_id"])
        books.append(book)
    return books

def get_all_books(sort_by="title"):
    return run_query(BASE_QUERY + get_order_by(sort_by))

def search_books(search_text, sort_by="title"):
    #search title, author, category, keywords and summary
    # % means anything can be before or after the text
    pattern = "%" + search_text + "%"
    return run_query(BASE_QUERY + """
        WHERE lit.title LIKE ?
           OR a.first_name LIKE ?
           OR a.last_name LIKE ?
           OR lit.category LIKE ?
           OR lit.keywords LIKE ?
           OR lit.summary LIKE ?
    """ + get_order_by(sort_by), (pattern, pattern, pattern, pattern, pattern, pattern))

def get_book(literature_id):
    #one book's info, or None if it doesn't exist
    books = run_query(BASE_QUERY + " WHERE lit.literature_id = ?", (literature_id,))
    if len(books) == 0:
        return None
    return books[0]
