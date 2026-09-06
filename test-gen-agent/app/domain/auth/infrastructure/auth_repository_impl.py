"""认证上下文的 SQLite 仓储适配器。"""

from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from typing import Optional

from app.core.database import Database


class AuthRepositoryImpl:
    """认证聚合的持久化端口实现。"""

    db_name = "tga.db"

    def __init__(self) -> None:
        self._ensure_schema()

    @staticmethod
    def _hash(password: str) -> str:
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), 100_000
        ).hex()
        return f"pbkdf2_sha256$100000${salt}${digest}"

    @staticmethod
    def _verify(password: str, stored: str) -> bool:
        try:
            algorithm, iterations, salt, expected = stored.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            actual = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), bytes.fromhex(salt), int(iterations)
            ).hex()
            return secrets.compare_digest(actual, expected)
        except (TypeError, ValueError):
            return False

    @classmethod
    def _ensure_schema(cls) -> None:
        conn = Database.get_conn(cls.db_name)
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS auth_users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT 'user',
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS auth_sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                csrf_token TEXT NOT NULL,
                expires_at REAL NOT NULL
            );
            """
        )
        row = conn.execute(
            "SELECT id FROM auth_users WHERE username = ?", ("admin",)
        ).fetchone()
        if row is None:
            now = time.time()
            conn.execute(
                "INSERT INTO auth_users "
                "(id, username, password_hash, name, role, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), "admin", cls._hash("admin123"), "管理员", "admin", now, now),
            )
        conn.commit()

    @staticmethod
    def _user(row) -> Optional[dict]:
        return dict(row) if row else None

    def authenticate(self, username: str, password: str) -> Optional[dict]:
        row = Database.get_conn(self.db_name).execute(
            "SELECT * FROM auth_users WHERE username = ? AND enabled = 1", (username,)
        ).fetchone()
        return self._user(row) if row and self._verify(password, row["password_hash"]) else None

    def create_session(self, user_id: str, **kwargs) -> dict:
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "INSERT INTO auth_sessions(token, user_id, csrf_token, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, csrf, time.time() + 30 * 24 * 3600),
        )
        conn.commit()
        return {"sessionId": token, "token": token, "csrfToken": csrf}

    def get_session_user(self, token: str) -> Optional[dict]:
        row = Database.get_conn(self.db_name).execute(
            "SELECT u.*, s.csrf_token FROM auth_sessions s "
            "JOIN auth_users u ON u.id = s.user_id "
            "WHERE s.token = ? AND s.expires_at > ? AND u.enabled = 1",
            (token, time.time()),
        ).fetchone()
        user = self._user(row)
        if user:
            user["_csrf_token"] = user.pop("csrf_token", "")
        return user

    def delete_session(self, token: str) -> bool:
        conn = Database.get_conn(self.db_name)
        cur = conn.execute("DELETE FROM auth_sessions WHERE token = ?", (token,))
        conn.commit()
        return cur.rowcount > 0

    def list_users(self, search: str = "", limit: int = 50) -> list:
        rows = Database.get_conn(self.db_name).execute(
            "SELECT * FROM auth_users WHERE username LIKE ? OR name LIKE ? "
            "ORDER BY created_at DESC LIMIT ?",
            (f"%{search}%", f"%{search}%", max(1, limit)),
        ).fetchall()
        return [dict(row) for row in rows]

    def create_user(self, username: str, password: str, **kwargs) -> dict:
        now = time.time()
        user = {
            "id": str(uuid.uuid4()), "username": username,
            "password_hash": self._hash(password), "name": kwargs.get("name", username),
            "email": kwargs.get("email", ""), "phone": kwargs.get("phone", ""),
            "role": kwargs.get("role", "user"), "enabled": 1,
            "created_at": now, "updated_at": now,
        }
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "INSERT INTO auth_users "
            "(id, username, password_hash, name, email, phone, role, enabled, created_at, updated_at) "
            "VALUES (:id, :username, :password_hash, :name, :email, :phone, :role, :enabled, :created_at, :updated_at)",
            user,
        )
        conn.commit()
        return user

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        row = Database.get_conn(self.db_name).execute(
            "SELECT * FROM auth_users WHERE id = ?", (user_id,)
        ).fetchone()
        return self._user(row)

    def update_user(self, user_id: str, **kwargs) -> Optional[dict]:
        allowed = {k: v for k, v in kwargs.items() if k in {"name", "email", "phone", "role"}}
        if not allowed:
            return self.get_user_by_id(user_id)
        allowed["updated_at"] = time.time()
        assignments = ", ".join(f"{key} = :{key}" for key in allowed)
        allowed["id"] = user_id
        conn = Database.get_conn(self.db_name)
        conn.execute(f"UPDATE auth_users SET {assignments} WHERE id = :id", allowed)
        conn.commit()
        return self.get_user_by_id(user_id)

    def delete_user(self, user_id: str) -> bool:
        conn = Database.get_conn(self.db_name)
        cur = conn.execute("DELETE FROM auth_users WHERE id = ?", (user_id,))
        conn.commit()
        return cur.rowcount > 0

    def reset_password(self, user_id: str, new_password: str) -> bool:
        conn = Database.get_conn(self.db_name)
        cur = conn.execute(
            "UPDATE auth_users SET password_hash = ?, updated_at = ? WHERE id = ?",
            (self._hash(new_password), time.time(), user_id),
        )
        conn.commit()
        return cur.rowcount > 0

    def set_user_enabled(self, user_id: str, enabled: bool) -> bool:
        conn = Database.get_conn(self.db_name)
        cur = conn.execute(
            "UPDATE auth_users SET enabled = ?, updated_at = ? WHERE id = ?",
            (int(enabled), time.time(), user_id),
        )
        conn.commit()
        return cur.rowcount > 0


_auth_repository = AuthRepositoryImpl()
auth_repository = _auth_repository
__all__ = ["AuthRepositoryImpl", "auth_repository"]
