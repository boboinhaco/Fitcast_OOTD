"""회원가입·로그인과 저장한 코디 (SQLite, 표준 라이브러리만 사용).

- users: 이메일·이름·비밀번호 해시(pbkdf2)·아바타 프로필(JSON)
- sessions: 로그인 토큰 (HttpOnly 쿠키 fc_session)
- looks: 저장한 코디 (착용 아이템·실제 상품·AI 피팅 이미지 키)
"""

import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from fitcast import config

COOKIE = "fc_session"
PBKDF2_ROUNDS = 200_000
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
  salt TEXT NOT NULL, pw_hash TEXT NOT NULL, profile TEXT NOT NULL DEFAULT '{}', created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS looks (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), title TEXT NOT NULL DEFAULT '',
  outfit TEXT NOT NULL, products TEXT NOT NULL DEFAULT '[]', tryon_key TEXT NOT NULL DEFAULT '', created TEXT NOT NULL);
"""


class AccountError(ValueError):
    """가입·로그인 입력 오류 (화면에 그대로 안내)."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def db():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(SCHEMA)
        yield con
        con.commit()
    finally:
        con.close()


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ROUNDS).hex()


def _user_dict(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "email": row["email"], "name": row["name"], "profile": json.loads(row["profile"] or "{}")}


def signup(email: str, password: str, name: str, profile: dict | None = None) -> tuple[dict, str]:
    """가입 후 (사용자, 세션 토큰)."""
    email, name = email.strip().lower(), name.strip()
    if "@" not in email or len(email) < 5:
        raise AccountError("이메일 형식을 확인해 주세요.")
    if len(password) < 6:
        raise AccountError("비밀번호는 6자 이상이어야 해요.")
    if not name:
        raise AccountError("이름(닉네임)을 입력해 주세요.")
    salt = secrets.token_hex(16)
    with db() as con:
        if con.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise AccountError("이미 가입된 이메일이에요. 로그인해 주세요.")
        cur = con.execute(
            "INSERT INTO users (email, name, salt, pw_hash, profile, created) VALUES (?, ?, ?, ?, ?, ?)",
            (email, name, salt, _hash(password, salt), json.dumps(profile or {}, ensure_ascii=False), _now()),
        )
        token = _new_session(con, cur.lastrowid)
        return _user_dict(con.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()), token


def login(email: str, password: str) -> tuple[dict, str]:
    with db() as con:
        row = con.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
        if not row or not secrets.compare_digest(_hash(password, row["salt"]), row["pw_hash"]):
            raise AccountError("이메일 또는 비밀번호가 맞지 않아요.")
        return _user_dict(row), _new_session(con, row["id"])


def _new_session(con: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    con.execute("INSERT INTO sessions (token, user_id, created) VALUES (?, ?, ?)", (token, user_id, _now()))
    return token


def logout(token: str) -> None:
    with db() as con:
        con.execute("DELETE FROM sessions WHERE token = ?", (token,))


def current_user(token: str | None) -> dict | None:
    if not token:
        return None
    with db() as con:
        row = con.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?", (token,)
        ).fetchone()
        return _user_dict(row) if row else None


def save_profile(user_id: int, profile: dict) -> None:
    with db() as con:
        con.execute("UPDATE users SET profile = ? WHERE id = ?", (json.dumps(profile, ensure_ascii=False), user_id))


def _look_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "title": row["title"], "outfit": json.loads(row["outfit"]), "products": json.loads(row["products"]),
        "tryon_key": row["tryon_key"], "tryon_image": f"/tryon/{row['tryon_key']}.png" if row["tryon_key"] else "",
        "created": row["created"],
    }


def list_looks(user_id: int) -> list[dict]:
    with db() as con:
        return [_look_dict(r) for r in con.execute("SELECT * FROM looks WHERE user_id = ? ORDER BY id DESC", (user_id,))]


def add_look(user_id: int, title: str, outfit: dict, products: list, tryon_key: str) -> dict:
    with db() as con:
        cur = con.execute(
            "INSERT INTO looks (user_id, title, outfit, products, tryon_key, created) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, title.strip()[:60], json.dumps(outfit, ensure_ascii=False), json.dumps(products, ensure_ascii=False), tryon_key, _now()),
        )
        return _look_dict(con.execute("SELECT * FROM looks WHERE id = ?", (cur.lastrowid,)).fetchone())


def delete_look(user_id: int, look_id: int) -> bool:
    with db() as con:
        return con.execute("DELETE FROM looks WHERE id = ? AND user_id = ?", (look_id, user_id)).rowcount > 0
