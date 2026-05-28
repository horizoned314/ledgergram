import sqlite3
import os

DB_PATH = "data/receipts.db"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL,
                type TEXT,
                merchant TEXT,
                date TEXT,
                raw_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

def save_transaction(amount: float, tx_type: str, merchant: str, date: str, raw_text: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (amount, type, merchant, date, raw_text)
            VALUES (?, ?, ?, ?, ?)
        ''', (amount, tx_type, merchant, date, raw_text))
        conn.commit()
        return cursor.lastrowid

def get_summary():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT type, SUM(amount) FROM transactions GROUP BY type")
        return cursor.fetchall()