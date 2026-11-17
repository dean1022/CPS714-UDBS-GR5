#Hold queue with staff priority for the University Digital Borrowing System
#same queue as holds.py, but staff are placed ahead of students
#two staff members are still sorted by who placed their hold first
#
#changed: the old holds.py was replaced by library.py, so place_hold() now calls library.py.
#library.py also uses get_queue() below to number the queue, so this is the one place the order is decided.
#Every change from the team's original staff_holds.py is marked with "changed:".

import library as holds  # changed: library.py does what holds.py did
from database import get_connection
from staff import is_staff, STAFF_STATUSES

#used in ORDER BY: staff rows get 0 and students get 1, so staff sort first
STAFF_FIRST = "CASE WHEN u.status = ANY(%s) THEN 0 ELSE 1 END"

#changed: hold rows point at library_user.user_id now, so we reach the users table through library_user
#(LEFT JOIN: a library user without a university record counts as a student)
HOLD_USERS = """FROM hold h
                JOIN library_user lu ON lu.user_id = h.user_id
                LEFT JOIN users u ON u.university_id = lu.university_id"""

def get_queue(literature_id):
    #everyone waiting for an item, staff first, then by time placed
    #no names so other users' info isn't shown
    conn = get_connection()
    try:
        rows = conn.execute(
            f"""SELECT h.hold_id, h.placed_at
                {HOLD_USERS}
                WHERE h.literature_id = %s AND h.status = 'WAITING'
                ORDER BY {STAFF_FIRST}, h.placed_at, h.hold_id""",
            (literature_id, list(STAFF_STATUSES)),
        ).fetchall()
    finally:
        conn.close()

    queue = []
    for position, row in enumerate(rows, start=1):
        queue.append({
            "position": position,
            "hold_id": row["hold_id"],
            "placed_at": row["placed_at"],
        })
    return queue

def queue_length(literature_id):
    return len(get_queue(literature_id))

def get_queue_position(hold_id, literature_id):
    #position of one hold in its queue, None if it isn't waiting
    for spot in get_queue(literature_id):
        if spot["hold_id"] == hold_id:
            return spot["position"]
    return None

def next_position(university_id, literature_id):
    #where this user would land if they placed a hold now
    conn = get_connection()
    try:
        row = conn.execute(
            f"""SELECT COUNT(*) AS total,
                      COUNT(*) FILTER (WHERE u.status = ANY(%s)) AS staff
               {HOLD_USERS}
               WHERE h.literature_id = %s AND h.status = 'WAITING'""",
            (list(STAFF_STATUSES), literature_id),
        ).fetchone()
    finally:
        conn.close()

    #staff only wait behind other staff, students wait behind everyone
    if is_staff(university_id):
        return row["staff"] + 1
    return row["total"] + 1

def place_hold(university_id, literature_id, now=None):
    #holds.py does all the checks and saves the hold
    #only the queue position changes, because staff move ahead of students
    hold_id = holds.place_hold(holds.user_id_for(university_id), literature_id)  # changed: library.place_hold(user_id, ...)
    result = {"hold_id": hold_id}  # changed: library.place_hold returns the new hold's id

    position = get_queue_position(result["hold_id"], literature_id)
    result["queue_position"] = position
    result["message"] = f"Hold placed. You're #{position} in the queue."
    return result

def get_my_holds(university_id):
    #data for the holds page, same as holds_page.py but with the staff-first positions
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT h.hold_id, h.literature_id, lit.title, h.status, h.placed_at, h.decision_deadline
               FROM hold h JOIN literature lit ON lit.literature_id = h.literature_id
               JOIN library_user lu ON lu.user_id = h.user_id
               WHERE lu.university_id = %s AND h.status IN ('WAITING', 'READY')
               ORDER BY h.placed_at, h.hold_id""",  # changed: user_id join, and decision_deadline for the countdown
            (university_id,),
        ).fetchall()
    finally:
        conn.close()

    my_holds = []
    for row in rows:
        hold = dict(row)
        hold["queue_position"] = get_queue_position(hold["hold_id"], hold["literature_id"])
        hold["queue_length"] = queue_length(hold["literature_id"])
        my_holds.append(hold)
    return my_holds
