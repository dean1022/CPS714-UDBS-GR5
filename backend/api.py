import os, pathlib, secrets, threading
from contextlib import contextmanager
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import database, library, auth
import notifications  # Sprint 4: the Notifications page (US-14)
# Sprint 4 staff mode: the team's staff files decide the faculty rules
import staff, staff_borrow, staff_holds, staff_hold_offers, staff_demo, seed_users

app=FastAPI(title="UDBS Python API", docs_url="/api/docs")
origin=os.environ.get("FRONTEND_ORIGIN", "http://localhost:8888").rstrip("/")
app.add_middleware(CORSMiddleware, allow_origins=[origin], allow_credentials=False, allow_methods=["GET","POST"], allow_headers=["Authorization","Content-Type"])
lock=threading.RLock() # serialize transactions across concurrent demo requests
@contextmanager
def connection():
    with lock:
        raw=database.open_db(); token=database._current.set(raw)
        library.pending_error_notes.clear()
        try:
            yield
            raw.commit()
        except library.LibraryError:
            raw.rollback()
            # US-14: the rollback also removed the error notification, so save it again on its own
            try:
                for user_id, kind, message, created in library.pending_error_notes:
                    database.conn.execute("INSERT INTO notification (user_id, type, message, created_at) VALUES (%s, %s, %s, %s)",
                                          (user_id, kind, message, created))
                raw.commit()
            except Exception:
                raw.rollback()
            raise
        except:
            raw.rollback()
            raise
        finally:
            database._current.reset(token);raw.close()

@app.exception_handler(auth.AuthError)
@app.exception_handler(library.LibraryError)
async def user_error(request,e): return JSONResponse({"message":str(e)},status_code=400)

@app.get('/api/health')
def health(): return {"status":"ok"}

class Credentials(BaseModel):
    identifier:str
    password:str

@app.post('/api/login')
def login(body:Credentials):
    with connection():
        apply_demo_roles_once()
        token=auth.login(body.identifier,body.password)
        user=with_role(auth.get_current_user(token))
        return {"token":token,"user":user}

roles_applied=False
def apply_demo_roles_once():
    # staff_demo.py: even demo IDs are faculty, odd ones are students. Runs once each time the server starts,
    # so a database seeded before this rule is fixed too. Accounts that aren't demo accounts are left alone.
    global roles_applied
    if not roles_applied:
        staff_demo.apply_demo_roles()
        roles_applied=True

def with_role(user):
    # Role distinction: student vs faculty, and the limits that come with it (staff.py / staff_borrow.py)
    if not user: return user
    faculty=staff.is_staff(user['university_id'])
    user['is_staff']=faculty
    user['role_label']='Faculty' if faculty else 'Student'
    user['loan_limit']=staff_borrow.loan_limit(user['university_id'])
    user['hold_limit']=user['max_holds']
    user['perks']=(["No due date on loans",f"Up to {staff.STAFF_MAX_LOANS} active loans","Priority in hold queues"] if faculty else [])
    return user

def current_user(request:Request):
    header=request.headers.get('authorization','')
    if not header.startswith('Bearer '): raise HTTPException(401,'Please sign in.')
    user=auth.get_current_user(header[7:])
    if not user: raise HTTPException(401,'Session expired. Please sign in.')
    return with_role(user)

@app.get('/api/session')
def session(request:Request):
    with connection(): return {"user":current_user(request)}

@app.post('/api/logout')
def logout(request:Request):
    with connection():
        current_user(request)
        auth.logout(request.headers.get('authorization')[7:])
        return {"message":"Logged out"}

def book_obj(book_id):
    b=library.book_details(book_id)
    cat=database.conn.execute('SELECT name FROM category WHERE category_id=%s',(b['category_id'],)).fetchone()
    b['category']=cat['name'];b['available_slots']=b['free_slots'];b['summary']=b.get('summary') or ''
    b['total_access_slots']=min(b['total_access_slots'],library.TEST_CONCURRENT_LOANS)
    b.pop('file_url',None)
    return b

@app.get('/api/books')
def books(request:Request,q:str='',category:str='',sort:str='title'):
    with connection():
        current_user(request);library.check_due_items()
        matching=library.search(q)
        result=[book_obj(x['literature_id']) for x in matching]
        if category: result=[b for b in result if b['category']==category]
        if sort=='author': result.sort(key=lambda b:(', '.join(b['authors']).casefold(),b['title'].casefold()))
        else: result.sort(key=lambda b:b['title'].casefold())
        categories=[r['name'] for r in database.conn.execute('SELECT name FROM category ORDER BY name').fetchall()]
        return {'books':result,'categories':categories,'total':database.conn.execute('SELECT COUNT(*) AS n FROM literature').fetchone()['n']}

@app.get('/api/book/{book_id}')
def book(request:Request,book_id:int):
    with connection():current_user(request);library.check_due_items();return {'book':book_obj(book_id)}

@app.post('/api/borrow/{book_id}')
def borrow(request:Request,book_id:int):
    with connection():
        user=current_user(request)
        result=staff_borrow.borrow_literature(user['university_id'],book_id)  # students fall through to library.borrow
        return {'message':'Borrowed successfully','due_at':result['due_at']}

@app.get('/api/loans')
def loans(request:Request):
    with connection():
        user=current_user(request);library.check_due_items()
        return {'loans':library.my_loans(user['user_id'])}

@app.post('/api/return/{loan_id}')
def early_return(request:Request,loan_id:int):
    with connection():
        user=current_user(request);library.return_book(user['user_id'],loan_id)
        return {'message':'Returned successfully'}

# Renew (US-08) and holds (US-10 to US-13)
@app.post('/api/renew/{loan_id}')
def renew(request:Request,loan_id:int):
    with connection():
        user=current_user(request);library.check_due_items()
        library.renew(user['user_id'],loan_id)
        return {'message':'Renewed successfully'}

@app.post('/api/hold/{book_id}')
def place_hold(request:Request,book_id:int):
    with connection():
        user=current_user(request)
        result=staff_holds.place_hold(user['university_id'],book_id)  # staff go ahead of students
        return {'message':result['message'],'queue_position':result['queue_position']}

@app.get('/api/holds')
def holds(request:Request):
    with connection():
        user=current_user(request);library.check_due_items()
        return {'holds':staff_holds.get_my_holds(user['university_id'])}

@app.get('/api/book/{book_id}/queue')
def queue(request:Request,book_id:int):
    with connection():
        user=current_user(request);library.check_due_items()
        # Staff mode: faculty join ahead of students, so "your place" isn't always the end of the line
        return {'queue':library.hold_queue(book_id),'your_position':staff_holds.next_position(user['university_id'],book_id),
                'staff_priority':user['is_staff']}

@app.post('/api/holds/{hold_id}/cancel')
def cancel_hold(request:Request,hold_id:int):
    with connection():
        user=current_user(request)
        library.cancel_hold(user['user_id'],hold_id)
        return {'message':'Hold cancelled'}

@app.post('/api/holds/{hold_id}/accept')
def accept_hold(request:Request,hold_id:int):
    with connection():
        user=current_user(request);library.check_due_items()  # expire anything whose time is up first
        result=staff_hold_offers.accept_hold(user['university_id'],hold_id)  # staff get no due date
        return {'message':'Hold accepted. The book is now in your Personal Library.','due_at':result['due_at']}

@app.post('/api/holds/{hold_id}/decline')
def decline_hold(request:Request,hold_id:int):
    with connection():
        user=current_user(request);library.check_due_items()
        staff_hold_offers.decline_hold(user['university_id'],hold_id)  # the slot goes to the next person, staff first
        return {'message':'Hold declined'}

# Personal information (US-15)
class ProfileChange(BaseModel):
    display_name:str
    pronouns:str|None=None

@app.get('/api/profile')
def profile(request:Request):
    with connection():
        user=current_user(request)
        return {'profile':library.get_profile(user['user_id'])}

@app.post('/api/profile')
def update_profile(request:Request,body:ProfileChange):
    with connection():
        user=current_user(request)
        return {'message':'Your changes were saved.','profile':library.update_profile(user['user_id'],body.display_name,body.pronouns)}

@app.get('/api/read/{book_id}')
def read(request:Request,book_id:int):
    with connection():
        user=current_user(request)
        library.check_due_items()
        filename=pathlib.Path(library.read_book(user['user_id'],book_id)).name
        # Convert the original .txt literature reference to its PDF counterpart.
        pdf_name=pathlib.Path(filename).stem+'.pdf'
        path=pathlib.Path(__file__).parent/'ebooks'/pdf_name
        if not path.is_file(): raise HTTPException(404,'PDF unavailable. Add the PDF to backend/ebooks first.')
        return FileResponse(path,media_type='application/pdf',filename=pdf_name,content_disposition_type='inline',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

@app.post('/api/jobs/expire')
def expire(request:Request):
    expected=os.environ.get('CRON_SECRET','')
    if not expected or not secrets.compare_digest(request.headers.get('authorization',''),f'Bearer {expected}'):
        raise HTTPException(403,'Forbidden')
    with connection():library.check_due_items();return {'ok':True,'checked_at':datetime.utcnow().isoformat()}

# Notifications (US-14 / FR-23)
@app.get('/api/notifications')
def notification_list(request:Request,unread:int=0):
    with connection():
        user=current_user(request);library.check_due_items()  # sends any reminders that are due first
        return {'notifications':notifications.my_notifications(user['user_id'],bool(unread)),
                'unread':notifications.unread_count(user['user_id'])}

@app.get('/api/notifications/summary')
def notification_summary(request:Request):
    # small request the navigation bar makes every so often for the badge and pop-up
    with connection():
        user=current_user(request);library.check_due_items()
        newest=notifications.my_notifications(user['user_id'])[:5]
        return {'unread':notifications.unread_count(user['user_id']),'latest_id':notifications.latest_id(user['user_id']),'newest':newest}

@app.post('/api/notifications/read')
def notification_read_all(request:Request):
    with connection():
        user=current_user(request);notifications.mark_read(user['user_id'])
        return {'message':'All notifications marked as read.','unread':0}

@app.post('/api/notifications/{notification_id}/read')
def notification_read(request:Request,notification_id:int):
    with connection():
        user=current_user(request);notifications.mark_read(user['user_id'],notification_id)
        return {'unread':notifications.unread_count(user['user_id'])}
