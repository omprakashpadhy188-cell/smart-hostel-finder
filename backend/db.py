"""MySQL connection helper. Secrets are read from backend/.env (never commit that file)."""
import os
from decimal import Decimal
import mysql.connector
from dotenv import load_dotenv

load_dotenv()   # loads backend/.env into environment variables

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "smart_hostel_finder"),
}


def get_connection():
    if not DB_CONFIG["password"]:
        raise RuntimeError("DB_PASSWORD is not set. Create backend/.env (copy .env.example) and put your MySQL password in it.")
    return mysql.connector.connect(**DB_CONFIG)


def _clean(row):
    """Convert Decimal -> float so rows are JSON friendly."""
    return {k: (float(v) if isinstance(v, Decimal) else v) for k, v in row.items()}


def query(sql, params=None):
    """Run a SELECT and return a list of dict rows."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        rows = [_clean(r) for r in cur.fetchall()]
        cur.close()
        return rows
    finally:
        conn.close()
