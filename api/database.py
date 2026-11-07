
import sqlite3
from pathlib import Path
from contextlib import contextmanager
DB_PATH = Path(__file__).parent / "insurance.db"

@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # rows behave like dicts: row["age"]
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn            
        conn.commit()         
    except Exception:
        conn.rollback()       
        raise                 
    finally:
        conn.close()          

def init_db() -> None:
    with get_connection() as conn:
        conn.executescript( """
            CREATE TABLE IF NOT EXISTS customers (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT    NOT NULL,
                email TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                age   INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS quotes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                car_value   REAL    NOT NULL,
                price       REAL    NOT NULL,
                created_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS policies (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_id INTEGER NOT NULL UNIQUE REFERENCES quotes(id) ON DELETE CASCADE,
                status   TEXT    NOT NULL DEFAULT 'active'
            );
            """)
    