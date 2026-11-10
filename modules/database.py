import sqlite3
from datetime import datetime
from config import DB_PATH

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                analyzed_at TEXT NOT NULL,
                last_close REAL,
                score INTEGER,
                decision TEXT,
                buy_zone TEXT,
                target_price TEXT,
                stop_loss TEXT,
                summary TEXT
            )
        """)
        conn.commit()

def save_analysis(symbol: str, last_close: float, score: int, decision: str, buy_zone: str, target_price: str, stop_loss: str, summary: str):
    init_db()
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO analysis_history (symbol, analyzed_at, last_close, score, decision, buy_zone, target_price, stop_loss, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), last_close, score, decision, buy_zone, target_price, stop_loss, summary))
        conn.commit()

def get_recent_history(symbol: str = None, limit: int = 10):
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        if symbol:
            cursor.execute("SELECT symbol, analyzed_at, last_close, decision, buy_zone, target_price, stop_loss, summary FROM analysis_history WHERE symbol = ? ORDER BY id DESC LIMIT ?", (symbol, limit))
        else:
            cursor.execute("SELECT symbol, analyzed_at, last_close, decision, buy_zone, target_price, stop_loss, summary FROM analysis_history ORDER BY id DESC LIMIT ?", (limit,))
        return cursor.fetchall()
