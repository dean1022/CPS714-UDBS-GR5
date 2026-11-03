"""PostgreSQL (Supabase) connection for the UDBS backend.
api.py opens one connection per request, and library.py and auth.py run their queries through `conn`.
Queries use %s placeholders and rows come back as dictionaries, so columns are read as row["name"].
"""
import os, contextvars
import psycopg
from psycopg.rows import dict_row

_current = contextvars.ContextVar("db_conn", default=None)


class Result:
    """The rows a query returned."""
    def __init__(self, rows):
        self.rows = rows
    def fetchone(self): return self.rows[0] if self.rows else None
    def fetchall(self): return self.rows
    def __iter__(self): return iter(self.rows)


def open_db():
    url = os.environ.get("DATABASE_URL")
    if not url: raise RuntimeError("Set DATABASE_URL to your Supabase PostgreSQL connection string")
    return psycopg.connect(url, row_factory=dict_row, autocommit=False)


class DB:
    def raw(self):
        c = _current.get()
        if c is None: raise RuntimeError("Database not opened for request")
        return c
    def execute(self, sql, params=()):
        with self.raw().cursor() as cur:
            cur.execute(sql, params or None)  # no params means a plain query, so a % in the SQL is left alone
            rows = cur.fetchall() if cur.description else []
        return Result(rows)
    def commit(self): self.raw().commit()
    def rollback(self): self.raw().rollback()
    def close(self): pass


conn = DB()
def get_connection(): return conn
