"""AI 配置聚合仓储实现（Adapter / Anti-Corruption Layer）。

将既有 AiConfigRepo 模块命令封装为面向 AiConfig 聚合的仓储接口。
"""
from __future__ import annotations

import json
import uuid
from typing import Optional

from app.core.database import Database
from app.domain.ai_config.domain.entities.ai_config import AiConfig
from app.domain.common.entities import Identifier


class AiConfigRepoAdapter:
    """AI 配置聚合的 SQLite 持久化适配器。"""

    db_name = "tga.db"

    def __init__(self) -> None:
        conn = Database.get_conn(self.db_name)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS ai_configs (
                id TEXT PRIMARY KEY,
                scope TEXT NOT NULL,
                config_type TEXT NOT NULL DEFAULT 'default',
                owner TEXT NOT NULL DEFAULT '',
                owner_type TEXT NOT NULL DEFAULT 'PERSONAL',
                project_id TEXT NOT NULL DEFAULT '',
                config TEXT NOT NULL DEFAULT '{}',
                create_user TEXT NOT NULL DEFAULT 'admin',
                create_time REAL NOT NULL,
                update_time REAL NOT NULL,
                UNIQUE(scope, config_type, owner, project_id)
            )"""
        )
        conn.commit()

    def next_id(self) -> str:
        return uuid.uuid4().hex[:16]

    def save(self, config: AiConfig) -> AiConfig:
        """保存聚合，并按业务唯一键执行 upsert。"""
        conn = Database.get_conn(self.db_name)
        now = config.update_time
        conn.execute(
            """INSERT INTO ai_configs
            (id, scope, config_type, owner, owner_type, project_id, config,
             create_user, create_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scope, config_type, owner, project_id) DO UPDATE SET
              id=excluded.id, owner_type=excluded.owner_type,
              config=excluded.config, create_user=excluded.create_user,
              update_time=excluded.update_time""",
            (config.id.value, config.scope, config.config_type, config.owner,
             config.owner_type, config.project_id,
             json.dumps(config.config_value, ensure_ascii=False),
             config.create_user, config.create_time, now),
        )
        conn.commit()
        return config

    def get(self, scope: str, owner: str = "", project_id: str = "",
            config_type: str = "default") -> Optional[AiConfig]:
        """按 scope/owner/project_id 读取。"""
        row = Database.get_conn(self.db_name).execute(
            "SELECT * FROM ai_configs WHERE scope = ? AND config_type = ? "
            "AND owner = ? AND project_id = ?",
            (scope, config_type, owner, project_id),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        try:
            data["config_value"] = json.loads(data.pop("config", "{}"))
        except (TypeError, json.JSONDecodeError):
            data["config_value"] = {}
        return AiConfig.from_dict(data)

    def delete(self, scope: str, owner: str = "", project_id: str = "",
               config_type: str = "default") -> bool:
        """按 scope/owner/project_id 删除。"""
        conn = Database.get_conn(self.db_name)
        cur = conn.execute(
            "DELETE FROM ai_configs WHERE scope = ? AND config_type = ? "
            "AND owner = ? AND project_id = ?",
            (scope, config_type, owner, project_id),
        )
        conn.commit()
        return cur.rowcount > 0
