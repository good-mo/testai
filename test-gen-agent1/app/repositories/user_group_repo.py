# app/repositories/user_group_repo.py
"""用户组（角色）数据访问层（Phase 3 重构 · 4 层对齐）。

承接 `app.auth.user_groups` 的用户组/角色管理数据层：
  - 用户组 CRUD（全局 SYSTEM / 组织 ORGANIZATION / 项目 PROJECT）
  - 用户组成员关联
  - 用户组权限配置

本层是用户组表的唯一 DB 访问入口，输出字段形态与旧 `app.auth.user_groups`
完全一致（createTime/updateTime 毫秒、internal 布尔化、scopeId/type 等），
确保 Service 与 Router 可直接消费、零回归。

验收口径：本层不改动任何路由行为，并与旧层在相同数据库上的输出逐条一致。
"""
import json
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.database import Database
from app.logging_config import get_logger
from app.repositories.base import BaseRepo

logger = get_logger(__name__)


# 内置用户组定义（不可删除/修改 internal 字段）
BUILTIN_GLOBAL_GROUPS = [
    {
        "id": "admin", "name": "管理员", "description": "系统管理员",
        "internal": True, "type": "SYSTEM", "scopeId": "global",
        "createTime": 0, "updateTime": 0, "createUser": "admin", "pos": 1,
    },
    {
        "id": "member", "name": "成员", "description": "系统成员",
        "internal": True, "type": "SYSTEM", "scopeId": "global",
        "createTime": 0, "updateTime": 0, "createUser": "admin", "pos": 2,
    },
    {
        "id": "read-only", "name": "只读成员", "description": "只读成员",
        "internal": True, "type": "SYSTEM", "scopeId": "global",
        "createTime": 0, "updateTime": 0, "createUser": "admin", "pos": 3,
    },
]

# 内置组织/项目用户组
BUILTIN_ORG_GROUPS = [
    {
        "id": "org-admin", "name": "组织管理员", "description": "组织管理员",
        "internal": True, "type": "ORGANIZATION", "scopeId": "organization",
        "createTime": 0, "updateTime": 0, "createUser": "admin", "pos": 1,
    },
    {
        "id": "org-member", "name": "组织成员", "description": "组织成员",
        "internal": True, "type": "ORGANIZATION", "scopeId": "organization",
        "createTime": 0, "updateTime": 0, "createUser": "admin", "pos": 2,
    },
    {
        "id": "project-admin", "name": "项目管理员", "description": "项目管理员",
        "internal": True, "type": "PROJECT", "scopeId": "",
        "createTime": 0, "updateTime": 0, "createUser": "admin", "pos": 1,
    },
    {
        "id": "project-member", "name": "项目成员", "description": "项目成员",
        "internal": True, "type": "PROJECT", "scopeId": "",
        "createTime": 0, "updateTime": 0, "createUser": "admin", "pos": 2,
    },
    {
        "id": "project-readonly", "name": "项目只读成员", "description": "项目只读成员",
        "internal": True, "type": "PROJECT", "scopeId": "",
        "createTime": 0, "updateTime": 0, "createUser": "admin", "pos": 3,
    },
]

# 内置权限配置（用户组 id -> 权限 key 列表）
BUILTIN_PERMISSIONS: Dict[str, List[str]] = {}


class UserGroupRepo(BaseRepo):
    """用户组/角色数据访问层。"""

    db_name = "tga.db"
    table_name = "user_groups"

    # ── 表结构初始化 ────────────────────────────────────
    @classmethod
    def init_tables(cls) -> None:
        """初始化用户组相关表结构。"""
        conn = Database.get_conn(cls.db_name)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_groups (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    internal INTEGER DEFAULT 0,
                    type TEXT DEFAULT 'SYSTEM',      -- SYSTEM/ORGANIZATION/PROJECT
                    scope_id TEXT DEFAULT '',
                    pos INTEGER DEFAULT 99,
                    create_time REAL,
                    update_time REAL,
                    create_user TEXT DEFAULT 'admin',
                    update_user TEXT DEFAULT 'admin'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_groups_type ON user_groups(type)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_group_members (
                    id TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    username TEXT DEFAULT '',
                    name TEXT DEFAULT '',
                    email TEXT DEFAULT '',
                    type TEXT DEFAULT 'SYSTEM',
                    scope_id TEXT DEFAULT '',
                    create_time REAL,
                    update_time REAL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ugm_group ON user_group_members(group_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ugm_user ON user_group_members(user_id)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_group_permissions (
                    group_id TEXT PRIMARY KEY,
                    permissions TEXT DEFAULT '[]',
                    update_time REAL
                )
            """)
            conn.commit()
        except Exception as exc:  # pragma: no cover
            logger.error("初始化用户组表失败: %s", exc)

    @classmethod
    def seed_builtin_groups(cls) -> None:
        """插入内置用户组（如不存在）。"""
        conn = Database.get_conn(cls.db_name)
        for g in BUILTIN_GLOBAL_GROUPS + BUILTIN_ORG_GROUPS:
            cur = conn.execute("SELECT COUNT(*) FROM user_groups WHERE id = ?", (g["id"],))
            if cur.fetchone()[0] == 0:
                conn.execute(
                    """INSERT INTO user_groups
                       (id, name, description, internal, type, scope_id, pos, create_time, update_time, create_user)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (g["id"], g["name"], g["description"], 1, g["type"], g["scopeId"],
                     g["pos"], g["createTime"], g["updateTime"], g["createUser"]),
                )
        conn.commit()

    @classmethod
    def _to_group_dict(cls, row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "internal": bool(row["internal"]),
            "type": row["type"],
            "scopeId": row["scope_id"],
            "createTime": int((row["create_time"] or 0) * 1000),
            "updateTime": int((row["update_time"] or 0) * 1000),
            "createUser": row["create_user"],
            "pos": row["pos"],
        }

    @classmethod
    def _to_member_dict(cls, row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "userId": row["user_id"],
            "groupId": row["group_id"],
            "username": row["username"],
            "name": row["name"],
            "email": row["email"],
            "type": row["type"],
            "scopeId": row["scope_id"],
            "createTime": int((row["create_time"] or 0) * 1000),
            "updateTime": int((row["update_time"] or 0) * 1000),
        }

    # ── 用户组 CRUD ─────────────────────────────────────
    @classmethod
    def list_groups(cls, group_type: str = "SYSTEM",
                    scope_id: str = "") -> List[Dict[str, Any]]:
        """列出用户组。"""
        conn = Database.get_conn(cls.db_name)
        if scope_id and scope_id != "global":
            rows = conn.execute(
                "SELECT * FROM user_groups WHERE type = ? AND (scope_id IN ('global', 'organization', 'project') OR scope_id = ? OR scope_id = '') ORDER BY pos, name",
                (group_type, scope_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM user_groups WHERE type = ? ORDER BY pos, name", (group_type,)
            ).fetchall()
        return [cls._to_group_dict(r) for r in rows]

    @classmethod
    def get_group(cls, group_id: str) -> Optional[Dict[str, Any]]:
        """获取单个用户组。"""
        conn = Database.get_conn(cls.db_name)
        row = conn.execute("SELECT * FROM user_groups WHERE id = ?", (group_id,)).fetchone()
        if not row:
            return None
        return cls._to_group_dict(row)

    @classmethod
    def create_group(cls, name: str, description: str = "", group_type: str = "SYSTEM",
                     scope_id: str = "", create_user: str = "admin",
                     pos: int = 99) -> Dict[str, Any]:
        """创建用户组。"""
        now = time.time()
        gid = str(uuid.uuid4())
        conn = Database.get_conn(cls.db_name)
        conn.execute(
            """INSERT INTO user_groups
               (id, name, description, internal, type, scope_id, pos, create_time, update_time, create_user)
               VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?, ?)""",
            (gid, name, description, group_type, scope_id, pos, now, now, create_user),
        )
        conn.commit()
        return cls.get_group(gid)

    @classmethod
    def update_group(cls, group_id: str, name: str = None, description: str = None,
                     pos: int = None, update_user: str = "admin") -> Optional[Dict[str, Any]]:
        """更新用户组。内置用户组只允许改描述。"""
        group = cls.get_group(group_id)
        if not group:
            return None
        conn = Database.get_conn(cls.db_name)
        now = time.time()
        fields = []
        params = []
        if not group["internal"]:
            if name is not None:
                fields.append("name = ?")
                params.append(name)
        if description is not None:
            fields.append("description = ?")
            params.append(description)
        if pos is not None:
            fields.append("pos = ?")
            params.append(pos)
        if not fields:
            return group
        fields.append("update_time = ?")
        fields.append("update_user = ?")
        params.extend([now, update_user])
        params.append(group_id)
        conn.execute(f"UPDATE user_groups SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
        return cls.get_group(group_id)

    @classmethod
    def delete_group(cls, group_id: str) -> bool:
        """删除用户组（内置用户组不可删）。"""
        group = cls.get_group(group_id)
        if not group or group["internal"]:
            return False
        conn = Database.get_conn(cls.db_name)
        conn.execute("DELETE FROM user_groups WHERE id = ?", (group_id,))
        conn.execute("DELETE FROM user_group_members WHERE group_id = ?", (group_id,))
        conn.execute("DELETE FROM user_group_permissions WHERE group_id = ?", (group_id,))
        conn.commit()
        return True

    # ── 用户组成员管理 ──────────────────────────────────
    @classmethod
    def list_group_members(cls, group_id: str, keyword: str = "") -> List[Dict[str, Any]]:
        """列出用户组成员。"""
        conn = Database.get_conn(cls.db_name)
        if keyword:
            like = f"%{keyword}%"
            rows = conn.execute(
                "SELECT * FROM user_group_members WHERE group_id = ? AND (username LIKE ? OR name LIKE ? OR email LIKE ?) ORDER BY create_time",
                (group_id, like, like, like),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM user_group_members WHERE group_id = ? ORDER BY create_time", (group_id,)
            ).fetchall()
        return [cls._to_member_dict(r) for r in rows]

    @classmethod
    def add_group_member(cls, group_id: str, user_id: str, username: str = "",
                         name: str = "", email: str = "", group_type: str = "SYSTEM",
                         scope_id: str = "") -> Optional[Dict[str, Any]]:
        """添加用户组成员。"""
        now = time.time()
        conn = Database.get_conn(cls.db_name)
        cur = conn.execute(
            "SELECT COUNT(*) FROM user_group_members WHERE group_id = ? AND user_id = ?",
            (group_id, user_id),
        )
        if cur.fetchone()[0] > 0:
            return cls.get_group_member(group_id, user_id)
        mid = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO user_group_members
               (id, group_id, user_id, username, name, email, type, scope_id, create_time, update_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (mid, group_id, user_id, username, name, email, group_type, scope_id, now, now),
        )
        conn.commit()
        return cls.get_group_member(group_id, user_id)

    @classmethod
    def get_group_member(cls, group_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        conn = Database.get_conn(cls.db_name)
        row = conn.execute(
            "SELECT * FROM user_group_members WHERE group_id = ? AND user_id = ?",
            (group_id, user_id),
        ).fetchone()
        return cls._to_member_dict(row) if row else None

    @classmethod
    def remove_group_member(cls, group_id: str, user_id: str) -> bool:
        """移除用户组成员。"""
        conn = Database.get_conn(cls.db_name)
        cur = conn.execute(
            "DELETE FROM user_group_members WHERE group_id = ? AND user_id = ?",
            (group_id, user_id),
        )
        conn.commit()
        return cur.rowcount > 0

    @classmethod
    def remove_group_member_by_id(cls, user_role_id: str) -> bool:
        """按关联记录 id 移除用户组成员。"""
        conn = Database.get_conn(cls.db_name)
        cur = conn.execute("DELETE FROM user_group_members WHERE id = ?", (user_role_id,))
        conn.commit()
        return cur.rowcount > 0

    @classmethod
    def remove_user_org_memberships(cls, user_id: str) -> int:
        """移除某用户下所有 ORGANIZATION 类型用户组成员关系（更新角色前清理）。"""
        conn = Database.get_conn(cls.db_name)
        cur = conn.execute(
            "DELETE FROM user_group_members WHERE user_id = ? AND type = 'ORGANIZATION'",
            (user_id,),
        )
        conn.commit()
        return cur.rowcount

    @classmethod
    def get_user_options(cls, exclude_group_id: str = "",
                         keyword: str = "") -> List[Dict[str, Any]]:
        """获取可选用户（用于用户组添加成员下拉）。"""
        from app.auth.store import AuthStore
        store = AuthStore()
        users = store.list_users()
        existing = set()
        if exclude_group_id:
            existing = {m["userId"] for m in cls.list_group_members(exclude_group_id)}
        result = []
        for u in users:
            if u.get("deleted"):
                continue
            if u["id"] in existing:
                continue
            uname = u.get("username", "")
            name = u.get("name", "")
            if keyword and keyword not in uname and keyword not in name:
                continue
            result.append({
                "id": u["id"],
                "userId": u["id"],
                "name": name or uname,
                "username": uname,
                "email": u.get("email", ""),
            })
        return result

    # ── 用户组权限管理 ──────────────────────────────────
    @classmethod
    def get_group_permissions(cls, group_id: str) -> List[str]:
        """获取用户组权限。"""
        conn = Database.get_conn(cls.db_name)
        row = conn.execute(
            "SELECT permissions FROM user_group_permissions WHERE group_id = ?", (group_id,)
        ).fetchone()
        if not row:
            return []
        try:
            return json.loads(row["permissions"])
        except Exception:
            return []

    @classmethod
    def update_group_permissions(cls, group_id: str,
                                 permissions: List[str]) -> bool:
        """更新用户组权限。"""
        conn = Database.get_conn(cls.db_name)
        now = time.time()
        raw = json.dumps(permissions or [], ensure_ascii=False)
        cur = conn.execute(
            "SELECT COUNT(*) FROM user_group_permissions WHERE group_id = ?", (group_id,)
        )
        if cur.fetchone()[0] > 0:
            conn.execute(
                "UPDATE user_group_permissions SET permissions = ?, update_time = ? WHERE group_id = ?",
                (raw, now, group_id),
            )
        else:
            conn.execute(
                "INSERT INTO user_group_permissions (group_id, permissions, update_time) VALUES (?, ?, ?)",
                (group_id, raw, now),
            )
        conn.commit()
        return True


# 确保表存在（下沉前 user_groups.py 在 import 时执行建表 + 播种内置组）
UserGroupRepo.init_tables()
UserGroupRepo.seed_builtin_groups()
