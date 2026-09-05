# app/repositories/ai_config_repo.py
"""AI 用例生成配置数据访问层（Phase P2 · stub 真实化）。

为「功能用例 AI 配置」与「接口用例 AI 配置」提供真实持久化承载：
  - ai_configs  通用配置表（scope + owner + config_type 区分不同用途）

原 functional_cases_extra.py / apitest_compat_case.py 中：
  - /functional/case/ai/get/config → 空 {}
  - /functional/case/ai/save/config → None
  - /api/case/ai/get/config → 空 {}
  - /api/case/ai/save/config → None
现统一落真实表，读回 / 保存不再为空 / 丢失。
"""
import json
import time
import uuid
from typing import Any, Dict, Optional

from app.repositories.base import BaseRepo


def _now() -> float:
    return time.time()


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


# ── 配置 scope / config_type ───────────────────────────────
SCOPE_FUNCTIONAL_CASE = "functional_case"   # /functional/case/ai/*
SCOPE_API_CASE = "api_case"                 # /api/case/ai/*


class AiConfigRepo(BaseRepo):
    """AI 用例生成配置仓库。"""

    db_name = "tga.db"
    table_name = "ai_configs"

    @classmethod
    def _ensure_table(cls) -> None:
        conn = cls.get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_configs (
                id TEXT PRIMARY KEY,
                scope TEXT DEFAULT '',
                config_type TEXT DEFAULT '',
                owner TEXT DEFAULT '',
                owner_type TEXT DEFAULT 'PERSONAL',
                project_id TEXT DEFAULT '',
                config_value TEXT DEFAULT '{}',
                create_user TEXT DEFAULT 'admin',
                create_time REAL,
                update_time REAL
            )
        """)
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_config_unique
                ON ai_configs(scope, config_type, owner, project_id)
        """)
        conn.commit()

    @classmethod
    def _to_dict(cls, row: Any) -> Dict[str, Any]:
        val = row["config_value"] or "{}"
        try:
            cfg = json.loads(val)
        except Exception:
            cfg = {}
        return {
            "id": row["id"],
            "scope": row["scope"] or "",
            "configType": row["config_type"] or "",
            "owner": row["owner"] or "",
            "ownerType": (row["owner_type"] or "PERSONAL").strip(),
            "projectId": row["project_id"] or "",
            "config": cfg if isinstance(cfg, dict) else {},
            "createUser": row["create_user"] or "admin",
            "createTime": int((row["create_time"] or 0) * 1000),
            "updateTime": int((row["update_time"] or 0) * 1000),
        }

    @classmethod
    def get(cls, scope: str, config_type: str = "default",
            owner: str = "", project_id: str = "") -> Optional[Dict[str, Any]]:
        """按 scope + config_type + owner（可选 project）读取配置。"""
        cls._ensure_table()
        row = cls.query_one(
            """SELECT * FROM ai_configs
               WHERE scope = ? AND config_type = ? AND owner = ? AND project_id = ?
               ORDER BY update_time DESC LIMIT 1""",
            (scope, config_type, owner, project_id),
        )
        return cls._to_dict(row) if row else None

    @classmethod
    def save(cls, scope: str, config_value: Dict[str, Any],
             config_type: str = "default", owner: str = "",
             project_id: str = "", create_user: str = "admin") -> Dict[str, Any]:
        """按 scope + owner 存在则更新、否则创建。"""
        cls._ensure_table()
        existing = cls.get(scope, config_type, owner, project_id)
        val_json = json.dumps(config_value or {}, ensure_ascii=False)
        now = _now()
        if existing:
            cls.execute(
                """UPDATE ai_configs SET config_value=?, update_time=?, create_user=?,
                       project_id=?, owner_type='PERSONAL'
                   WHERE scope=? AND config_type=? AND owner=? AND project_id=?""",
                (val_json, now, create_user, project_id,
                 scope, config_type, owner, project_id),
            )
            row = cls.query_one(
                "SELECT * FROM ai_configs WHERE id = ?", (existing["id"],)
            )
        else:
            cfg_id = _new_id()
            cls.execute(
                """INSERT INTO ai_configs
                   (id, scope, config_type, owner, owner_type, project_id,
                    config_value, create_user, create_time, update_time)
                   VALUES (?, ?, ?, ?, 'PERSONAL', ?, ?, ?, ?, ?)""",
                (cfg_id, scope, config_type, owner, project_id,
                 val_json, create_user, now, now),
            )
            row = cls.query_one(
                "SELECT * FROM ai_configs WHERE id = ?", (cfg_id,)
            )
        return cls._to_dict(row) if row else {}

    @classmethod
    def delete(cls, scope: str, config_type: str = "default",
               owner: str = "", project_id: str = "") -> bool:
        cls._ensure_table()
        return cls.execute(
            """DELETE FROM ai_configs
               WHERE scope=? AND config_type=? AND owner=? AND project_id=?""",
            (scope, config_type, owner, project_id),
        ).rowcount > 0


# ── 默认配置（与前端 models/ai.ts 对齐）────────────────────
def default_case_ai_config() -> Dict[str, Any]:
    """功能用例 AI 默认配置（对应前端 CaseAiChatConfig）。"""
    return {
        "designConfig": {
            "normal": True,
            "abnormal": True,
            "equivalenceClassPartitioning": True,
            "boundaryValueAnalysis": True,
            "decisionTableTesting": True,
            "causeEffectGraphing": True,
            "orthogonalExperimentMethod": True,
            "scenarioMethod": True,
            "scenarioMethodDescription": "",
        },
        "templateConfig": {
            "caseEditType": "TEXT",
            "caseName": True,
            "preCondition": True,
            "caseSteps": True,
            "expectedResult": True,
            "remark": True,
        },
    }


def default_api_ai_config() -> Dict[str, Any]:
    """接口用例 AI 默认配置（对应前端 ApiAiChatConfig）。"""
    return {
        "normal": True,
        "abnormal": True,
        "caseName": True,
        "requestParams": True,
        "preScript": True,
        "postScript": True,
        "assertion": True,
    }


def merge_case_ai_config(saved: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """合并保存值到默认结构，确保字段完整（前端直接读 config 属性）。"""
    base = default_case_ai_config()
    if not saved:
        return base
    cfg = saved.get("config") or {}
    for section in ("designConfig", "templateConfig"):
        saved_section = cfg.get(section)
        if isinstance(saved_section, dict):
            base[section].update(saved_section)
    return base


def merge_api_ai_config(saved: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """合并保存值到默认结构（布尔字段兜底）。"""
    base = default_api_ai_config()
    if not saved:
        return base
    cfg = saved.get("config") or {}
    for key in base:
        if key in cfg:
            base[key] = bool(cfg[key])
    return base
