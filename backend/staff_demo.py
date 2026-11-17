#Demo account roles for the University Digital Borrowing System
#rule: a demo account with an even ID number is faculty, an odd one is a student
#e.g. 501000002 is faculty and 700000001 is a student
#faculty are the staff (see staff.py), so this decides which demo accounts get the staff perks

from database import get_connection
from seed_users import STUDENTS, FACULTY

def demo_status(university_id):
    #works out the role from the last digit of the ID
    if int(university_id[-1]) % 2 == 0:
        return "faculty"
    return "student"

def demo_ids():
    #every demo account ID from seed_users.py
    return [person[0] for person in STUDENTS + FACULTY]

def apply_demo_roles():
    #run after seed(), it saves the even/odd role on each demo account
    #it also fixes demo accounts that were seeded before this rule existed
    #accounts that aren't demo accounts are left alone
    conn = get_connection()
    try:
        for university_id in demo_ids():
            conn.execute(
                "UPDATE users SET status = %s WHERE university_id = %s",
                (demo_status(university_id), university_id),
            )
        conn.commit()
    finally:
        conn.close()
