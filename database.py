import os
import sqlite3
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("DATA_DIR", BASE_DIR)
os.makedirs(DATA_DIR, exist_ok=True)
DB = os.path.join(DATA_DIR, "chakra_bot.db")

def _c():
    return sqlite3.connect(DB)

def create_tables():
    connection = _c()
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            telegram_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS test_results(
            id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER,
            leading_chakra INTEGER, scores TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS premium_reports(
            id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER,
            result_id INTEGER, report_path TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(telegram_id,result_id)
        );
        CREATE TABLE IF NOT EXISTS energy_maps(
            id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER,
            scores TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS payments(
            id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER,
            result_id INTEGER, amount INTEGER, currency TEXT, status TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS funnel_state(
            telegram_id INTEGER PRIMARY KEY, step INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    connection.commit(); connection.close()

def save_user(user):
    connection = _c()
    connection.execute("INSERT INTO users VALUES(?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name", (user.id, user.username, user.first_name))
    connection.commit(); connection.close()

def save_result(uid, chakra, scores):
    connection = _c(); cursor = connection.cursor()
    cursor.execute("INSERT INTO test_results(telegram_id,leading_chakra,scores) VALUES(?,?,?)", (uid, chakra, json.dumps(scores, ensure_ascii=False)))
    result_id = cursor.lastrowid; connection.commit(); connection.close(); return result_id

def get_result(uid, result_id):
    connection = _c(); row = connection.execute("SELECT id,leading_chakra,scores,created_at FROM test_results WHERE telegram_id=? AND id=?", (uid, result_id)).fetchone(); connection.close(); return row

def get_last(uid):
    connection = _c(); row = connection.execute("SELECT id,leading_chakra,scores,created_at FROM test_results WHERE telegram_id=? ORDER BY id DESC LIMIT 1", (uid,)).fetchone(); connection.close(); return row

def history(uid):
    connection = _c(); rows = connection.execute("SELECT id,leading_chakra,created_at FROM test_results WHERE telegram_id=? ORDER BY id DESC", (uid,)).fetchall(); connection.close(); return rows

def save_report(uid, result_id, path):
    connection = _c(); connection.execute("INSERT OR REPLACE INTO premium_reports(telegram_id,result_id,report_path) VALUES(?,?,?)", (uid, result_id, path)); connection.commit(); connection.close()

def get_report(uid, result_id):
    connection = _c(); row = connection.execute("SELECT report_path FROM premium_reports WHERE telegram_id=? AND result_id=?", (uid, result_id)).fetchone(); connection.close(); return row

def save_energy_map(uid, scores):
    connection = _c(); cursor = connection.cursor(); cursor.execute("INSERT INTO energy_maps(telegram_id,scores) VALUES(?,?)", (uid, json.dumps(scores, ensure_ascii=False))); map_id = cursor.lastrowid; connection.commit(); connection.close(); return map_id

def get_last_energy_map(uid):
    connection = _c(); row = connection.execute("SELECT id,scores,created_at FROM energy_maps WHERE telegram_id=? ORDER BY id DESC LIMIT 1", (uid,)).fetchone(); connection.close(); return row

def save_payment(uid, result_id, amount, currency, status="paid"):
    connection = _c(); connection.execute("INSERT INTO payments(telegram_id,result_id,amount,currency,status) VALUES(?,?,?,?,?)", (uid, result_id, amount, currency, status)); connection.commit(); connection.close()

def has_paid(uid, result_id):
    connection = _c(); row = connection.execute("SELECT 1 FROM payments WHERE telegram_id=? AND result_id=? AND status='paid' ORDER BY id DESC LIMIT 1", (uid, result_id)).fetchone(); connection.close(); return bool(row)

def set_funnel_step(uid, step):
    connection = _c(); connection.execute("INSERT INTO funnel_state(telegram_id,step,updated_at) VALUES(?,?,CURRENT_TIMESTAMP) ON CONFLICT(telegram_id) DO UPDATE SET step=excluded.step, updated_at=CURRENT_TIMESTAMP", (uid, step)); connection.commit(); connection.close()

def stats():
    connection = _c(); users = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]; results = connection.execute("SELECT COUNT(*) FROM test_results").fetchone()[0]; distribution = dict(connection.execute("SELECT leading_chakra,COUNT(*) FROM test_results GROUP BY leading_chakra").fetchall()); connection.close(); return users, results, distribution
