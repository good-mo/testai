# app/auth/store.py
"""认证数据存储：用户、会话、RSA 密钥对。

内存实现 + 可选的 SQLite 持久化。默认使用内存存储，适合开发环境。
"""

import base64
import hashlib
import os
import secrets
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app import db as _db
from app.core.database import Database
from app.logging_config import get_logger

logger = get_logger(__name__)

# ── 登录防爆破配置 ────────────────────────────────────────────
_LOGIN_MAX_ATTEMPTS = 5          # 窗口内允许的最大失败次数
_LOGIN_LOCK_WINDOW = 300         # 失败计数窗口（秒）
_LOGIN_LOCKOUT_SECONDS = 300     # 触发锁定后的冷却时间（秒）

# 登录失败记录：{username: [attempt_time, ...]}，用于滑动窗口计数。
# 使用进程内内存存储（非持久化），避免写库放大；多进程部署时由负载均衡
# 分摊攻击流量，单实例仍能有效抑制暴力破解。
_login_failures: Dict[str, list] = {}
_login_lockout_until: Dict[str, float] = {}
_login_guard_lock = threading.Lock()

# 会话滑动过期：每次活跃访问将过期时间顺延（30 天无操作才失效）
_SESSION_TTL_SECONDS = 30 * 24 * 3600
# 距过期不足该阈值才续期，避免每次请求都写库
_SESSION_RENEW_THRESHOLD = 24 * 3600


# ── RSA 密钥管理 ────────────────────────────────────────────────
_rsa_private_key: Optional[rsa.RSAPrivateKey] = None
_rsa_public_key_pem: str = ""

# RSA 密钥持久化文件路径（项目根目录下）
_RSA_PRIVATE_KEY_FILE = os.path.join(_db.PROJECT_ROOT, ".rsa_private_key.pem")


def _ensure_rsa_keys() -> None:
    """加载或生成 RSA 密钥对（2048 位，持久化到磁盘）。"""
    global _rsa_private_key, _rsa_public_key_pem
    if _rsa_private_key is not None:
        return

    # 1. 尝试从磁盘加载已有密钥
    if os.path.exists(_RSA_PRIVATE_KEY_FILE):
        try:
            with open(_RSA_PRIVATE_KEY_FILE, "rb") as f:
                _rsa_private_key = serialization.load_pem_private_key(
                    f.read(), password=None
                )
        except Exception:
            logger.warning("RSA 密钥文件损坏，重新生成")
            _rsa_private_key = None

    # 2. 若不存在或加载失败，生成 2048 位新密钥并持久化
    if _rsa_private_key is None:
        _rsa_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem_bytes = _rsa_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        try:
            with open(_RSA_PRIVATE_KEY_FILE, "wb") as f:
                f.write(pem_bytes)
            # 设置文件权限为仅当前用户可读写
            os.chmod(_RSA_PRIVATE_KEY_FILE, 0o600)
        except Exception as e:
            logger.warning("RSA 密钥持久化失败（不影响本次运行）: %s", e)

    # 3. 导出公钥 PEM
    public_key = _rsa_private_key.public_key()
    _rsa_public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def get_rsa_public_key() -> str:
    """返回 RSA 公钥 PEM 字符串（供前端加密密码）。"""
    _ensure_rsa_keys()
    return _rsa_public_key_pem


def rsa_decrypt(encrypted_b64: str) -> str:
    """使用 RSA 私钥解密前端传来的 Base64 密文。"""
    _ensure_rsa_keys()
    try:
        encrypted_bytes = base64.b64decode(encrypted_b64)
        from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
        plaintext = _rsa_private_key.decrypt(
            encrypted_bytes,
            asym_padding.PKCS1v15(),
        )
        return plaintext.decode("utf-8")
    except Exception:
        # 如果解密失败，尝试直接返回（可能是明文）
        return encrypted_b64


# ── 密码哈希（PBKDF2-HMAC-SHA256 加盐慢哈希）────────────────────
_SALT_BYTES = 16
_PBKDF2_ITERATIONS = 100_000


def _password_hash(password: str) -> str:
    """PBKDF2-HMAC-SHA256 加盐慢哈希（替代裸 SHA256）。"""
    salt = secrets.token_bytes(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    # 存储格式: pbkdf2_sha256$iterations$salt_b64$hash_b64
    return "pbkdf2_sha256${}${}${}".format(
        _PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode("utf-8"),
        base64.b64encode(dk).decode("utf-8"),
    )


def _password_verify(password: str, stored_hash: str) -> bool:
    """验证密码与存储的 PBKDF2 哈希是否匹配。

    向后兼容旧格式（裸 SHA256 十六进制字符串）。
    """
    if not stored_hash:
        return False
    # 兼容旧版裸 SHA256 哈希
    if len(stored_hash) == 64 and not stored_hash.startswith("pbkdf2_"):
        try:
            return secrets.compare_digest(
                hashlib.sha256(password.encode("utf-8")).hexdigest(),
                stored_hash,
            )
        except Exception:
            return False
    try:
        algo, iterations_str, salt_b64, hash_b64 = stored_hash.split("$")
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iterations_str)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return secrets.compare_digest(dk, expected)
    except Exception:
        return False


# ── 数据存储类 ──────────────────────────────────────────────────
class AuthStore:
    """用户与会话存储。

    使用 SQLite 持久化（users 表 + sessions 表），支持多进程安全。
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or _db.db_path(_db.AUTH_DB)
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库表结构。"""
        conn = Database.get_conn("auth.db")
        # WAL 模式下开启 synchronous=NORMAL：降低会话写入 fsync 开销，
        # 同时保持崩溃安全（WAL+NORMAL 对应用崩溃仍安全）
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                email TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                avatar TEXT DEFAULT '',
                name TEXT DEFAULT '',
                role TEXT DEFAULT 'user',
                enable INTEGER DEFAULT 1,
                create_time REAL,
                update_time REAL,
                create_user TEXT DEFAULT 'system',
                update_user TEXT DEFAULT 'system',
                deleted INTEGER DEFAULT 0,
                language TEXT DEFAULT 'zh-CN',
                last_organization_id TEXT DEFAULT '',
                last_project_id TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                csrf_token TEXT NOT NULL,
                create_time REAL,
                expire_time REAL,
                ip TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_local_configs (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                user_url TEXT DEFAULT '',
                type TEXT DEFAULT 'API',
                enable INTEGER DEFAULT 0,
                create_time REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                access_key TEXT DEFAULT '',
                secret_key TEXT DEFAULT '',
                description TEXT DEFAULT '',
                enable INTEGER DEFAULT 1,
                forever INTEGER DEFAULT 0,
                expire_time REAL DEFAULT 0,
                create_time REAL
            )
        """)
        # 确保默认管理员用户存在
        self._ensure_default_users(conn)

    def _ensure_default_users(self, conn: sqlite3.Connection) -> None:
        """创建默认用户。"""
        now = time.time()
        # 默认管理员
        cursor = conn.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("admin",))
        if cursor.fetchone()[0] == 0:
            conn.execute(
                """INSERT INTO users (id, username, password_hash, name, role, email,
                   create_time, update_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), "admin", _password_hash("admin123"), "管理员", "admin",
                 "admin@example.com", now, now),
            )
        # 默认测试用户
        cursor = conn.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("demo",))
        if cursor.fetchone()[0] == 0:
            conn.execute(
                """INSERT INTO users (id, username, password_hash, name, role, email,
                   create_time, update_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), "demo", _password_hash("demo"), "演示用户", "user",
                 "demo@example.com", now, now),
            )

    # ── 登录防爆破 ────────────────────────────────────────
    def _is_login_locked(self, username: str) -> bool:
        """判断用户名当前是否处于锁定状态。"""
        now = time.time()
        with _login_guard_lock:
            until = _login_lockout_until.get(username, 0)
            if until and now < until:
                return True
            if until and now >= until:
                # 冷却结束，重置计数
                _login_lockout_until.pop(username, None)
                _login_failures.pop(username, None)
        return False

    def _register_login_failure(self, username: str) -> None:
        """记录一次登录失败；达到阈值则触发锁定。"""
        now = time.time()
        with _login_guard_lock:
            attempts = [t for t in _login_failures.get(username, [])
                        if now - t < _LOGIN_LOCK_WINDOW]
            attempts.append(now)
            _login_failures[username] = attempts
            if len(attempts) >= _LOGIN_MAX_ATTEMPTS:
                _login_lockout_until[username] = now + _LOGIN_LOCKOUT_SECONDS
                logger.warning(
                    "登录失败次数过多，账号 %s 已锁定 %d 秒",
                    username, _LOGIN_LOCKOUT_SECONDS,
                )

    def _register_login_success(self, username: str) -> None:
        """登录成功后清除失败计数与锁定。"""
        with _login_guard_lock:
            _login_failures.pop(username, None)
            _login_lockout_until.pop(username, None)

    def login_lock_remaining(self, username: str) -> int:
        """返回当前锁定剩余秒数（0 表示未锁定）。"""
        if self._is_login_locked(username):
            with _login_guard_lock:
                return max(0, int(_login_lockout_until.get(username, 0) - time.time()))
        return 0

    # ── 用户管理 ─────────────────────────────────────────
    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """验证用户名密码，成功返回用户信息，失败返回 None。

        集成登录防爆破：
          - 锁定期间直接返回 None（不再做密码校验，避免放大攻击成本）；
          - 校验失败记录失败计数，达阈值触发锁定；
          - 校验成功清除历史失败计数。
        """
        if self._is_login_locked(username):
            return None
        conn = Database.get_conn("auth.db")
        cursor = conn.execute(
            "SELECT * FROM users WHERE username = ? AND deleted = 0 AND enable = 1",
            (username,),
        )
        row = cursor.fetchone()
        if not row:
            self._register_login_failure(username)
            return None
        cols = [d[0] for d in cursor.description]
        user = dict(zip(cols, row, strict=False))
        if not _password_verify(password, user["password_hash"]):
            self._register_login_failure(username)
            return None
        # 清除密码哈希
        user.pop("password_hash", None)
        self._register_login_success(username)
        return user

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """按 ID 获取用户。"""
        conn = Database.get_conn("auth.db")
        cursor = conn.execute(
            "SELECT * FROM users WHERE id = ? AND deleted = 0", (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        user = dict(zip(cols, row, strict=False))
        user.pop("password_hash", None)
        return user

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """按用户名获取用户。"""
        conn = Database.get_conn("auth.db")
        cursor = conn.execute(
            "SELECT * FROM users WHERE username = ? AND deleted = 0", (username,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        user = dict(zip(cols, row, strict=False))
        user.pop("password_hash", None)
        return user

    def list_users(self) -> List[Dict[str, Any]]:
        """列出所有用户（不含密码）。"""
        conn = Database.get_conn("auth.db")
        cursor = conn.execute(
            "SELECT * FROM users WHERE deleted = 0 ORDER BY create_time DESC"
        )
        users = []
        for row in cursor.fetchall():
            cols = [d[0] for d in cursor.description]
            user = dict(zip(cols, row, strict=False))
            user.pop("password_hash", None)
            users.append(user)
        return users

    def create_user(self, username: str, password: str, **kwargs) -> Dict[str, Any]:
        """创建新用户。"""
        user_id = str(uuid.uuid4())
        now = time.time()
        conn = Database.get_conn("auth.db")
        conn.execute(
            """INSERT INTO users (id, username, password_hash, name, email, phone,
               role, create_time, update_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, username, _password_hash(password),
             kwargs.get("name", username), kwargs.get("email", ""),
             kwargs.get("phone", ""), kwargs.get("role", "user"), now, now),
        )
        return self.get_user_by_id(user_id) or {}

    def update_user(self, user_id: str, **fields) -> Optional[Dict[str, Any]]:
        """更新用户信息。"""
        allowed = {"email", "phone", "avatar", "name", "language", "role",
                   "last_organization_id", "last_project_id"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get_user_by_id(user_id)
        updates["update_time"] = time.time()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [user_id]
        conn = Database.get_conn("auth.db")
        conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        return self.get_user_by_id(user_id)

    def delete_user(self, user_id: str) -> bool:
        """软删除用户。"""
        conn = Database.get_conn("auth.db")
        cursor = conn.execute(
            "UPDATE users SET deleted = 1, update_time = ? WHERE id = ?",
            (time.time(), user_id),
        )
        return cursor.rowcount > 0

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """修改密码。"""
        conn = Database.get_conn("auth.db")
        cursor = conn.execute(
            "SELECT password_hash FROM users WHERE id = ?", (user_id,)
        )
        row = cursor.fetchone()
        if not row or not _password_verify(old_password, row[0]):
            return False
        conn.execute(
            "UPDATE users SET password_hash = ?, update_time = ? WHERE id = ?",
            (_password_hash(new_password), time.time(), user_id),
        )
        return True

    def set_user_enabled(self, user_id: str, enable: bool) -> bool:
        """启用/禁用用户。"""
        conn = Database.get_conn("auth.db")
        cursor = conn.execute(
            "UPDATE users SET enable = ?, update_time = ? WHERE id = ?",
            (1 if enable else 0, time.time(), user_id),
        )
        return cursor.rowcount > 0

    def reset_password(self, user_id: str, new_password: str) -> bool:
        """重置用户密码。"""
        conn = Database.get_conn("auth.db")
        cursor = conn.execute(
            "UPDATE users SET password_hash = ?, update_time = ? WHERE id = ?",
            (_password_hash(new_password), time.time(), user_id),
        )
        return cursor.rowcount > 0

    # ── 会话管理 ─────────────────────────────────────────
    def create_session(self, user_id: str, ip: str = "") -> Dict[str, str]:
        """创建会话，返回 session_id 和 csrf_token。"""
        session_id = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        now = time.time()
        expire = now + _SESSION_TTL_SECONDS  # 30 天滑动有效期
        conn = Database.get_conn("auth.db")
        conn.execute(
            """INSERT INTO sessions (id, user_id, csrf_token, create_time, expire_time, ip)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, user_id, csrf_token, now, expire, ip),
        )
        return {"sessionId": session_id, "csrfToken": csrf_token}

    def get_session_user(self, session_id: str) -> Optional[Dict[str, Any]]:
        """通过会话 ID 获取用户（含滑动续期）。

        会话有效期内每次活跃访问都会顺延过期时间：距过期不足
        _SESSION_RENEW_THRESHOLD 时才续期，避免每次请求都写库。
        """
        if not session_id:
            return None
        now = time.time()
        conn = Database.get_conn("auth.db")
        cursor = conn.execute(
            """SELECT s.*, u.* FROM sessions s
               JOIN users u ON s.user_id = u.id
               WHERE s.id = ? AND s.expire_time > ? AND u.deleted = 0""",
            (session_id, now),
        )
        row = cursor.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        # 合并 sessions 和 users 的列（去掉重复）
        data = dict(zip(cols, row, strict=False))
        expire_time = data.get("expire_time") or 0
        # 滑动续期：距过期不足阈值时顺延 TTL
        if expire_time and expire_time - now < _SESSION_RENEW_THRESHOLD:
            new_expire = now + _SESSION_TTL_SECONDS
            conn.execute(
                "UPDATE sessions SET expire_time = ? WHERE id = ?",
                (new_expire, session_id),
            )
            data["expire_time"] = new_expire
        user = self._extract_user_from_join(data)
        # 附带会话元数据（csrf_token / ip），供中间件做 CSRF 校验
        user["_csrf_token"] = data.get("csrf_token", "")
        user["_session_id"] = data.get("id", "")
        user["_session_ip"] = data.get("ip", "")
        return user

    def _extract_user_from_join(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """从 JOIN 结果中提取用户字段。"""
        user = {
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
        # 尝试获取 session 的 expire_time 和 create_time
        user["session_expire_time"] = data.get("expire_time", 0)
        user["session_create_time"] = data.get("create_time", 0)
        return user

    def delete_session(self, session_id: str) -> bool:
        """删除会话（登出）。"""
        conn = Database.get_conn("auth.db")
        cursor = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return cursor.rowcount > 0

    def cleanup_expired_sessions(self) -> None:
        """清理过期会话。"""
        conn = Database.get_conn("auth.db")
        conn.execute("DELETE FROM sessions WHERE expire_time < ?", (time.time(),))

    def revoke_user_sessions(self, user_id: str) -> int:
        """吊销指定用户的全部会话（如改密/重置密码后调用）。

        Returns:
            被吊销的会话数量。
        """
        conn = Database.get_conn("auth.db")
        cursor = conn.execute(
            "DELETE FROM sessions WHERE user_id = ?", (user_id,)
        )
        return cursor.rowcount

    # ── 本地执行配置 ─────────────────────────────────────
    def get_local_configs(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的本地执行配置。"""
        conn = Database.get_conn("auth.db")
        cursor = conn.execute(
            "SELECT * FROM user_local_configs WHERE user_id = ?", (user_id,)
        )
        rows = cursor.fetchall()
        return [dict(zip([d[0] for d in cursor.description], r, strict=False)) for r in rows]

    def add_local_config(self, user_id: str, user_url: str, cfg_type: str = "API") -> Dict[str, Any]:
        """添加本地执行配置。"""
        cfg_id = str(uuid.uuid4())
        conn = Database.get_conn("auth.db")
        conn.execute(
            """INSERT INTO user_local_configs (id, user_id, user_url, type, enable, create_time)
               VALUES (?, ?, ?, ?, 0, ?)""",
            (cfg_id, user_id, user_url, cfg_type, time.time()),
        )
        return {"id": cfg_id, "user_url": user_url, "type": cfg_type, "enable": False}

    def update_local_config(self, cfg_id: str, user_url: str) -> bool:
        """更新本地执行配置。"""
        conn = Database.get_conn("auth.db")
        cursor = conn.execute(
            "UPDATE user_local_configs SET user_url = ? WHERE id = ?",
            (user_url, cfg_id),
        )
        return cursor.rowcount > 0

    def toggle_local_config(self, cfg_id: str, enable: bool) -> bool:
        """启用/禁用本地执行配置。"""
        conn = Database.get_conn("auth.db")
        cursor = conn.execute(
            "UPDATE user_local_configs SET enable = ? WHERE id = ?",
            (1 if enable else 0, cfg_id),
        )
        return cursor.rowcount > 0

    # ── API Key 管理 ────────────────────────────────────
    def list_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户 API Key 列表。"""
        conn = Database.get_conn("auth.db")
        cursor = conn.execute(
            "SELECT * FROM api_keys WHERE user_id = ?", (user_id,)
        )
        rows = cursor.fetchall()
        keys = []
        for r in rows:
            item = dict(zip([d[0] for d in cursor.description], r, strict=False))
            item.pop("secret_key", None)  # 不返回 secret
            keys.append(item)
        return keys

    def create_api_key(self, user_id: str, description: str = "", forever: bool = False,
                       expire_time: int = 0) -> Dict[str, Any]:
        """创建 API Key。"""
        key_id = str(uuid.uuid4())
        access_key = f"ak_{secrets.token_hex(8)}"
        secret_key = f"sk_{secrets.token_hex(16)}"
        conn = Database.get_conn("auth.db")
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
        """启用/禁用 API Key。"""
        conn = Database.get_conn("auth.db")
        cursor = conn.execute(
            "UPDATE api_keys SET enable = ? WHERE id = ?",
            (1 if enable else 0, key_id),
        )
        return cursor.rowcount > 0

    def delete_api_key(self, key_id: str) -> bool:
        """删除 API Key。"""
        conn = Database.get_conn("auth.db")
        cursor = conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
        return cursor.rowcount > 0


# ── 全局单例 ───────────────────────────────────────────────────
auth_store = AuthStore()
