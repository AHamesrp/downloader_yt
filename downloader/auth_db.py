"""SQLite: usuários e códigos OTP de login (2FA por e-mail)."""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from werkzeug.security import check_password_hash

_lock = threading.RLock()


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path) -> None:
    with _lock:
        conn = _connect(db_path)
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT COLLATE NOCASE UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS login_otps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    code_hash TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    used INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                CREATE INDEX IF NOT EXISTS idx_login_otps_user ON login_otps(user_id);
                """
            )
            conn.commit()
        finally:
            conn.close()


def with_connection(db_path: Path, fn):
    with _lock:
        conn = _connect(db_path)
        try:
            return fn(conn)
        finally:
            conn.close()


def create_user(conn: sqlite3.Connection, email: str, password_hash: str) -> int | None:
    email = email.strip().lower()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?,?,?)",
            (email, password_hash, time.time()),
        )
        conn.commit()
        return int(cur.lastrowid)
    except sqlite3.IntegrityError:
        conn.rollback()
        return None


def get_user_by_email(conn: sqlite3.Connection, email: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?",
        (email.strip().lower(),),
    ).fetchone()
    return dict(row) if row else None


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def create_login_otp(conn: sqlite3.Connection, user_id: int, code_hash: str, ttl_sec: int = 600) -> None:
    now = time.time()
    conn.execute("UPDATE login_otps SET used = 1 WHERE user_id = ? AND used = 0", (user_id,))
    conn.execute(
        "INSERT INTO login_otps (user_id, code_hash, expires_at, used) VALUES (?,?,?,0)",
        (user_id, code_hash, now + ttl_sec),
    )
    conn.commit()


def verify_login_otp(conn: sqlite3.Connection, user_id: int, plain_code: str) -> bool:
    now = time.time()
    rows = conn.execute(
        """
        SELECT id, code_hash FROM login_otps
        WHERE user_id = ? AND used = 0 AND expires_at > ?
        ORDER BY id DESC LIMIT 8
        """,
        (user_id, now),
    ).fetchall()
    for r in rows:
        if check_password_hash(r["code_hash"], plain_code):
            conn.execute("UPDATE login_otps SET used = 1 WHERE id = ?", (r["id"],))
            conn.commit()
            return True
    return False
