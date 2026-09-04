import sqlite3, json
DB="chakra_bot.db"
def _c(): return sqlite3.connect(DB)
def create_tables():
 c=_c(); c.executescript("""CREATE TABLE IF NOT EXISTS users(telegram_id INTEGER PRIMARY KEY,username TEXT,first_name TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
 CREATE TABLE IF NOT EXISTS test_results(id INTEGER PRIMARY KEY AUTOINCREMENT,telegram_id INTEGER,leading_chakra INTEGER,scores TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
 CREATE TABLE IF NOT EXISTS premium_reports(id INTEGER PRIMARY KEY AUTOINCREMENT,telegram_id INTEGER,result_id INTEGER,report_path TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(telegram_id,result_id));"""); c.commit(); c.close()
def save_user(u):
 c=_c(); c.execute("INSERT INTO users VALUES(?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username,first_name=excluded.first_name",(u.id,u.username,u.first_name)); c.commit(); c.close()
def save_result(uid,ch,scores):
 c=_c(); cur=c.cursor(); cur.execute("INSERT INTO test_results(telegram_id,leading_chakra,scores) VALUES(?,?,?)",(uid,ch,json.dumps(scores,ensure_ascii=False))); rid=cur.lastrowid;c.commit();c.close();return rid
def get_result(uid,rid):
 c=_c();r=c.execute("SELECT id,leading_chakra,scores,created_at FROM test_results WHERE telegram_id=? AND id=?",(uid,rid)).fetchone();c.close();return r
def get_last(uid):
 c=_c();r=c.execute("SELECT id,leading_chakra,scores,created_at FROM test_results WHERE telegram_id=? ORDER BY id DESC LIMIT 1",(uid,)).fetchone();c.close();return r
def history(uid):
 c=_c();r=c.execute("SELECT id,leading_chakra,created_at FROM test_results WHERE telegram_id=? ORDER BY id DESC",(uid,)).fetchall();c.close();return r
def save_report(uid,rid,path):
 c=_c();c.execute("INSERT OR REPLACE INTO premium_reports(telegram_id,result_id,report_path) VALUES(?,?,?)",(uid,rid,path));c.commit();c.close()
def get_report(uid,rid):
 c=_c();r=c.execute("SELECT report_path FROM premium_reports WHERE telegram_id=? AND result_id=?",(uid,rid)).fetchone();c.close();return r
def stats():
 c=_c(); users=c.execute("SELECT COUNT(*) FROM users").fetchone()[0]; results=c.execute("SELECT COUNT(*) FROM test_results").fetchone()[0]; dist=dict(c.execute("SELECT leading_chakra,COUNT(*) FROM test_results GROUP BY leading_chakra").fetchall());c.close();return users,results,dist
