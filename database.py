import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("library.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                university_id TEXT PRIMARY KEY,
                email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                first_name    TEXT NOT NULL,
                last_name     TEXT NOT NULL,
                display_name  TEXT NOT NULL,
                pronouns      TEXT,
                status        TEXT NOT NULL CHECK (status IN ('student', 'faculty'))
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token         TEXT PRIMARY KEY,
                university_id TEXT NOT NULL REFERENCES users(university_id),
                created_at    TEXT NOT NULL,
                expires_at    TEXT NOT NULL
            );
            """
        )
