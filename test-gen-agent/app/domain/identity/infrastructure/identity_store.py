"""身份上下文 SQLite 存储适配器（薄门面存储）。

为 identity_app_service 中"薄委托"方法提供本地存储实现，替代对
app.repositories.* 的旧依赖。聚合级操作仍由 identity_repository_impl
中的仓储适配器负责；本文件仅覆盖旁路查询/统计/配置类方法。
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Optional

from app.core.database import Database


class IdentityStore:
    db_name = "tga.db"

    def __init__(self) -> None:
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_organizations ("
            "id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT DEFAULT '', "
            "status TEXT DEFAULT 'active', created_at REAL NOT NULL, updated_at REAL NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_organization_members ("
            "id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, user_id TEXT NOT NULL, "
            "username TEXT DEFAULT '', name TEXT DEFAULT '', email TEXT DEFAULT '', "
            "role TEXT DEFAULT 'member')"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_org_projects ("
            "id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, project_id TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_api_keys ("
            "id TEXT PRIMARY KEY, user_id TEXT NOT NULL, description TEXT DEFAULT '', "
            "access_key TEXT DEFAULT '', enable INTEGER DEFAULT 1, create_time REAL NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_local_configs ("
            "id TEXT PRIMARY KEY, user_id TEXT NOT NULL, user_url TEXT DEFAULT '', "
            "cfg_type TEXT DEFAULT '', cfg_id TEXT DEFAULT '', enable INTEGER DEFAULT 1)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_user_groups ("
            "id TEXT PRIMARY KEY, name TEXT DEFAULT '', description TEXT DEFAULT '', "
            "group_type TEXT DEFAULT 'SYSTEM', scope_id TEXT DEFAULT '', internal INTEGER DEFAULT 0)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_group_members ("
            "id TEXT PRIMARY KEY, group_id TEXT NOT NULL, user_id TEXT NOT NULL, "
            "username TEXT DEFAULT '', name TEXT DEFAULT '', email TEXT DEFAULT '', "
            "group_type TEXT DEFAULT 'SYSTEM', scope_id TEXT DEFAULT '')"
        )
        conn.commit()

    # ── 组织 ──────────────────────────────────────────
    def create_org(self, name, description):
        item_id = uuid.uuid4().hex[:12]
        now = time.time()
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "INSERT INTO domain_organizations VALUES (?, ?, ?, ?, ?, ?)",
            (item_id, name, description, "active", now, now),
        )
        conn.commit()
        return {"id": item_id, "name": name, "description": description, "status": "active"}

    def update_org(self, org_id, data):
        conn = Database.get_conn(self.db_name)
        set_clause = ", ".join(f"{k}=?" for k in data)
        conn.execute(f"UPDATE domain_organizations SET {set_clause}, updated_at=? WHERE id=?", (*data.values(), time.time(), org_id))
        conn.commit()
        return self.get_org(org_id)

    def get_org(self, org_id):
        r = Database.get_conn(self.db_name).execute("SELECT * FROM domain_organizations WHERE id=?", (org_id,)).fetchone()
        return dict(r) if r else None

    def get_org_by_name(self, name):
        r = Database.get_conn(self.db_name).execute("SELECT * FROM domain_organizations WHERE name=? AND status!='deleted'", (name,)).fetchone()
        return dict(r) if r else None

    def list_orgs(self, search="", status="", limit=100, offset=0):
        q = "SELECT * FROM domain_organizations WHERE 1=1"
        p = []
        if search: q += " AND name LIKE ?"; p.append(f"%{search}%")
        if status: q += " AND status=?"; p.append(status)
        p += [max(1, limit), max(0, offset)]
        rows = Database.get_conn(self.db_name).execute(q + " ORDER BY created_at DESC LIMIT ? OFFSET ?", p).fetchall()
        return [dict(r) for r in rows]

    def count_orgs(self, search=""):
        return len(self.list_orgs(search=search, limit=999999))

    def delete_org(self, org_id, hard=False):
        if hard:
            Database.get_conn(self.db_name).execute("DELETE FROM domain_organizations WHERE id=?", (org_id,))
        else:
            Database.get_conn(self.db_name).execute("UPDATE domain_organizations SET status='deleted' WHERE id=?", (org_id,))
        Database.get_conn(self.db_name).commit()
        return True

    def recover_org(self, org_id):
        Database.get_conn(self.db_name).execute("UPDATE domain_organizations SET status='active' WHERE id=?", (org_id,))
        Database.get_conn(self.db_name).commit()
        return True

    # ── 组织成员 ──────────────────────────────────────
    def add_member(self, org_id, user_id, role="member", username="", name="", email=""):
        item_id = uuid.uuid4().hex[:12]
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "INSERT INTO domain_organization_members VALUES (?, ?, ?, ?, ?, ?, ?)",
            (item_id, org_id, user_id, username, name, email, role),
        )
        conn.commit()
        return {"id": item_id, "organization_id": org_id, "user_id": user_id, "role": role}

    def remove_member(self, org_id, user_id):
        Database.get_conn(self.db_name).execute("DELETE FROM domain_organization_members WHERE organization_id=? AND user_id=?", (org_id, user_id))
        Database.get_conn(self.db_name).commit()
        return True

    def list_members(self, org_id, search="", limit=100, offset=0):
        q = "SELECT * FROM domain_organization_members WHERE organization_id=?"
        p = [org_id]
        if search: q += " AND (name LIKE ? OR username LIKE ?)"; p += [f"%{search}%", f"%{search}%"]
        p += [max(1, limit), max(0, offset)]
        rows = Database.get_conn(self.db_name).execute(q + " LIMIT ? OFFSET ?", p).fetchall()
        return [dict(r) for r in rows]

    def get_member(self, member_id):
        r = Database.get_conn(self.db_name).execute("SELECT * FROM domain_organization_members WHERE id=?", (member_id,)).fetchone()
        return dict(r) if r else None

    def count_members(self, org_id):
        r = Database.get_conn(self.db_name).execute("SELECT COUNT(*) AS n FROM domain_organization_members WHERE organization_id=?", (org_id,)).fetchone()
        return int(r["n"]) if r else 0

    def update_member(self, org_id, user_id, role):
        Database.get_conn(self.db_name).execute("UPDATE domain_organization_members SET role=? WHERE organization_id=? AND user_id=?", (role, org_id, user_id))
        Database.get_conn(self.db_name).commit()
        return True

    # ── 组织项目绑定 ──────────────────────────────────
    def bind_project(self, project_id, org_id):
        item_id = uuid.uuid4().hex[:12]
        conn = Database.get_conn(self.db_name)
        conn.execute("INSERT INTO domain_org_projects VALUES (?, ?, ?)", (item_id, org_id, project_id))
        conn.commit()
        return True

    def list_projects(self, org_id):
        rows = Database.get_conn(self.db_name).execute("SELECT project_id FROM domain_org_projects WHERE organization_id=?", (org_id,)).fetchall()
        return [{"project_id": r["project_id"]} for r in rows]

    def list_orgs_by_user(self, user_id):
        rows = Database.get_conn(self.db_name).execute("SELECT o.* FROM domain_organizations o JOIN domain_organization_members m ON o.id=m.organization_id WHERE m.user_id=? AND o.status!='deleted'", (user_id,)).fetchall()
        return [dict(r) for r in rows]

    def list_orgs_by_users(self, user_ids):
        if not user_ids:
            return {}
        placeholders = ",".join("?" for _ in user_ids)
        rows = Database.get_conn(self.db_name).execute(f"SELECT o.*, m.user_id FROM domain_organizations o JOIN domain_organization_members m ON o.id=m.organization_id WHERE m.user_id IN ({placeholders}) AND o.status!='deleted'", user_ids).fetchall()
        result = {}
        for r in dict(r):
            result.setdefault(r["user_id"], []).append(dict(r))
        return result

    def tenant_summary(self):
        conn = Database.get_conn(self.db_name)
        orgs = conn.execute("SELECT COUNT(*) AS n FROM domain_organizations WHERE status!='deleted'").fetchone()["n"]
        users = conn.execute("SELECT COUNT(*) AS n FROM domain_users WHERE enabled=1").fetchone()["n"] if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='domain_users'").fetchone() else 0
        projects = conn.execute("SELECT COUNT(*) AS n FROM domain_projects").fetchone()["n"] if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='domain_projects'").fetchone() else 0
        return {"organizations": orgs, "users": users, "projects": projects}

    def get_tenant_summary(self):
        return self.tenant_summary()

    # ── API Key ───────────────────────────────────────
    def create_api_key(self, user_id, description="", forever=False, expire_time=None):
        item_id = uuid.uuid4().hex[:12]
        access_key = "ak_" + uuid.uuid4().hex[:16]
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "INSERT INTO domain_api_keys VALUES (?, ?, ?, ?, ?, ?)",
            (item_id, user_id, description, access_key, 1, time.time()),
        )
        conn.commit()
        return {"key_id": item_id, "access_key": access_key}

    def delete_api_key(self, key_id):
        Database.get_conn(self.db_name).execute("DELETE FROM domain_api_keys WHERE id=?", (key_id,))
        Database.get_conn(self.db_name).commit()
        return True

    def list_api_keys(self, user_id=""):
        q = "SELECT * FROM domain_api_keys WHERE 1=1"
        p = []
        if user_id: q += " AND user_id=?"; p.append(user_id)
        rows = Database.get_conn(self.db_name).execute(q, p).fetchall()
        return [dict(r) for r in rows]

    def toggle_api_key(self, key_id, enable):
        Database.get_conn(self.db_name).execute("UPDATE domain_api_keys SET enable=? WHERE id=?", (int(enable), key_id))
        Database.get_conn(self.db_name).commit()
        return True

    # ── 本地配置 ──────────────────────────────────────
    def add_local_config(self, user_id, user_url, cfg_type=""):
        item_id = uuid.uuid4().hex[:12]
        cfg_id = "cfg_" + uuid.uuid4().hex[:8]
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "INSERT INTO domain_local_configs VALUES (?, ?, ?, ?, ?, ?)",
            (item_id, user_id, user_url, cfg_type, cfg_id, 1),
        )
        conn.commit()
        return {"cfg_id": cfg_id}

    def get_local_configs(self, user_id=""):
        q = "SELECT * FROM domain_local_configs WHERE 1=1"
        p = []
        if user_id: q += " AND user_id=?"; p.append(user_id)
        rows = Database.get_conn(self.db_name).execute(q, p).fetchall()
        return [dict(r) for r in rows]

    def update_local_config(self, cfg_id, user_url):
        Database.get_conn(self.db_name).execute("UPDATE domain_local_configs SET user_url=? WHERE id=?", (user_url, cfg_id))
        Database.get_conn(self.db_name).commit()
        return True

    def toggle_local_config(self, cfg_id, enable):
        Database.get_conn(self.db_name).execute("UPDATE domain_local_configs SET enable=? WHERE id=?", (int(enable), cfg_id))
        Database.get_conn(self.db_name).commit()
        return True

    # ── 用户组 ────────────────────────────────────────
    def create_group(self, name="", description="", group_type="SYSTEM", scope_id=""):
        item_id = uuid.uuid4().hex[:12]
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "INSERT INTO domain_user_groups VALUES (?, ?, ?, ?, ?, ?)",
            (item_id, name, description, group_type, scope_id, 0),
        )
        conn.commit()
        return {"id": item_id, "name": name, "description": description, "group_type": group_type, "scope_id": scope_id, "internal": 0}

    def get_group(self, group_id):
        r = Database.get_conn(self.db_name).execute("SELECT * FROM domain_user_groups WHERE id=?", (group_id,)).fetchone()
        return dict(r) if r else None

    def list_groups(self, group_type="SYSTEM", scope_id=""):
        q = "SELECT * FROM domain_user_groups WHERE 1=1"
        p = []
        if group_type: q += " AND group_type=?"; p.append(group_type)
        if scope_id: q += " AND scope_id=?"; p.append(scope_id)
        rows = Database.get_conn(self.db_name).execute(q, p).fetchall()
        return [dict(r) for r in rows]

    def update_group(self, group_id, name="", description=""):
        Database.get_conn(self.db_name).execute("UPDATE domain_user_groups SET name=?, description=? WHERE id=?", (name, description, group_id))
        Database.get_conn(self.db_name).commit()
        return self.get_group(group_id)

    def delete_group(self, group_id):
        Database.get_conn(self.db_name).execute("DELETE FROM domain_user_groups WHERE id=?", (group_id,))
        Database.get_conn(self.db_name).commit()
        return True

    def update_group_permissions(self, group_id, permissions):
        # 权限存储在单独表中或 JSON，此处占位
        return True

    def get_group_permissions(self, group_id):
        return []

    # ── 用户组成员 ────────────────────────────────────
    def add_group_member(self, group_id, user_id, username="", name="", email="", group_type="SYSTEM", scope_id=""):
        item_id = uuid.uuid4().hex[:12]
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "INSERT INTO domain_group_members VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (item_id, group_id, user_id, username, name, email, group_type, scope_id),
        )
        conn.commit()
        return {"id": item_id, "group_id": group_id, "user_id": user_id}

    def remove_group_member(self, group_id, user_id):
        Database.get_conn(self.db_name).execute("DELETE FROM domain_group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
        Database.get_conn(self.db_name).commit()
        return True

    def remove_group_member_by_id(self, user_role_id):
        Database.get_conn(self.db_name).execute("DELETE FROM domain_group_members WHERE id=?", (user_role_id,))
        Database.get_conn(self.db_name).commit()
        return True

    def list_group_members(self, group_id, keyword=""):
        q = "SELECT * FROM domain_group_members WHERE group_id=?"
        p = [group_id]
        if keyword: q += " AND (name LIKE ? OR username LIKE ?)"; p += [f"%{keyword}%", f"%{keyword}%"]
        rows = Database.get_conn(self.db_name).execute(q, p).fetchall()
        return [dict(r) for r in rows]


identity_store = IdentityStore()
IdentityRepo = identity_store
__all__ = ["IdentityStore", "IdentityRepo", "identity_store"]