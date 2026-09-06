"""模板聚合仓储实现（去 Adapter，直接 SQL）。

修复说明：
  - 消除 TemplateRepoAdapter 中间层（只做 entity↔dict 翻译，无业务逻辑）
  - 把 template_repo 的 SQL 移入此处，成为域内私有实现
  - 聚合重建（from_dict）与持久化在同一个文件内闭环，不再跨文件翻译

修复前调用链：AppService → TemplateRepoAdapter → TemplateRepo → SQLite（4 层）
修复后调用链：AppService → TemplateRepositoryImpl → SQLite（2 层）
"""
from __future__ import annotations

import json
import time
import uuid
from typing import List, Optional

from app.core.database import Database
from app.domain.template.domain.entities.template import Template
from app.logging_config import get_logger

logger = get_logger(__name__)

# ── 域内常量 ──────────────────────────────────────────
DB_NAME = "tga.db"
TABLE = "templates"


class TemplateRepositoryImpl:
    """模板仓储：直接持有 SQL，不再委托 Flat Repository。"""

    def __init__(self):
        self._ensure_table()

    @staticmethod
    def _conn():
        return Database.get_conn(DB_NAME)

    # ── 建表 ──────────────────────────────────────────────
    @classmethod
    def _ensure_table(cls) -> None:
        """幂等建表。"""
        conn = cls._conn()
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

    # ── 聚合重建 ──────────────────────────────────────────
    @staticmethod
    def _row_to_entity(row: dict) -> Template:
        """数据库行 → 聚合根实体。"""
        d = dict(row)
        # 反序列化 JSON 文本字段
        for k in ("custom_fields", "system_fields", "upload_img_file_ids"):
            if isinstance(d.get(k), str):
                try:
                    d[k] = json.loads(d[k])
                except (json.JSONDecodeError, TypeError):
                    d[k] = []
        return Template.from_dict(d)

    # ── 读 ────────────────────────────────────────────────
    def list_templates(self, scope_type: str, scope_id: str,
                       scene: str = "") -> List[Template]:
        query = "SELECT * FROM templates WHERE scope_type = ? AND scope_id = ?"
        params: list = [scope_type, scope_id]
        if scene:
            query += " AND scene = ?"
            params.append(scene)
        query += " ORDER BY create_time ASC"
        rows = self._conn().execute(query, tuple(params)).fetchall()
        return [self._row_to_entity(dict(r)) for r in rows]

    def get_template(self, template_id: str) -> Optional[Template]:
        row = self._conn().execute(
            "SELECT * FROM templates WHERE id = ?", (template_id,)
        ).fetchone()
        return self._row_to_entity(dict(row)) if row else None

    def count_in_scope(self, scope_type: str, scope_id: str, scene: str) -> int:
        row = self._conn().execute(
            "SELECT COUNT(*) AS c FROM templates WHERE scope_type=? AND scope_id=? AND scene=?",
            (scope_type, scope_id, scene),
        ).fetchone()
        return row["c"] if row else 0

    # ── 写 ────────────────────────────────────────────────
    def upsert_template(self, template: Template) -> Optional[Template]:
        """新增或更新模板，返回聚合根。"""
        d = template.to_dict()
        # 平台默认标记兼容
        platform_default = d.get("platformDefault", d.get("platform_default", False))
        now = time.time()
        conn = self._conn()

        existing = conn.execute(
            "SELECT id FROM templates WHERE id = ?", (str(template.id.value),)
        ).fetchone()

        custom_fields = json.dumps(template._custom_fields, ensure_ascii=False)
        system_fields = json.dumps(template._system_fields, ensure_ascii=False)
        upload_ids = json.dumps(template._upload_img_file_ids, ensure_ascii=False)

        if existing:
            conn.execute(
                "UPDATE templates SET name=?, remark=?, scene=?, scope_id=?, "
                "enable_third_part=?, internal=?, custom_fields=?, system_fields=?, "
                "upload_img_file_ids=?, update_time=?, update_user=? WHERE id=?",
                (
                    template._name, template._remark, template._scene.value,
                    template._scope_id,
                    1 if template._enable_third_part else 0,
                    1 if template._internal else 0,
                    custom_fields, system_fields, upload_ids,
                    now, template._update_user,
                    str(template.id.value),
                ),
            )
        else:
            conn.execute(
                "INSERT INTO templates (id, name, remark, scene, scope_type, scope_id, "
                "internal, enable_default, enable_third_part, ref_id, platform_default, "
                "custom_fields, system_fields, upload_img_file_ids, create_time, update_time, "
                "create_user, update_user) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    str(template.id.value), template._name, template._remark,
                    template._scene.value, template._scope_type.value, template._scope_id,
                    1 if template._internal else 0,
                    1 if template._enable_default else 0,
                    1 if template._enable_third_part else 0,
                    template._ref_id,
                    1 if platform_default else 0,
                    custom_fields, system_fields, upload_ids,
                    now, now,
                    template._create_user, template._update_user,
                ),
            )
        conn.commit()
        return self.get_template(str(template.id.value))

    def delete_template(self, template_id: str) -> bool:
        cursor = self._conn().execute(
            "DELETE FROM templates WHERE id = ?", (template_id,)
        )
        self._conn().commit()
        return cursor.rowcount > 0

    def set_default(self, scope_type: str, scope_id: str, scene: str,
                    template_id: str) -> bool:
        """将指定模板设为范围内默认模板，并清除其余默认标记。"""
        with Database.transaction(DB_NAME) as conn:
            conn.execute(
                "UPDATE templates SET enable_default=0 WHERE scope_type=? AND scope_id=? AND scene=?",
                (scope_type, scope_id, scene),
            )
            cursor = conn.execute(
                "UPDATE templates SET enable_default=1 WHERE id=? AND scope_type=? AND scope_id=? AND scene=?",
                (template_id, scope_type, scope_id, scene),
            )
        return cursor.rowcount > 0

    def seed_default(self, scope_type: str, scope_id: str, scene: str,
                     name: str) -> Optional[Template]:
        """范围内无模板时，落一条系统默认模板。"""
        if self.count_in_scope(scope_type, scope_id, scene) > 0:
            return None
        template_id = str(uuid.uuid4())
        now = time.time()
        conn = self._conn()
        conn.execute(
            "INSERT INTO templates (id, name, remark, scene, scope_type, scope_id, "
            "internal, enable_default, custom_fields, system_fields, upload_img_file_ids, "
            "create_time, update_time, create_user, update_user) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                template_id, name, "系统默认模板", scene, scope_type, scope_id,
                1, 1, "[]", "[]", "[]",
                now, now, "admin", "admin",
            ),
        )
        conn.commit()
        return self.get_template(template_id)


# 模块级单例
template_repository = TemplateRepositoryImpl()

__all__ = ["TemplateRepositoryImpl", "template_repository"]
