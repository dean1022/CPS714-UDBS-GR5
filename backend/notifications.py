#Notifications page (US-14 / FR-23)
#library.py saves the notifications with notify() when something happens:
#  HOLD_READY, HOLD_WINDOW_CLOSING, ERROR, BORROW_SUCCESS, LOAN_RETURNED, LOAN_LIMIT, HOLD_LIMIT
#  plus HOLD_PLACED, HOLD_CANCELLED, HOLD_DECLINED, HOLD_EXPIRED, LOAN_RENEWED and LOAN_DUE_SOON
#this file only reads them back for the website and marks them as read

from database import conn

#short titles the website shows above each message
TITLES = {
    "HOLD_READY": "Hold ready",
    "HOLD_WINDOW_CLOSING": "Decision window closing",
    "HOLD_EXPIRED": "Hold expired",
    "HOLD_PLACED": "Hold placed",
    "HOLD_CANCELLED": "Hold cancelled",
    "HOLD_DECLINED": "Hold declined",
    "BORROW_SUCCESS": "Borrowed",
    "LOAN_RETURNED": "Loan returned",
    "LOAN_RENEWED": "Loan renewed",
    "LOAN_DUE_SOON": "Loan due soon",
    "LOAN_LIMIT": "Loan limit reached",
    "HOLD_LIMIT": "Hold limit reached",
    "ERROR": "Something went wrong",
}

#which ones ask the user to do something (the page highlights these)
NEEDS_ACTION = {"HOLD_READY", "HOLD_WINDOW_CLOSING", "LOAN_DUE_SOON"}

MAX_SHOWN = 200  # the page shows the newest 200


def my_notifications(user_id, unread_only=False):
    #newest first
    sql = ("SELECT n.notification_id, n.type, n.message, n.created_at, n.is_read, n.loan_id, n.hold_id,"
           " COALESCE(lo.literature_id, h.literature_id) AS literature_id"
           " FROM notification n"
           " LEFT JOIN loan lo ON lo.loan_id = n.loan_id"
           " LEFT JOIN hold h ON h.hold_id = n.hold_id"
           " WHERE n.user_id = %s")
    if unread_only:
        sql += " AND n.is_read = 0"
    sql += " ORDER BY n.created_at DESC, n.notification_id DESC LIMIT %s"
    rows = conn.execute(sql, (user_id, MAX_SHOWN)).fetchall()
    return [dict(row) | {"title": TITLES.get(row["type"], "Notice"),
                         "needs_action": row["type"] in NEEDS_ACTION,
                         "is_read": bool(row["is_read"])} for row in rows]


def unread_count(user_id):
    return conn.execute(
        "SELECT COUNT(*) AS n FROM notification WHERE user_id = %s AND is_read = 0", (user_id,)
    ).fetchone()["n"]


def latest_id(user_id):
    #the newest notification id, so the website can tell when a new one arrives
    row = conn.execute("SELECT MAX(notification_id) AS n FROM notification WHERE user_id = %s", (user_id,)).fetchone()
    return row["n"] or 0


def mark_read(user_id, notification_id=None):
    #one notification, or all of them when notification_id is None
    if notification_id is None:
        conn.execute("UPDATE notification SET is_read = 1 WHERE user_id = %s AND is_read = 0", (user_id,))
    else:
        conn.execute("UPDATE notification SET is_read = 1 WHERE user_id = %s AND notification_id = %s",
                     (user_id, notification_id))
    conn.commit()
