# app.py
from fastapi import FastAPI, Request, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import sqlite3, hashlib, secrets, datetime, os
from pathlib import Path
from typing import Optional, Dict
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import OpenAI
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()  # ← this must come BEFORE any route definitions
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")  # ← correct, no indentation if global

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})




# Load env variables
load_dotenv()

# App setup
app = FastAPI(title="Citizen AI")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Create folders if needed
Path("templates").mkdir(exist_ok=True)
Path("static").mkdir(exist_ok=True)

# Fallbacks if AI fails
FALLBACK_RESPONSES = [
    "Please visit india.gov.in or contact your local authority.",
    "Consult your nearest government office for proper assistance.",
    "Refer to the official portal for accurate guidance."
]

class CitizenAIDatabase:
    def __init__(self, db_path="citizen_ai.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, username TEXT UNIQUE, email TEXT UNIQUE,
                password_hash TEXT, salt TEXT, full_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME, is_active BOOLEAN DEFAULT 1
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY, user_id INTEGER, session_token TEXT UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME, is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY, user_id INTEGER,
                user_message TEXT, ai_response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sentiment_analysis (
                id INTEGER PRIMARY KEY, user_id INTEGER,
                feedback_text TEXT, sentiment TEXT, confidence REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.commit()
        conn.close()

    def _hash_password(self, password: str, salt: Optional[str] = None):
        if not salt:
            salt = secrets.token_hex(16)
        hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hash.hex(), salt

    def register_user(self, username, email, password, full_name):
        if len(password) < 8:
            return {"success": False, "message": "Password must be at least 8 characters"}
        pw_hash, salt = self._hash_password(password)
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO users (username, email, password_hash, salt, full_name)
                VALUES (?, ?, ?, ?, ?)''', (username, email, pw_hash, salt, full_name))
            conn.commit()
            user_id = cur.lastrowid
            return {"success": True, "user_id": user_id}
        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                return {"success": False, "message": "Username exists"}
            if "email" in str(e):
                return {"success": False, "message": "Email exists"}
            return {"success": False, "message": "Registration failed"}
        finally:
            conn.close()

    def login_user(self, username, password):
        conn = sqlite3.connect(self.db_path)
        user = conn.execute('''
            SELECT id, username, password_hash, salt, is_active, full_name
            FROM users WHERE username = ? OR email = ?''', (username, username)).fetchone()
        if not user or not user[4]:
            conn.close()
            return {"success": False, "message": "Invalid credentials"}
        uid, uname, stored_hash, salt, _, fname = user
        input_hash, _ = self._hash_password(password, salt)
        if input_hash == stored_hash:
            token = secrets.token_urlsafe(32)
            expiry = datetime.datetime.now() + datetime.timedelta(days=7)
            conn.execute('''
                INSERT INTO sessions (user_id, session_token, expires_at)
                VALUES (?, ?, ?)''', (uid, token, expiry))
            conn.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (uid,))
            conn.commit()
            conn.close()
            return {"success": True, "session_token": token, "user_id": uid, "username": uname, "full_name": fname}
        conn.close()
        return {"success": False, "message": "Invalid credentials"}

    def verify_session(self, token: str):
        conn = sqlite3.connect(self.db_path)
        row = conn.execute('''
            SELECT s.user_id, u.username, s.expires_at, u.full_name
            FROM sessions s JOIN users u ON s.user_id = u.id
            WHERE s.session_token = ? AND s.is_active = 1
        ''', (token,)).fetchone()
        conn.close()
        if not row: return None
        uid, uname, expiry, fname = row
        if datetime.datetime.fromisoformat(expiry) < datetime.datetime.now():
            return None
        return {"user_id": uid, "username": uname, "full_name": fname}

    def save_chat(self, uid, msg, reply):
        conn = sqlite3.connect(self.db_path)
        conn.execute('INSERT INTO chat_history (user_id, user_message, ai_response) VALUES (?, ?, ?)',
                     (uid, msg, reply))
        conn.commit()
        conn.close()

    def save_sentiment(self, uid, text, sentiment, confidence):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            INSERT INTO sentiment_analysis (user_id, feedback_text, sentiment, confidence)
            VALUES (?, ?, ?, ?)''', (uid, text, sentiment, confidence))
        conn.commit()
        conn.close()

    def get_chat_history(self, uid, limit=10):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute('''
            SELECT user_message, ai_response, timestamp
            FROM chat_history WHERE user_id = ?
            ORDER BY timestamp DESC LIMIT ?''', (uid, limit)).fetchall()
        conn.close()
        return rows

    def get_sentiment_stats(self):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute('SELECT sentiment, COUNT(*) FROM sentiment_analysis GROUP BY sentiment').fetchall()
        conn.close()
        return dict(rows)

# Initialize database
db = CitizenAIDatabase()

class SimpleCitizenAI:
    def __init__(self):
        self.llm = OpenAI(openai_api_key=os.getenv("OPENAI_API_KEY"))
        self.prompt_template = PromptTemplate(
            input_variables=["user_question"],
            template="""
You are Citizen AI, a smart assistant for Indian citizens. You help with:
- Indian schemes, smart cities, sustainability, pollution, energy, water, waste
- Always follow Indian laws
User question: {user_question}
Give a helpful, Indian-context answer.
"""
        )

    def generate_response(self, user_message: str) -> str:
        try:
            prompt = self.prompt_template.format(user_question=user_message)
            return self.llm.invoke(prompt).strip()
        except Exception as e:
            return FALLBACK_RESPONSES[0] + f" (Error: {str(e)})"

ai = SimpleCitizenAI()

def get_current_user(session_token: Optional[str] = Cookie(None)):
    return db.verify_session(session_token)

def analyse_sentiment(text: str):
    positives = ['good', 'great', 'helpful', 'happy']
    negatives = ['bad', 'terrible', 'angry', 'poor']
    low = text.lower()
    p = sum(w in low for w in positives)
    n = sum(w in low for w in negatives)
    if p > n: return "Positive", min(0.6 + 0.1 * (p - n), 1.0)
    if n > p: return "Negative", min(0.6 + 0.1 * (n - p), 1.0)
    return "Neutral", 0.5

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session_token: Optional[str] = Cookie(None)):
    if get_current_user(session_token):
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...), full_name: str = Form(...)):
    result = db.register_user(username, email, password, full_name)
    if result["success"]:
        return RedirectResponse("/login?message=Registered", status_code=302)
    return templates.TemplateResponse("register.html", {"request": request, "error": result["message"]})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, message: Optional[str] = None):
    return templates.TemplateResponse("login.html", {"request": request, "message": message})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    result = db.login_user(username, password)
    if result["success"]:
        resp = RedirectResponse("/dashboard", status_code=302)
        resp.set_cookie("session_token", result["session_token"], httponly=True)
        return resp
    return templates.TemplateResponse("login.html", {"request": request, "error": result["message"]})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session_token: Optional[str] = Cookie(None)):
    user = get_current_user(session_token)
    if not user: return RedirectResponse("/login")
    history = db.get_chat_history(user["user_id"], 5)
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user, "chat_history": history})

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request, session_token: Optional[str] = Cookie(None)):
    user = get_current_user(session_token)
    if not user: return RedirectResponse("/login")
    return templates.TemplateResponse("chat.html", {"request": request, "user": user})

@app.post("/chat")
async def chat(request: Request, message: str = Form(...), session_token: Optional[str] = Cookie(None)):
    user = get_current_user(session_token)
    if not user: return RedirectResponse("/login")
    reply = ai.generate_response(message)
    db.save_chat(user["user_id"], message, reply)
    return templates.TemplateResponse("chat.html", {"request": request, "user": user, "user_message": message, "ai_response": reply})

@app.get("/feedback", response_class=HTMLResponse)
async def feedback_page(request: Request, session_token: Optional[str] = Cookie(None)):
    user = get_current_user(session_token)
    if not user: return RedirectResponse("/login")
    return templates.TemplateResponse("feedback.html", {"request": request, "user": user})

@app.post("/feedback")
async def feedback(request: Request, feedback: str = Form(...), session_token: Optional[str] = Cookie(None)):
    user = get_current_user(session_token)
    if not user: return RedirectResponse("/login")
    sentiment, confidence = analyse_sentiment(feedback)
    db.save_sentiment(user["user_id"], feedback, sentiment, confidence)
    return templates.TemplateResponse("feedback.html", {"request": request, "user": user, "success": "Thank you!", "sentiment": sentiment})

@app.get("/logout")
async def logout():
    resp = RedirectResponse("/", status_code=302)
    resp.delete_cookie("session_token")
    return resp

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", reload=True)
