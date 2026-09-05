# app/repositories/project_repo.py
"""项目数据访问层（Phase 3 重构 · 4 层对齐）。

本层是项目 CRUD / 项目成员 / 项目环境关联数据访问的统一入口，
已从「委托旧 app.projects.management」下沉为**仓库内直接 SQLite 实现**，
消除 Repository 空壳化：SQL 实现收口在本层，输出形态与旧层完全一致
（零回归由 tests/test_project_repo_alignment.py 对齐用例保证）。

纯数据访问（项目 CRUD / 成员 / 环境关联）均在仓库内直连 SQL；
项目源码扫描 / 回收站-业务数据级联等业务编排归 Service 层，不在此处。
"""
import time
import uuid
from typing import Dict, List, Optional

from app.core.database import Database
from app.repositories.base import BaseRepo


class ProjectRepo(BaseRepo):
    db_name = "projects.db"
    table_name = "projects"

    # 建表守卫：收敛到 _conn() 一处。此前多数方法已显式调用 _init_tables()，
    # 但仍有遗漏路径在冷启动空库下裸查；统一到连接获取即可全覆盖。
    _schema_ensured = False

    # ── 连接与建表 ─────────────────────────────────────────
    @classmethod
    def _conn(cls):
        """获取 projects.db 连接；首访懒触发一次主项目表建表守卫。"""
        if not cls._schema_ensured:
            cls._init_tables()
            cls._schema_ensured = True
        return Database.get_conn(cls.db_name)

    @classmethod
    def _init_tables(cls) -> None:
        """确保 projects / project_envs / project_members 表存在且列齐全。

        直接用 Database 连接，避免与 _conn 守卫互相递归。
        """
        conn = Database.get_conn(cls.db_name)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                repo_url TEXT DEFAULT '',
                language TEXT DEFAULT 'python',
                path TEXT DEFAULT '',
                status TEXT DEFAULT 'active',  -- active/archived/deleted
                organization_id TEXT DEFAULT '',  -- 所属组织
                deleted INTEGER DEFAULT 0,       -- 0: 正常, 1: 已删除(回收站)
                deleted_at REAL,
                created_at REAL,
                updated_at REAL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name)")

        # 兼容历史库/他处建表：幂等补齐 projects 软删除列
        pcols = [r[1] for r in conn.execute("PRAGMA table_info(projects)").fetchall()]
        if "deleted" not in pcols:
            conn.execute("ALTER TABLE projects ADD COLUMN deleted INTEGER DEFAULT 0")
        if "deleted_at" not in pcols:
            conn.execute("ALTER TABLE projects ADD COLUMN deleted_at REAL")
        if "organization_id" not in pcols:
            conn.execute("ALTER TABLE projects ADD COLUMN organization_id TEXT DEFAULT ''")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS project_envs (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                env_id TEXT NOT NULL,
                created_at REAL,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS project_members (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT DEFAULT '',
                name TEXT DEFAULT '',
                email TEXT DEFAULT '',
                role TEXT DEFAULT 'member',  -- admin/member/guest
                user_group TEXT DEFAULT '',
                created_at REAL,
                updated_at REAL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_members_project ON project_members(project_id)")
        conn.commit()

    @classmethod
    def _get_project_row(cls, pid: str, include_deleted: bool = False) -> Optional[dict]:
        """按 id 取 projects 行。

        - include_deleted=False（默认）: 仅返回未删除项目（软删除后不可见）。
        - include_deleted=True: 忽略删除标记，供回收站/恢复逻辑读取。
        """
        sql = "SELECT * FROM projects WHERE id = ?"
        if not include_deleted:
            sql += " AND (deleted IS NULL OR deleted = 0)"
        row = cls._conn().execute(sql, (pid,)).fetchone()
        return dict(row) if row else None

    # ── 项目 CRUD ─────────────────────────────────────────
    @classmethod
    def create(cls, name: str = "", description: str = "", repo_url: str = "",
               language: str = "python", path: str = "") -> dict:
        """创建项目。"""
        cls._init_tables()
        pid = str(uuid.uuid4())
        now = time.time()
        cls._conn().execute(
            """INSERT INTO projects
               (id, name, description, repo_url, language, path, status,
                deleted, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (pid, name, description, repo_url, language, path, 'active',
             0, now, now),
        )
        cls._conn().commit()
        return cls.get(pid) or {"id": pid}

    @classmethod
    def get(cls, pid: str, include_deleted: bool = False) -> Optional[dict]:
        """获取项目详情（默认不含回收站已删除项目）。"""
        cls._init_tables()
        return cls._get_project_row(pid, include_deleted=include_deleted)

    @classmethod
    def list(cls, search: str = "", status: str = "", limit: int = 100,
             include_deleted: bool = False) -> List[dict]:
        """列出项目（默认不含回收站已删除项目）。"""
        cls._init_tables()
        sql = "SELECT * FROM projects WHERE 1=1"
        if not include_deleted:
            sql += " AND (deleted IS NULL OR deleted = 0)"
        params: list = []
        if search:
            sql += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(int(limit))
        rows = cls._conn().execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def update(cls, pid: str, data: dict = None, **kwargs) -> Optional[dict]:
        """更新项目，兼容 data dict 或 **kwargs 两种入参。

        仅允许更新未软删除的项目：软删（回收站）后 update 直接返回 None，
        不修改记录（与 get 的 include_deleted 过滤口径一致）。
        """
        cls._init_tables()
        if cls.get(pid) is None:
            return None
        updates = dict(data) if data is not None else dict(kwargs)
        allowed = {'name', 'description', 'repo_url', 'language', 'path', 'status'}
        set_pairs = []
        params: list = []
        for k, v in updates.items():
            if k in allowed and v is not None:
                set_pairs.append(f"{k} = ?")
                params.append(v)
        if set_pairs:
            set_pairs.append("updated_at = ?")
            params.append(time.time())
            params.append(pid)
            cls._conn().execute(
                f"UPDATE projects SET {', '.join(set_pairs)} WHERE id = ?", params
            )
            cls._conn().commit()
        return cls.get(pid)

    @classmethod
    def delete(cls, pid: str) -> bool:
        """删除项目（软删除，进入回收站）。"""
        cls._init_tables()
        if not cls.get(pid):
            return False
        now = time.time()
        cur = cls._conn().execute(
            "UPDATE projects SET deleted = 1, deleted_at = ?, status = 'deleted', "
            "updated_at = ? WHERE id = ?",
            (now, now, pid),
        )
        cls._conn().commit()
        return cur.rowcount > 0

    @classmethod
    def recover(cls, pid: str) -> bool:
        """从回收站恢复软删除的项目。"""
        cls._init_tables()
        now = time.time()
        cur = cls._conn().execute(
            "UPDATE projects SET deleted = 0, deleted_at = NULL, status = 'active', "
            "updated_at = ? WHERE id = ?",
            (now, pid),
        )
        cls._conn().commit()
        return cur.rowcount > 0

    @classmethod
    def hard_delete(cls, pid: str) -> bool:
        """彻底删除项目（回收站清空专用）。

        仅当项目确已软删除（deleted=1）时才允许物理删除，确保默认调用方
        不会绕过回收站。projects 与其关联的 project_envs 级联删除置于同一
        事务，保证整体原子性（任一步失败可整体回滚）。
        """
        cls._init_tables()
        with Database.transaction(cls.db_name) as conn:
            row = conn.execute(
                "SELECT deleted FROM projects WHERE id = ?", (pid,)
            ).fetchone()
            if not row:
                return False
            if row["deleted"] != 1:
                return False
            conn.execute("DELETE FROM projects WHERE id = ?", (pid,))
            conn.execute("DELETE FROM project_envs WHERE project_id = ?", (pid,))
        return True

    @classmethod
    def get_stats(cls, pid: str) -> dict:
        """获取项目统计信息。"""
        cls._init_tables()
        env_count = cls._conn().execute(
            "SELECT COUNT(*) FROM project_envs WHERE project_id = ?", (pid,)
        ).fetchone()[0]
        return {'project_id': pid, 'env_count': env_count}

    # ── 项目成员管理 ─────────────────────────────────────
    @classmethod
    def _get_member_row(cls, member_id: str) -> Optional[dict]:
        row = cls._conn().execute(
            "SELECT * FROM project_members WHERE id = ?", (member_id,)
        ).fetchone()
        return dict(row) if row else None

    @classmethod
    def add_member(cls, project_id: str, user_id: str = "", username: str = "",
                   name: str = "", email: str = "", role: str = "member",
                   user_group: str = "") -> Optional[dict]:
        """添加项目成员。"""
        cls._init_tables()
        conn = cls._conn()
        existing = conn.execute(
            "SELECT id FROM project_members WHERE project_id = ? AND user_id = ?",
            (project_id, user_id or username),
        ).fetchone()
        if existing:
            return None
        mid = str(uuid.uuid4())
        now = time.time()
        conn.execute(
            """INSERT INTO project_members
               (id, project_id, user_id, username, name, email, role, user_group,
                created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (mid, project_id, user_id or username, username, name or username,
             email, role, user_group, now, now),
        )
        conn.commit()
        return cls._get_member_row(mid)

    @classmethod
    def list_members(cls, project_id: str, keyword: str = "") -> List[dict]:
        """列出项目成员。"""
        cls._init_tables()
        sql = "SELECT * FROM project_members WHERE project_id = ?"
        params: list = [project_id]
        if keyword:
            sql += " AND (username LIKE ? OR name LIKE ? OR email LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        sql += " ORDER BY created_at ASC"
        rows = cls._conn().execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def get_member(cls, member_id: str) -> Optional[dict]:
        """获取单个项目成员。"""
        cls._init_tables()
        return cls._get_member_row(member_id)

    @classmethod
    def update_member(cls, member_id: str, data: dict = None, **kwargs) -> Optional[dict]:
        """更新项目成员，兼容 data dict 或 **kwargs 两种入参。"""
        cls._init_tables()
        updates = dict(data) if data is not None else dict(kwargs)
        allowed = {'username', 'name', 'email', 'role', 'user_group'}
        set_pairs = []
        params: list = []
        for k, v in updates.items():
            if k in allowed and v is not None:
                set_pairs.append(f"{k} = ?")
                params.append(v)
        if set_pairs:
            set_pairs.append("updated_at = ?")
            params.append(time.time())
            params.append(member_id)
            cls._conn().execute(
                f"UPDATE project_members SET {', '.join(set_pairs)} WHERE id = ?",
                params,
            )
            cls._conn().commit()
        return cls._get_member_row(member_id)

    @classmethod
    def remove_member(cls, project_id: str, user_id: str) -> bool:
        """移除项目成员。"""
        cls._init_tables()
        cur = cls._conn().execute(
            "DELETE FROM project_members WHERE project_id = ? AND user_id = ?",
            (project_id, user_id),
        )
        cls._conn().commit()
        return cur.rowcount > 0

    @classmethod
    def batch_remove_members(cls, project_id: str, user_ids: List[str]) -> int:
        """批量移除项目成员。"""
        cls._init_tables()
        removed = 0
        for uid in user_ids:
            if cls.remove_member(project_id, uid):
                removed += 1
        return removed

    @classmethod
    def count_members_by_project(cls) -> Dict[str, int]:
        """统计各项目成员数。返回 {project_id: count}（组织前端 memberCount）。

        原 organizations 路由直接内联 SQL 扫 project_members 分组统计，
        下沉到本仓库层收口数据访问。
        """
        cls._init_tables()
        rows = cls._conn().execute(
            "SELECT project_id, COUNT(*) AS cnt FROM project_members GROUP BY project_id"
        ).fetchall()
        return {r["project_id"]: int(r["cnt"]) for r in rows}

    @classmethod
    def list_projects_by_user_ids(cls, user_ids) -> Dict[str, List[dict]]:
        """批量反查多个用户所属的项目（含项目 id/name）。

        单条 SQL 联查 project_members 与未删除 projects，返回
        {user_id: [{"id": project_id, "name": project_name}, ...]}，
        供组织/成员列表批量拼接 projectIdNameMap，避免逐项目 list_members 的 N+1 查询。
        """
        cls._init_tables()
        ids = [u for u in (user_ids or []) if u]
        if not ids:
            return {}
        placeholders = ",".join("?" * len(ids))
        try:
            rows = cls._conn().execute(
                "SELECT pm.user_id, p.id AS project_id, p.name AS project_name "
                "FROM project_members pm JOIN projects p ON p.id = pm.project_id "
                f"WHERE pm.user_id IN ({placeholders}) "
                "AND (p.deleted IS NULL OR p.deleted = 0) "
                "ORDER BY pm.created_at ASC",
                list(ids),
            ).fetchall()
        except Exception:
            return {}
        result: Dict[str, List[dict]] = {uid: [] for uid in ids}
        for r in rows:
            uid = r["user_id"]
            if uid in result:
                result[uid].append({"id": r["project_id"], "name": r["project_name"]})
        return result

    @classmethod
    def remove_user_all_projects(cls, user_id: str) -> int:
        """移除某用户在全部项目下的成员关系（跨项目批量删除）。

        原 organizations 路由直接内联 SQL ``DELETE FROM project_members
        WHERE user_id = ?``，下沉到本仓库层收口数据访问。
        """
        cls._init_tables()
        cur = cls._conn().execute(
            "DELETE FROM project_members WHERE user_id = ?",
            (user_id,),
        )
        cls._conn().commit()
        return cur.rowcount

    # ── 项目自定义函数（custom_funcs 表，存于 testcases.db）──────────────
    CUSTOM_FUNC_COLS = {
        "id": "id", "name": "name", "script": "script", "type": "type",
        "description": "description", "status": "status",
        "project_id": "project_id", "tags": "tags", "params": "params",
        "result": "result", "internal": "internal",
        "create_time": "create_time", "update_time": "update_time",
        "create_user": "create_user", "update_user": "update_user",
    }

    @classmethod
    def _ensure_custom_func_table(cls) -> None:
        """确保 custom_funcs 表存在且列齐全。"""
        conn = Database.get_conn("testcases.db")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS custom_funcs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                script TEXT DEFAULT '',
                type TEXT DEFAULT 'HTTP',
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'DRAFT',
                project_id TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                params TEXT DEFAULT '[]',
                result TEXT DEFAULT '',
                internal INTEGER DEFAULT 0,
                create_time REAL,
                update_time REAL,
                create_user TEXT DEFAULT 'admin',
                update_user TEXT DEFAULT 'admin'
            )
        """)
        try:
            existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(custom_funcs)").fetchall()}
            for col, ddl in [
                ("tags", "TEXT DEFAULT '[]'"),
                ("params", "TEXT DEFAULT '[]'"),
                ("result", "TEXT DEFAULT ''"),
                ("internal", "INTEGER DEFAULT 0"),
                ("create_user", "TEXT DEFAULT 'admin'"),
                ("update_user", "TEXT DEFAULT 'admin'"),
            ]:
                if col not in existing_cols:
                    conn.execute(f"ALTER TABLE custom_funcs ADD COLUMN {col} {ddl}")
        except Exception:
            pass
        conn.commit()

    @classmethod
    def list_custom_funcs(cls, project_id: str = "", keyword: str = "") -> List[dict]:
        """分页列出自定义函数（支持 project_id / keyword 过滤）。"""
        cls._ensure_custom_func_table()
        query = "SELECT * FROM custom_funcs"
        conditions = []
        params: list = []
        if project_id:
            conditions.append("project_id = ?")
            params.append(project_id)
        if keyword:
            conditions.append("(name LIKE ? OR id LIKE ?)")
            kw = f"%{keyword}%"
            params.extend([kw, kw])
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY create_time DESC"
        return cls.query_all(query, tuple(params))

    @classmethod
    def get_custom_func_row(cls, func_id: str) -> Optional[dict]:
        """获取 custom_funcs 行（原始字段）。"""
        cls._ensure_custom_func_table()
        return cls.query_one(
            "SELECT * FROM custom_funcs WHERE id = ?", (func_id,)
        )

    @classmethod
    def create_custom_func(cls, func_id: str, name: str = "", script: str = "",
                           func_type: str = "HTTP", description: str = "",
                           status: str = "DRAFT", project_id: str = "",
                           tags: list = None, params: str = "[]", result: str = "",
                           create_user: str = "admin") -> bool:
        """插入自定义函数。"""
        import json
        import time
        cls._ensure_custom_func_table()
        tags = tags or []
        tags_str = json.dumps(tags, ensure_ascii=False)
        now = time.time()
        cls.execute(
            """INSERT INTO custom_funcs
               (id, name, script, type, description, status, project_id, tags, params, result,
                internal, create_time, update_time, create_user, update_user)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)""",
            (func_id, name, script, func_type, description, status, project_id,
             tags_str, params, result, now, now, create_user, create_user),
        )
        return True

    @classmethod
    def update_custom_func(cls, func_id: str, updates: dict,
                           update_user: str = "admin") -> bool:
        """更新自定义函数（按字段名直接更新，tags 需 JSON 序列化后传入）。"""
        import time
        cls._ensure_custom_func_table()
        sets = []
        params: list = []
        for field in ["name", "script", "type", "description", "status", "tags",
                      "params", "result"]:
            if field in updates:
                sets.append(f"{field} = ?")
                params.append(updates[field])
        if not sets:
            return False
        sets.append("update_user = ?")
        params.append(update_user)
        sets.append("update_time = ?")
        params.append(time.time())
        params.append(func_id)
        cursor = cls.execute(
            f"UPDATE custom_funcs SET {', '.join(sets)} WHERE id = ?", tuple(params)
        )
        return cursor.rowcount > 0

    @classmethod
    def update_custom_func_status(cls, func_id: str, status: str) -> bool:
        """更新自定义函数状态。"""
        import time
        cls._ensure_custom_func_table()
        cursor = cls.execute(
            "UPDATE custom_funcs SET status = ?, update_time = ? WHERE id = ?",
            (status, time.time(), func_id),
        )
        return cursor.rowcount > 0

    @classmethod
    def delete_custom_func(cls, func_id: str) -> bool:
        """删除自定义函数。"""
        cls._ensure_custom_func_table()
        cursor = cls.execute(
            "DELETE FROM custom_funcs WHERE id = ?", (func_id,)
        )
        return cursor.rowcount > 0

    @classmethod
    def list_custom_func_status(cls, project_id: str = "") -> List[dict]:
        """列出自定义函数状态（id/name/status）。"""
        cls._ensure_custom_func_table()
        query = "SELECT id, name, status FROM custom_funcs"
        params: list = []
        if project_id:
            query += " WHERE project_id = ?"
            params.append(project_id)
        return cls.query_all(query, tuple(params))

    # ── 项目自定义字段（project_custom_fields 表，存于 tga.db）────────
    @classmethod
    def _ensure_custom_field_table(cls) -> None:
        """确保 project_custom_fields 表存在且列齐全。"""
        conn = Database.get_conn("tga.db")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS project_custom_fields (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                remark TEXT DEFAULT '',
                type TEXT DEFAULT 'INPUT',
                scene TEXT DEFAULT 'FUNCTIONAL',
                scope_id TEXT DEFAULT '',
                internal INTEGER DEFAULT 0,
                enable_option_key INTEGER DEFAULT 0,
                options TEXT DEFAULT '[]',
                used INTEGER DEFAULT 0,
                create_time REAL,
                update_time REAL,
                create_user TEXT DEFAULT 'admin',
                update_user TEXT DEFAULT 'admin'
            )
        """)
        try:
            existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(project_custom_fields)").fetchall()}
            for col, ddl in [
                ("used", "INTEGER DEFAULT 0"),
                ("enable_option_key", "INTEGER DEFAULT 0"),
            ]:
                if col not in existing_cols:
                    conn.execute(f"ALTER TABLE project_custom_fields ADD COLUMN {col} {ddl}")
        except Exception:
            pass
        conn.commit()

    @classmethod
    def list_custom_fields(cls, scope_id: str, scene: str = "") -> List[dict]:
        """列出项目自定义字段。"""
        cls._ensure_custom_field_table()
        query = "SELECT * FROM project_custom_fields WHERE scope_id = ?"
        params: list = [scope_id]
        if scene:
            query += " AND scene = ?"
            params.append(scene)
        query += " ORDER BY update_time ASC"
        return cls.query_all(query, tuple(params))

    @classmethod
    def get_custom_field(cls, field_id: str) -> Optional[dict]:
        """获取单个项目自定义字段。"""
        cls._ensure_custom_field_table()
        return cls.query_one(
            "SELECT * FROM project_custom_fields WHERE id = ?", (field_id,)
        )

    @classmethod
    def upsert_custom_field(cls, field_id: str, body: dict) -> Optional[dict]:
        """新增或更新项目自定义字段，返回原始行。"""
        import json
        import time
        cls._ensure_custom_field_table()
        scene = body.get("scene") or "FUNCTIONAL"
        options = body.get("options") or []
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except (json.JSONDecodeError, TypeError):
                options = []
        enable_key = body.get("enableOptionKey") or body.get("enable_option_key") or False
        now = time.time()
        existing = cls.query_one(
            "SELECT id FROM project_custom_fields WHERE id = ?", (field_id,)
        )
        if existing:
            cls.execute(
                "UPDATE project_custom_fields SET name=?, remark=?, type=?, scene=?, "
                "enable_option_key=?, options=?, update_time=? WHERE id=?",
                (
                    body.get("name", ""), body.get("remark", ""), body.get("type", "INPUT"),
                    scene, 1 if enable_key else 0,
                    json.dumps(options, ensure_ascii=False), now, field_id,
                ),
            )
        else:
            cls.execute(
                "INSERT INTO project_custom_fields (id, name, remark, type, scene, scope_id, "
                "internal, enable_option_key, options, used, create_time, update_time, create_user, update_user) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    field_id, body.get("name", ""), body.get("remark", ""), body.get("type", "INPUT"),
                    scene, body.get("scopeId", ""), 0, 1 if enable_key else 0,
                    json.dumps(options, ensure_ascii=False), 1 if body.get("used") else 0,
                    now, now, body.get("createUser", "admin"), body.get("updateUser", "admin"),
                ),
            )
        return cls.get_custom_field(field_id)

    @classmethod
    def delete_custom_field(cls, field_id: str) -> bool:
        """删除项目自定义字段。"""
        cls._ensure_custom_field_table()
        cursor = cls.execute(
            "DELETE FROM project_custom_fields WHERE id = ?", (field_id,)
        )
        return cursor.rowcount > 0

    @classmethod
    def remove_role_from_all_members(cls, role_id: str) -> int:
        """从所有项目成员的 user_group 列中移除指定角色 ID。"""
        import time as _time

        from app.core.database import Database
        conn = Database.get_conn("projects.db")
        rows = conn.execute(
            "SELECT id, user_group FROM project_members"
        ).fetchall()
        removed = 0
        for row in rows:
            ug = row["user_group"] or ""
            ids = [g.strip() for g in ug.split(",") if g.strip()]
            if role_id in ids:
                ids = [g for g in ids if g != role_id]
                conn.execute(
                    "UPDATE project_members SET user_group = ?, updated_at = ? WHERE id = ?",
                    (",".join(ids), _time.time(), row["id"]),
                )
                removed += 1
        conn.commit()
        return removed

    @classmethod
    def get_custom_func(cls, func_id: str) -> Optional[dict]:
        """按 id 读取项目自定义函数（custom_funcs 表，存于 testcases.db）。"""
        return cls.get_custom_func_row(func_id)


project_repo = ProjectRepo
