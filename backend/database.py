"""Postgres adapter for Kusal/Megan's original Python code.
The original SQL uses SQLite ? placeholders. This thin wrapper translates those
into psycopg parameters, leaving library.py / auth.py behavior readable.
"""
import os, contextvars, re
import psycopg
from psycopg.rows import dict_row

_current = contextvars.ContextVar("db_conn", default=None)
class Row(dict):
    def __getitem__(self,key):
        if isinstance(key,int): return list(self.values())[key]
        return super().__getitem__(key)

class Result:
    def __init__(self, rows, lastrowid=None):
        self.rows=rows; self.lastrowid=lastrowid
    def fetchone(self): return self.rows[0] if self.rows else None
    def fetchall(self): return self.rows
    def __iter__(self): return iter(self.rows)

def open_db():
    url=os.environ.get("DATABASE_URL")
    if not url: raise RuntimeError("Set DATABASE_URL to your Supabase PostgreSQL connection string")
    return psycopg.connect(url, row_factory=dict_row, autocommit=False)

class DB:
    def raw(self):
        c=_current.get()
        if c is None: raise RuntimeError("Database not opened for request")
        return c
    def execute(self,sql,params=()):
        sql=sql.replace("?","%s")
        # Python modules need cursor.lastrowid for loan notification insertion.
        insert_id=None
        if re.match(r"\s*INSERT INTO loan\s*\(",sql,re.I) and "RETURNING" not in sql.upper():
            sql += " RETURNING loan_id"
            insert_id='loan_id'
        with self.raw().cursor() as cur:
            cur.execute(sql,params)
            rows=[Row(x) for x in cur.fetchall()] if cur.description else []
        return Result(rows, rows[0][insert_id] if insert_id and rows else None)
    def commit(self): self.raw().commit()
    def rollback(self): self.raw().rollback()
    def close(self): pass

conn=DB()
def get_connection(): return conn
