# app/repositories/organization_repo.py
"""组织（租户）数据访问层（Phase 3 重构 · 4 层对齐）。

本层是组织 / 组织成员 / 组织-项目关联数据访问的统一入口。

组织 / 组织成员表 DDL 的唯一权威来源收口于此（_init_tables），
并随连接获取懒触发建表守卫，避免多源重复建表导致「谁先跑谁定 schema」。

纯数据访问（CRUD / 查询 / 成员 / 关联）均在仓库内直连 SQL；
跨 auth/projects 的业务编排（seed_tenant_data）归 Service 层处理，
本层不做业务编排，也不再 lazy-import 旧 app.organizations.store。
"""
import time
import uuid
from typing import Dict, List, Optional

from app.core.database import Database
from app.logging_config import get_logger
from app.repositories.base import BaseRepo


class OrganizationRepo(BaseRepo):
    """组织数据访问仓库。"""

    db_name = "projects.db"
    table_name = "organizations"

    # 建表守卫：收敛到 _conn() 一处，覆盖冷启动空库裸查路径。
    _schema_ensured = False

    # ── 连接与建表 ─────────────────────────────────────────
    @classmethod
    def _conn(cls):
        """获取 projects.db 连接；首访懒触发一次组织主表建表守卫。"""
        if not cls._schema_ensured:
            cls._init_tables()
            cls._schema_ensured = True
        return Database.get_conn(cls.db_name)

    @classmethod
    def _init_tables(cls) -> None:
        """确保 organizations / organization_members 表存在且列齐全。

        organizations / organization_members 表的唯一权威 DDL 收口于此。
        projects / project_envs / project_members 表仍由 ProjectRepo 独家负责，
        此处仅触发其建表以确保组织-项目关联查询的表一定存在。

        直接用 Database 连接，避免与 _conn 守卫互相递归。
        """
        conn = Database.get_conn(cls.db_name)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                num INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',   -- active/disabled/deleted
                deleted INTEGER DEFAULT 0,
                create_time REAL,
                update_time REAL,
                create_user TEXT DEFAULT 'admin',
                update_user TEXT DEFAULT 'admin'
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_org_name ON organizations(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_org_status ON organizations(status)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS organization_members (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT DEFAULT '',
                name TEXT DEFAULT '',
                email TEXT DEFAULT '',
                role TEXT DEFAULT 'member',   -- admin/member
                create_time REAL,
                update_time REAL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_org_members_org ON organization_members(organization_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_org_members_user ON organization_members(user_id)")

        # 确保默认组织存在（系统默认租户，auth/system 等路由依赖）
        cls._ensure_default_org(conn)

        # projects 相关表仍由 ProjectRepo 独家负责，此处仅触发其建表。
        from app.repositories.project_repo import ProjectRepo
        ProjectRepo._init_tables()
        conn.commit()

    @classmethod
    def _ensure_default_org(cls, conn) -> None:
        """确保默认组织及其管理员成员存在（幂等）。"""
        cur = conn.execute(
            "SELECT COUNT(*) FROM organizations WHERE id = ?", ("default-org",)
        )
        if cur.fetchone()[0] > 0:
            return
        now = time.time()
        conn.execute(
            """INSERT INTO organizations
               (id, name, description, num, status, deleted, create_time, update_time)
               VALUES (?,?,?,?,?,?,?,?)""",
            ("default-org", "默认组织", "系统默认组织", 1, 'active', 0, now, now),
        )
        try:
            from app.auth.store import auth_store
            admin = auth_store.get_user_by_username("admin")
        except Exception:
            admin = None
        if admin:
            conn.execute(
                """INSERT OR IGNORE INTO organization_members
                   (id, organization_id, user_id, username, name, email, role, create_time, update_time)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4()), "default-org", admin["id"],
                 admin.get("username", ""), admin.get("name", ""),
                 admin.get("email", ""), 'admin', now, now),
            )

    # ── 行工具 ────────────────────────────────────────────
    @classmethod
    def _attach_member_count(cls, org: dict) -> dict:
        """附加组织成员数量（与旧 store.get_organization 口径一致）。"""
        cnt = cls._conn().execute(
            "SELECT COUNT(*) FROM organization_members WHERE organization_id = ?",
            (org["id"],),
        ).fetchone()[0]
        org["memberCount"] = cnt
        return org

    @classmethod
    def _get_org_row(cls, oid: str) -> Optional[dict]:
        row = cls._conn().execute(
            "SELECT * FROM organizations WHERE id = ? AND deleted = 0", (oid,)
        ).fetchone()
        return dict(row) if row else None

    # ── 组织 CRUD ─────────────────────────────────────────
    @classmethod
    def create(cls, name: str, description: str = "",
               create_user: str = "admin") -> dict:
        oid = str(uuid.uuid4())
        now = time.time()
        conn = cls._conn()
        num = conn.execute(
            "SELECT COALESCE(MAX(num), 0) + 1 FROM organizations"
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO organizations
               (id, name, description, num, status, deleted,
                create_time, update_time, create_user, update_user)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (oid, name, description, num, 'active', 0, now, now,
             create_user, create_user),
        )
        conn.commit()
        org = cls._get_org_row(oid)
        return cls._attach_member_count(org) if org else {"id": oid}

    @classmethod
    def get(cls, oid: str) -> Optional[dict]:
        org = cls._get_org_row(oid)
        return cls._attach_member_count(org) if org else None

    @classmethod
    def get_by_name(cls, name: str) -> Optional[dict]:
        row = cls._conn().execute(
            "SELECT * FROM organizations WHERE name = ? AND deleted = 0", (name,)
        ).fetchone()
        return dict(row) if row else None

    @classmethod
    def list(cls, search: str = "", status: str = "",
             limit: int = 100, offset: int = 0) -> List[dict]:
        sql = "SELECT * FROM organizations WHERE deleted = 0"
        params: list = []
        if search:
            sql += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY num ASC LIMIT ? OFFSET ?"
        params.extend([int(limit), int(offset)])
        rows = cls._conn().execute(sql, params).fetchall()
        return [cls._attach_member_count(dict(r)) for r in rows]

    @classmethod
    def count(cls, search: str = "") -> int:
        sql = "SELECT COUNT(*) FROM organizations WHERE deleted = 0"
        params: list = []
        if search:
            sql += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        return cls._conn().execute(sql, params).fetchone()[0]

    @classmethod
    def update(cls, oid: str, data: Optional[dict] = None,
               **kwargs) -> Optional[dict]:
        """更新组织信息，兼容 data dict 或 **kwargs 两种入参方式。"""
        updates = dict(data) if data is not None else dict(kwargs)
        allowed = {"name", "description", "status"}
        set_pairs = []
        params: list = []
        for k, v in updates.items():
            if k in allowed and v is not None:
                set_pairs.append(f"{k} = ?")
                params.append(v)
        if set_pairs:
            set_pairs.append("update_time = ?")
            params.append(time.time())
            params.append(oid)
            cls._conn().execute(
                f"UPDATE organizations SET {', '.join(set_pairs)} WHERE id = ?",
                params,
            )
            cls._conn().commit()
        return cls.get(oid)

    @classmethod
    def rename(cls, oid: str, name: str) -> Optional[dict]:
        return cls.update(oid, name=name)

    @classmethod
    def delete(cls, oid: str, hard: bool = False) -> bool:
        """删除组织。

        - hard=False: 软删除（标记 deleted=1, status='deleted'）
        - hard=True:  物理删除（含 organization_members 级联清理）
        批量/级联操作纳入事务：任一步失败整体回滚。
        """
        try:
            with Database.transaction(cls.db_name) as conn:
                if hard:
                    conn.execute("DELETE FROM organizations WHERE id = ?", (oid,))
                    conn.execute(
                        "DELETE FROM organization_members WHERE organization_id = ?",
                        (oid,),
                    )
                else:
                    conn.execute(
                        "UPDATE organizations SET deleted = 1, status = 'deleted', "
                        "update_time = ? WHERE id = ?",
                        (time.time(), oid),
                    )
            return True
        except Exception as e:
            get_logger(__name__).error("删除组织失败: %s", e)
            return False

    @classmethod
    def recover(cls, oid: str) -> bool:
        cur = cls._conn().execute(
            "UPDATE organizations SET deleted = 0, status = 'active', "
            "update_time = ? WHERE id = ?",
            (time.time(), oid),
        )
        cls._conn().commit()
        return cur.rowcount > 0

    @classmethod
    def enable(cls, oid: str) -> bool:
        return bool(cls.update(oid, status="active"))

    @classmethod
    def disable(cls, oid: str) -> bool:
        return bool(cls.update(oid, status="disabled"))

    # ── 组织成员管理 ─────────────────────────────────────
    @classmethod
    def list_members(cls, org_id: str, search: str = "",
                     limit: int = 100) -> List[dict]:
        sql = "SELECT * FROM organization_members WHERE organization_id = ?"
        params: list = [org_id]
        if search:
            sql += " AND (username LIKE ? OR name LIKE ? OR email LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        sql += " ORDER BY create_time ASC LIMIT ?"
        params.append(limit)
        rows = cls._conn().execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def get_member(cls, member_id: str) -> Optional[dict]:
        row = cls._conn().execute(
            "SELECT * FROM organization_members WHERE id = ?", (member_id,)
        ).fetchone()
        return dict(row) if row else None

    @classmethod
    def add_member(cls, org_id: str, user_id: str,
                   role: str = "member") -> Optional[dict]:
        conn = cls._conn()
        existing = conn.execute(
            "SELECT * FROM organization_members "
            "WHERE organization_id = ? AND user_id = ?",
            (org_id, user_id),
        ).fetchone()
        if existing:
            if existing["role"] != role:
                conn.execute(
                    "UPDATE organization_members SET role = ?, update_time = ? "
                    "WHERE id = ?",
                    (role, time.time(), existing["id"]),
                )
                conn.commit()
                return cls.get_member(existing["id"])
            return dict(existing)
        mid = str(uuid.uuid4())
        now = time.time()
        username, name, email = "", "", ""
        try:
            row = conn.execute(
                "SELECT username, name, email FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if row:
                username, name, email = row
        except Exception:
            pass
        conn.execute(
            """INSERT INTO organization_members
               (id, organization_id, user_id, username, name, email, role,
                create_time, update_time)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (mid, org_id, user_id, username, name, email, role, now, now),
        )
        conn.commit()
        return cls.get_member(mid)

    @classmethod
    def update_member(cls, org_id: str, user_id: str,
                      role: Optional[str] = None) -> Optional[dict]:
        if role is None:
            return None
        conn = cls._conn()
        conn.execute(
            "UPDATE organization_members SET role = ?, update_time = ? "
            "WHERE organization_id = ? AND user_id = ?",
            (role, time.time(), org_id, user_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM organization_members "
            "WHERE organization_id = ? AND user_id = ?",
            (org_id, user_id),
        ).fetchone()
        return dict(row) if row else None

    @classmethod
    def remove_member(cls, org_id: str, user_id: str) -> bool:
        cur = cls._conn().execute(
            "DELETE FROM organization_members "
            "WHERE organization_id = ? AND user_id = ?",
            (org_id, user_id),
        )
        cls._conn().commit()
        return cur.rowcount > 0

    @classmethod
    def count_members(cls, org_id: str) -> int:
        return cls._conn().execute(
            "SELECT COUNT(*) FROM organization_members "
            "WHERE organization_id = ?", (org_id,)
        ).fetchone()[0]

    @classmethod
    def list_orgs_by_user(cls, user_id: str) -> List[dict]:
        rows = cls._conn().execute(
            "SELECT o.* FROM organizations o "
            "JOIN organization_members m ON m.organization_id = o.id "
            "WHERE m.user_id = ? AND o.deleted = 0 ORDER BY o.num ASC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def list_orgs_by_users(cls, user_ids: List[str]) -> Dict[str, List[dict]]:
        if not user_ids:
            return {}
        placeholders = ",".join("?" * len(user_ids))
        try:
            rows = cls._conn().execute(
                "SELECT o.*, m.user_id FROM organizations o "
                "JOIN organization_members m ON m.organization_id = o.id "
                f"WHERE m.user_id IN ({placeholders}) AND o.deleted = 0 "
                "ORDER BY o.num ASC",
                list(user_ids),
            ).fetchall()
        except Exception:
            return {}
        result: Dict[str, List[dict]] = {uid: [] for uid in user_ids}
        for r in rows:
            d = dict(r)
            uid = d.pop("user_id", "")
            if uid in result:
                result[uid].append(d)
        return result

    # ── 组织-项目关联 ────────────────────────────────────
    @classmethod
    def list_projects(cls, org_id: str) -> List[dict]:
        rows = cls._conn().execute(
            "SELECT * FROM projects WHERE organization_id = ? AND deleted = 0 "
            "ORDER BY updated_at DESC", (org_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def bind_project(cls, project_id: str, org_id: str) -> bool:
        cur = cls._conn().execute(
            "UPDATE projects SET organization_id = ? WHERE id = ?",
            (org_id, project_id),
        )
        cls._conn().commit()
        return cur.rowcount > 0

    # ── 租户摘要 / 初始化 ────────────────────────────────
    @classmethod
    def tenant_summary(cls) -> dict:
        conn = cls._conn()
        org_count = conn.execute(
            "SELECT COUNT(*) FROM organizations WHERE deleted = 0"
        ).fetchone()[0]
        member_count = conn.execute(
            "SELECT COUNT(*) FROM organization_members"
        ).fetchone()[0]
        project_count = conn.execute(
            "SELECT COUNT(*) FROM projects WHERE deleted = 0"
        ).fetchone()[0]
        orgs = cls.list()
        return {
            "orgCount": org_count,
            "memberCount": member_count,
            "projectCount": project_count,
            "organizations": orgs,
        }

    @classmethod
    def get_tenant_summary(cls) -> dict:
        """兼容旧命名风格的租户摘要入口（同 tenant_summary）。"""
        return cls.tenant_summary()

    @classmethod
    def ensure_default_org(cls) -> None:
        """确保组织表与默认组织存在（幂等，供 Service 编排调用）。

        直接触发 _init_tables() 完成建表并确保默认组织，避免绕过建表守卫
        在空库上裸查 organizations 报“no such table”。
        """
        cls._init_tables()


organization_repo = OrganizationRepo
