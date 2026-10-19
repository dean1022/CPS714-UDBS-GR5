"""UDBS API on Render. Existing auth.py and library.py own the business rules."""
import os, pathlib, secrets, threading
from contextlib import contextmanager
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import database, library, auth

app=FastAPI(title="UDBS Python API", docs_url="/api/docs")
origin=os.environ.get("FRONTEND_ORIGIN", "http://localhost:8888").rstrip("/")
app.add_middleware(CORSMiddleware, allow_origins=[origin], allow_credentials=False, allow_methods=["GET","POST"], allow_headers=["Authorization","Content-Type"])
lock=threading.RLock() # serialize transactions across concurrent demo requests
@contextmanager
def connection():
    with lock:
        raw=database.open_db(); token=database._current.set(raw)
        try:
            yield
            raw.commit()
        except:
            raw.rollback()
            raise
        finally:
            database._current.reset(token);raw.close()

def error(e):
    if isinstance(e,(auth.AuthError,library.LibraryError,ValueError)): return JSONResponse({"message":str(e)}, status_code=400)
    raise e

@app.exception_handler(auth.AuthError)
@app.exception_handler(library.LibraryError)
async def user_error(request,e): return JSONResponse({"message":str(e)},status_code=400)

@app.get('/api/health')
def health(): return {"status":"ok"}

class Credentials(BaseModel):
    identifier:str
    password:str

class Identifier(BaseModel):
    book_id:int|None=None
    loan_id:int|None=None

@app.post('/api/login')
def login(body:Credentials):
    with connection():
        token=auth.login(body.identifier,body.password)
        user=auth.get_current_user(token)
        return {"token":token,"user":user}

def current_user(request:Request):
    header=request.headers.get('authorization','')
    if not header.startswith('Bearer '): raise HTTPException(401,'Please sign in.')
    user=auth.get_current_user(header[7:])
    if not user: raise HTTPException(401,'Session expired. Please sign in.')
    return user

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
    cat=database.conn.execute('SELECT name FROM category WHERE category_id=?',(b['category_id'],)).fetchone()
    b['category']=cat['name'];b['available_slots']=b['free_slots'];b['summary']=b.get('summary') or ''
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
        return {'books':result,'categories':categories,'total':database.conn.execute('SELECT count(*) FROM literature').fetchone()[0]}

@app.get('/api/book/{book_id}')
def book(request:Request,book_id:int):
    with connection():current_user(request);library.check_due_items();return {'book':book_obj(book_id)}

@app.post('/api/borrow/{book_id}')
def borrow(request:Request,book_id:int):
    with connection():
        user=current_user(request)
        library.borrow(user['user_id'],book_id)
        return {'message':'Borrowed successfully'}

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
