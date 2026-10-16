#Remaining loan time (US-07) for the University Digital Borrowing System

from datetime import datetime

from database import get_connection
from auth import TIME_FORMAT

def get_active_loans(university_id):
    #user's active loans w/ the title, soonest due first
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT l.loan_id, lit.title, l.borrowed_at, l.due_at
               FROM loan l JOIN literature lit ON lit.literature_id = l.literature_id
               WHERE l.university_id = ? AND l.status = 'ACTIVE'
               ORDER BY l.due_at""",
            (university_id,),
        ).fetchall()

        #convert db rows into dictionaries
        return [dict(row) for row in rows]
    finally:
        conn.close()

def seconds_left(due_at, now=None):
    now = now or datetime.now()
    left = datetime.strptime(due_at, TIME_FORMAT) - now

    #never go below 0
    return max(0, int(left.total_seconds()))

def format_time_left(seconds):
    if seconds <= 0:
        return "Expired"

    # 86400 secs in a day, 3600 in an hr
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{days}d {hours}h {minutes}m {secs}s"

def remaining_time(due_at, now=None):
    #time left on a loan e.g. "13d 23h 59m 58s"
    return format_time_left(seconds_left(due_at, now))
