# app/repositories/auth_repo.py
"""认证数据访问层（Phase 3 重构 · 4 层对齐）。

本层是认证域用户 / 会话 / API Key / 本地配置的数据访问唯一入口，
已从「委托旧 app.auth.store.AuthStore」下沉为**仓库内直接 SQLite 实现**
（auth.db → 统一路由至 tga.db），消除 Repository 空壳化。

纯数据访问（users / sessions / user_local_configs / api_keys 的 CRUD）
均在仓库内直连 SQL，输出形态与旧 AuthStore 完全一致（零回归由
tests/test_auth_repo_alignment.py 等对齐用例保证）。

下沉边界：本层只负责 auth.db 的纯数据访问（CRUD / 查询）；登录防爆破
计数 / RSA 密钥 / 密码哈希 / 会话滑动续期阈值等既有安全工具仍以
app.auth.store 为单一权威来源，此处仅按需懒代理，避免同一安全语义出现
两套实现漂移。
"""
import secrets
import sqlite3
import time
import uuid
from typing import Optional

from app.core.database import Database
from app.logging_config import get_logger

logger = get_logger(__name__)

# ── 认证安全工具（懒代理 app.auth.store 单一来源，避免双实现漂移）──
# 密码哈希 / RSA / 会话滑动续期阈值 / 登录防爆破均为跨数据访问的既有安全
# 工具，权威实现沉淀于 app.auth.store。此处仅按需懒代理，不重复实现，
# 保证下沉后的 auth_repo 与旧层在相同物理表上使用同一套安全语义。


def _sec_store():
    """懒加载 app.auth.store 模块（认证安全工具权威来源）。"""
    import app.auth.store as _m
    return _m


def _session_ttl() -> int:
    return _sec_store()._SESSION_TTL_SECONDS


def _session_renew_threshold() -> int:
    return _sec_store()._SESSION_RENEW_THRESHOLD


def _password_hash(password: str) -> str:
    return _sec_store()._password_hash(password)


def _password_verify(password: str, stored_hash: str) -> bool:
    return _sec_store()._password_verify(password, stored_hash)


def _rsa_public_key() -> str:
    return _sec_store().get_rsa_public_key()


def _rsa_decrypt(data: str) -> str:
    return _sec_store().rsa_decrypt(data)


# ── 登录防爆破（共享状态：与 app.auth.store 同一模块级状态）────
def _guard_store():
    """懒加载共享 AuthStore 单例（登录防爆破状态与 store 一致）。"""
    from app.auth.store import auth_store as _auth_store
    return _auth_store


def _guard_lockout_remaining(username: str) -> int:
    return _guard_store().login_lock_remaining(username)


def _guard_locked(username: str) -> bool:
    return _guard_store()._is_login_locked(username)


def _guard_failure(username: str) -> None:
    _guard_store()._register_login_failure(username)


def _guard_success(username: str) -> None:
    _guard_store()._register_login_success(username)


# ── 数据访问仓库 ───────────────────────────────────────────
class AuthRepo:
    """认证数据访问仓库（用户 / 会话 / API Key / 本地配置）。

    认证域唯一数据访问出口：直接以 auth.db（统一路由 tga.db）落库，
    不再委托旧 app.auth.store。对外暴露与旧 AuthStore 完全一致的
    实例方法签名，保证上层（service / router / 旧兼容层）零改动。
    """

    db_name = "auth.db"

    _schema_ensured = False

    def _conn(self) -> sqlite3.Connection:
        """获取 auth.db 连接；首次访问懒触发幂等建表。

        表 DDL 权威来源为 app.auth.store（AuthStore 单例导入即建表）。
        此处懒导入避免 auth_repo 在模块加载期导入 app.auth.store 触发
        app.auth.__init__ → router → auth_service 的循环导入。
        """
        if not type(self)._schema_ensured:
            import app.auth.store  # noqa: F401  触发表结构初始化
            type(self)._schema_ensured = True
        return Database.get_conn(self.db_name)

    def __init__(self):
        # 建表延迟到首次数据访问（_conn），规避模块加载期循环导入
        pass

    # ── 行 → dict 工具 ──────────────────────────────────
    @staticmethod
    def _row_to_user(row, desc) -> dict:
        user = dict(zip([d[0] for d in desc], row, strict=False))
        user.pop("password_hash", None)
        return user

    # ── RSA ──────────────────────────────────────────────
    def get_rsa_public_key(self) -> str:
        return _rsa_public_key()

    def rsa_decrypt(self, data: str) -> str:
        return _rsa_decrypt(data)

    def login_lock_remaining(self, username: str) -> int:
        return _guard_lockout_remaining(username)

    # ── 认证 ─────────────────────────────────────────────
    def authenticate(self, username: str, password: str) -> Optional[dict]:
        """验证用户名密码，成功返回用户信息，失败返回 None。"""
        if _guard_locked(username):
            return None
        conn = self._conn()
        cursor = conn.execute(
            "SELECT * FROM users WHERE username = ? AND deleted = 0 AND enable = 1",
            (username,),
        )
        row = cursor.fetchone()
        if not row:
            _guard_failure(username)
            return None
        data = dict(row)
        if not _password_verify(password, data.get("password_hash") or ""):
            _guard_failure(username)
            return None
        data.pop("password_hash", None)
        _guard_success(username)
        return data

    def create_session(self, user_id: str, ip: str = "") -> dict:
        session_id = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        now = time.time()
        expire = now + _session_ttl()
        conn = self._conn()
        conn.execute(
            """INSERT INTO sessions (id, user_id, csrf_token, create_time, expire_time, ip)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, user_id, csrf_token, now, expire, ip),
        )
        return {"sessionId": session_id, "csrfToken": csrf_token}

    def get_session_user(self, token: str) -> Optional[dict]:
        if not token:
            return None
        now = time.time()
        conn = self._conn()
        cursor = conn.execute(
            """SELECT s.*, u.* FROM sessions s
               JOIN users u ON s.user_id = u.id
               WHERE s.id = ? AND s.expire_time > ? AND u.deleted = 0""",
            (token, now),
        )
        row = cursor.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        data = dict(zip(cols, row, strict=False))
        expire_time = data.get("expire_time") or 0
        if expire_time and expire_time - now < _session_renew_threshold():
            new_expire = now + _session_ttl()
            conn.execute(
                "UPDATE sessions SET expire_time = ? WHERE id = ?",
                (new_expire, token),
            )
            data["expire_time"] = new_expire
        user = self._extract_user_from_join(data)
        user["_csrf_token"] = data.get("csrf_token", "")
        user["_session_id"] = data.get("id", "")
        user["_session_ip"] = data.get("ip", "")
        return user

    def _extract_user_from_join(self, data: dict) -> dict:
        return {
            "id": data.get("user_id", ""),
            "username": data.get("username", ""),
            "name": data.get("name", ""),
            "email": data.get("email", ""),
            "phone": data.get("phone", ""),
            "avatar": data.get("avatar", ""),
            "role": data.get("role", "user"),
            "enable": data.get("enable", 1),
            "create_time": data.get("create_time", 0),
            "update_time": data.get("update_time", 0),
            "language": data.get("language", "zh-CN"),
            "last_organization_id": data.get("last_organization_id", ""),
            "last_project_id": data.get("last_project_id", ""),
        }

    def delete_session(self, token: str) -> bool:
        cursor = self._conn().execute(
            "DELETE FROM sessions WHERE id = ?", (token,)
        )
        return cursor.rowcount > 0

    def cleanup_expired_sessions(self) -> int:
        cursor = self._conn().execute(
            "DELETE FROM sessions WHERE expire_time < ?", (time.time(),)
        )
        return cursor.rowcount

    def revoke_user_sessions(self, user_id: str) -> int:
        cursor = self._conn().execute(
            "DELETE FROM sessions WHERE user_id = ?", (user_id,)
        )
        return cursor.rowcount

    # ── 用户管理 ─────────────────────────────────────────
    def list_users(self, search: str = "", limit: int = 50,
                   offset: int = 0) -> list:
        conn = self._conn()
        cursor = conn.execute(
            "SELECT * FROM users WHERE deleted = 0 ORDER BY create_time DESC"
        )
        users = [self._row_to_user(r, cursor.description) for r in cursor.fetchall()]
        if search:
            s = str(search).lower()
            users = [u for u in users if s in str(u.get("username", "")).lower()
                     or s in str(u.get("name", "")).lower()
                     or s in str(u.get("email", "")).lower()]
        return users[int(offset):int(offset) + int(limit)]

    def create_user(self, username: str, password: str, **kwargs) -> dict:
        user_id = str(uuid.uuid4())
        now = time.time()
        conn = self._conn()
        conn.execute(
            """INSERT INTO users (id, username, password_hash, name, email, phone,
               role, create_time, update_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, username, _password_hash(password),
             kwargs.get("name", username), kwargs.get("email", ""),
             kwargs.get("phone", ""), kwargs.get("role", "user"), now, now),
        )
        return self.get_user_by_id(user_id) or {}

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        conn = self._conn()
        cursor = conn.execute(
            "SELECT * FROM users WHERE id = ? AND deleted = 0", (user_id,)
        )
        row = cursor.fetchone()
        return self._row_to_user(row, cursor.description) if row else None

    def get_user_by_username(self, username: str) -> Optional[dict]:
        conn = self._conn()
        cursor = conn.execute(
            "SELECT * FROM users WHERE username = ? AND deleted = 0", (username,)
        )
        row = cursor.fetchone()
        return self._row_to_user(row, cursor.description) if row else None

    def update_user(self, user_id: str, **kwargs) -> Optional[dict]:
        allowed = {"email", "phone", "avatar", "name", "language", "role",
                   "last_organization_id", "last_project_id"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return self.get_user_by_id(user_id)
        updates["update_time"] = time.time()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [user_id]
        conn = self._conn()
        conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        return self.get_user_by_id(user_id)

    def delete_user(self, user_id: str) -> bool:
        cursor = self._conn().execute(
            "UPDATE users SET deleted = 1, update_time = ? WHERE id = ?",
            (time.time(), user_id),
        )
        return cursor.rowcount > 0

    def change_password(self, user_id: str, old_password: str,
                        new_password: str) -> bool:
        conn = self._conn()
        row = conn.execute(
            "SELECT password_hash FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row or not _password_verify(old_password, row["password_hash"]):
            return False
        conn.execute(
            "UPDATE users SET password_hash = ?, update_time = ? WHERE id = ?",
            (_password_hash(new_password), time.time(), user_id),
        )
        return True

    def set_user_enabled(self, user_id: str, enabled: bool) -> bool:
        cursor = self._conn().execute(
            "UPDATE users SET enable = ?, update_time = ? WHERE id = ?",
            (1 if enabled else 0, time.time(), user_id),
        )
        return cursor.rowcount > 0

    def reset_password(self, user_id: str, new_password: str) -> bool:
        cursor = self._conn().execute(
            "UPDATE users SET password_hash = ?, update_time = ? WHERE id = ?",
            (_password_hash(new_password), time.time(), user_id),
        )
        return cursor.rowcount > 0

    # ── 本地执行配置 ─────────────────────────────────────
    def get_local_configs(self, user_id: str) -> list:
        conn = self._conn()
        cursor = conn.execute(
            "SELECT * FROM user_local_configs WHERE user_id = ?", (user_id,)
        )
        return [dict(zip([d[0] for d in cursor.description], r, strict=False))
                for r in cursor.fetchall()]

    def add_local_config(self, user_id: str, user_url: str,
                         cfg_type: str = "API") -> dict:
        cfg_id = str(uuid.uuid4())
        conn = self._conn()
        conn.execute(
            """INSERT INTO user_local_configs (id, user_id, user_url, type, enable, create_time)
               VALUES (?, ?, ?, ?, 0, ?)""",
            (cfg_id, user_id, user_url, cfg_type, time.time()),
        )
        return {"id": cfg_id, "user_url": user_url, "type": cfg_type, "enable": False}

    def update_local_config(self, cfg_id: str, user_url: str) -> bool:
        cursor = self._conn().execute(
            "UPDATE user_local_configs SET user_url = ? WHERE id = ?",
            (user_url, cfg_id),
        )
        return cursor.rowcount > 0

    def toggle_local_config(self, cfg_id: str, enable: bool) -> bool:
        cursor = self._conn().execute(
            "UPDATE user_local_configs SET enable = ? WHERE id = ?",
            (1 if enable else 0, cfg_id),
        )
        return cursor.rowcount > 0

    # ── API Key 管理 ────────────────────────────────────
    def list_api_keys(self, user_id: str = "") -> list:
        conn = self._conn()
        if user_id:
            cursor = conn.execute(
                "SELECT * FROM api_keys WHERE user_id = ?", (user_id,)
            )
        else:
            cursor = conn.execute("SELECT * FROM api_keys")
        keys = []
        for r in cursor.fetchall():
            item = dict(zip([d[0] for d in cursor.description], r, strict=False))
            item.pop("secret_key", None)
            keys.append(item)
        return keys

    def create_api_key(self, user_id: str, description: str = "",
                       forever: bool = False, expire_time: int = 0) -> dict:
        key_id = str(uuid.uuid4())
        access_key = f"ak_{secrets.token_hex(8)}"
        secret_key = f"sk_{secrets.token_hex(16)}"
        conn = self._conn()
        conn.execute(
            """INSERT INTO api_keys (id, user_id, access_key, secret_key, description,
               enable, forever, expire_time, create_time)
               VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)""",
            (key_id, user_id, access_key, secret_key, description,
             forever, expire_time, time.time()),
        )
        return {"id": key_id, "access_key": access_key, "secret_key": secret_key,
                "description": description, "enable": True, "forever": forever}

    def toggle_api_key(self, key_id: str, enable: bool) -> bool:
        cursor = self._conn().execute(
            "UPDATE api_keys SET enable = ? WHERE id = ?",
            (1 if enable else 0, key_id),
        )
        return cursor.rowcount > 0

    def delete_api_key(self, key_id: str) -> bool:
        cursor = self._conn().execute(
            "DELETE FROM api_keys WHERE id = ?", (key_id,)
        )
        return cursor.rowcount > 0


# 兼容类方法调用（部分上层代码按实例使用）
auth_repo = AuthRepo()
