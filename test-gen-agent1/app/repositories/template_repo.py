# app/repositories/template_repo.py
"""项目/组织模板数据访问层。

为前端「模板管理」提供真实持久化，替代原先返回空对象/未落库的桩实现：
  - /project/template/list/{projectId}/{scene}   应返回模板数组
  - /project/template/get/{id}                   应返回完整模板详情
  - /project/template/add|update|delete|set-default  需真实落库

模板按 (scope_type + scope_id + scene) 组织，同一范围内每条模板对应一次
启用配置状态；表存于 tga.db（与 project_custom_fields 同库）。
"""
import json
import time
from typing import List, Optional

from app.core.database import Database


class TemplateRepo:
    """模板数据访问（项目/组织通用）。"""

    @classmethod
    def _ensure_table(cls) -> None:
        conn = Database.get_conn("tga.db")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                remark TEXT DEFAULT '',
                scene TEXT DEFAULT 'FUNCTIONAL',
                scope_type TEXT DEFAULT 'PROJECT',
                scope_id TEXT DEFAULT '',
                internal INTEGER DEFAULT 0,
                enable_default INTEGER DEFAULT 0,
                enable_third_part INTEGER DEFAULT 0,
                ref_id TEXT DEFAULT '',
                platform_default INTEGER DEFAULT 0,
                custom_fields TEXT DEFAULT '[]',
                system_fields TEXT DEFAULT '[]',
                upload_img_file_ids TEXT DEFAULT '[]',
                create_time REAL,
                update_time REAL,
                create_user TEXT DEFAULT 'admin',
                update_user TEXT DEFAULT 'admin'
            )
        """)
        conn.commit()

    @classmethod
    def list_templates(cls, scope_type: str, scope_id: str, scene: str = "") -> List[dict]:
        cls._ensure_table()
        query = "SELECT * FROM templates WHERE scope_type = ? AND scope_id = ?"
        params: list = [scope_type, scope_id]
        if scene:
            query += " AND scene = ?"
            params.append(scene)
        query += " ORDER BY create_time ASC"
        conn = Database.get_conn("tga.db")
        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def get_template(cls, template_id: str) -> Optional[dict]:
        cls._ensure_table()
        conn = Database.get_conn("tga.db")
        row = conn.execute(
            "SELECT * FROM templates WHERE id = ?", (template_id,)
        ).fetchone()
        return dict(row) if row else None

    @classmethod
    def count_in_scope(cls, scope_type: str, scope_id: str, scene: str) -> int:
        cls._ensure_table()
        conn = Database.get_conn("tga.db")
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM templates WHERE scope_type=? AND scope_id=? AND scene=?",
            (scope_type, scope_id, scene),
        ).fetchone()
        return row["c"] if row else 0

    @classmethod
    def upsert_template(cls, template_id: str, body: dict, scope_type: str) -> Optional[dict]:
        """新增或更新模板，返回原始行。"""
        cls._ensure_table()
        scope_id = body.get("scopeId") or body.get("scope_id") or ""
        scene = body.get("scene") or "FUNCTIONAL"
        custom_fields = body.get("customFields") or body.get("custom_fields") or []
        system_fields = body.get("systemFields") or body.get("system_fields") or []
        upload_ids = body.get("uploadImgFileIds") or body.get("upload_img_file_ids") or []
        now = time.time()
        conn = Database.get_conn("tga.db")
        existing = conn.execute(
            "SELECT id FROM templates WHERE id = ?", (template_id,)
        ).fetchone()
        name = body.get("name", "未命名模板")
        remark = body.get("remark", "")
        if existing:
            conn.execute(
                "UPDATE templates SET name=?, remark=?, scene=?, scope_id=?, "
                "enable_third_part=?, internal=?, custom_fields=?, system_fields=?, "
                "upload_img_file_ids=?, update_time=?, update_user=? WHERE id=?",
                (
                    name, remark, scene, scope_id,
                    1 if body.get("enableThirdPart") else 0,
                    1 if body.get("internal") else 0,
                    json.dumps(custom_fields, ensure_ascii=False),
                    json.dumps(system_fields, ensure_ascii=False),
                    json.dumps(upload_ids, ensure_ascii=False),
                    now, body.get("updateUser") or body.get("createUser") or "admin",
                    template_id,
                ),
            )
        else:
            conn.execute(
                "INSERT INTO templates (id, name, remark, scene, scope_type, scope_id, "
                "internal, enable_default, enable_third_part, ref_id, platform_default, "
                "custom_fields, system_fields, upload_img_file_ids, create_time, update_time, "
                "create_user, update_user) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    template_id, name, remark, scene, scope_type, scope_id,
                    1 if body.get("internal") else 0,
                    1 if body.get("enableDefault") or body.get("enable_default") else 0,
                    1 if body.get("enableThirdPart") else 0,
                    body.get("refId") or "",
                    1 if body.get("enablePlatformDefault") else 0,
                    json.dumps(custom_fields, ensure_ascii=False),
                    json.dumps(system_fields, ensure_ascii=False),
                    json.dumps(upload_ids, ensure_ascii=False),
                    now, now,
                    body.get("createUser") or "admin",
                    body.get("updateUser") or body.get("createUser") or "admin",
                ),
            )
        conn.commit()
        return cls.get_template(template_id)

    @classmethod
    def delete_template(cls, template_id: str) -> bool:
        cls._ensure_table()
        conn = Database.get_conn("tga.db")
        cursor = conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        conn.commit()
        return cursor.rowcount > 0

    @classmethod
    def set_default(cls, scope_type: str, scope_id: str, scene: str, template_id: str) -> bool:
        """将指定模板设为范围内默认模板，并清除其余默认标记。"""
        cls._ensure_table()
        with Database.transaction("tga.db") as conn:
            conn.execute(
                "UPDATE templates SET enable_default=0 WHERE scope_type=? AND scope_id=? AND scene=?",
                (scope_type, scope_id, scene),
            )
            cursor = conn.execute(
                "UPDATE templates SET enable_default=1 WHERE id=? AND scope_type=? AND scope_id=? AND scene=?",
                (template_id, scope_type, scope_id, scene),
            )
        return cursor.rowcount > 0

    @classmethod
    def seed_default(cls, scope_type: str, scope_id: str, scene: str, name: str) -> Optional[dict]:
        """范围内无模板时，落一条系统默认模板，保证模板管理列表非空。"""
        if cls.count_in_scope(scope_type, scope_id, scene) > 0:
            return None
        return cls.upsert_template(
            str(__import__("uuid").uuid4()),
            {
                "name": name,
                "remark": "系统默认模板",
                "scene": scene,
                "scopeId": scope_id,
                "internal": 1,
                "enableDefault": 1,
                "customFields": [],
                "systemFields": [],
            },
            scope_type,
        )
