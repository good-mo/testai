# app/repositories/ai_model_repo.py
"""AI 模型源数据访问层（Phase P2 · auth 占位真实化）。

系统设置 / AI 个人中心的「模型源」持久化唯一数据出口：
  - ai_model_sources 表承载系统模型（owner_type=SYSTEM）与个人模型（owner_type=PERSONAL）
  - 原 `/ai/config/source/list`、`/ai/config/get`、`/ai/config/edit-source`、
    `/ai/config/delete` 均为返回空数组/空对象的占位 stub，现统一落真实表。
"""
import json
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.database import Database
from app.repositories.base import BaseRepo

# 模型类型 / 权限 / 所有者类型枚举（与前端 enums/modelEnum.ts 对齐）
MODEL_TYPE_LLM = "LLM"
MODEL_TYPE_VISION = "VISION"
MODEL_TYPE_AUDIO = "AUDIO"

PERMISSION_PUBLIC = "PUBLIC"
PERMISSION_PRIVATE = "PRIVATE"

OWNER_TYPE_SYSTEM = "SYSTEM"
OWNER_TYPE_PERSONAL = "PERSONAL"


def _now() -> float:
    return time.time()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class AiModelRepo(BaseRepo):
    """AI 模型源仓库。"""

    db_name = "auth.db"
    table_name = "ai_model_sources"

    # 建表守卫：首访连接时懒触发一次建表。
    # 收敛到 get_conn()，覆盖 upsert（先 get 判存在）等冷启动空库路径。
    _schema_ensured = False

    # ── 建表 ──────────────────────────────────────────────
    @classmethod
    def _ensure_table(cls) -> None:
        conn = Database.get_conn(cls.db_name)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_model_sources (
                id TEXT PRIMARY KEY,
                name TEXT DEFAULT '',
                type TEXT DEFAULT 'LLM',
                provider_name TEXT DEFAULT '',
                permission_type TEXT DEFAULT 'PUBLIC',
                status INTEGER DEFAULT 1,
                owner TEXT DEFAULT '',
                owner_type TEXT DEFAULT 'SYSTEM',
                base_name TEXT DEFAULT '',
                app_key TEXT DEFAULT '',
                api_url TEXT DEFAULT '',
                adv_setting TEXT DEFAULT '[]',
                create_user TEXT DEFAULT 'admin',
                create_time REAL,
                update_time REAL
            )
        """)
        conn.commit()

    @classmethod
    def get_conn(cls):
        """返回连接前确保 ai_model_sources 表存在（首访懒触发一次）。

        该表 DDL 在仓库内联，统一经 get_conn() 收敛守卫，让 upsert 等
        未显式建表的方法在冷启动空库下也能自动建表。
        """
        if not cls._schema_ensured:
            cls._ensure_table()
            cls._schema_ensured = True
        return Database.get_conn(cls.db_name)

    # ── 行 <-> dict ──────────────────────────────────────
    @staticmethod
    def _row_to_dict(row: Any) -> Dict[str, Any]:
        adv = row["adv_setting"] or "[]"
        try:
            adv_list = json.loads(adv)
        except Exception:
            adv_list = []
        return {
            "id": row["id"],
            "name": row["name"] or "",
            "type": row["type"] or MODEL_TYPE_LLM,
            "providerName": row["provider_name"] or "",
            "permissionType": row["permission_type"] or PERMISSION_PUBLIC,
            "status": bool(row["status"]),
            "owner": row["owner"] or "",
            "ownerType": (row["owner_type"] or OWNER_TYPE_SYSTEM).strip(),
            "baseName": row["base_name"] or "",
            "appKey": row["app_key"] or "",
            "apiUrl": row["api_url"] or "",
            "advSettingDTOList": adv_list,
            "createUserName": row["create_user"] or "admin",
            "createUser": row["create_user"] or "admin",
            "createTime": int((row["create_time"] or 0) * 1000),
            "updateTime": int((row["update_time"] or 0) * 1000),
        }

    @staticmethod
    def _dict_to_row(data: Dict[str, Any]) -> Dict[str, Any]:
        adv = data.get("advSettingDTOList") or data.get("adv_setting") or []
        if not isinstance(adv, list):
            try:
                adv = json.loads(adv) if isinstance(adv, str) else []
            except Exception:
                adv = []
        return {
            "name": str(data.get("name") or ""),
            "type": str(data.get("type") or MODEL_TYPE_LLM),
            "provider_name": str(data.get("providerName") or data.get("provider_name") or ""),
            "permission_type": str(data.get("permissionType") or data.get("permission_type") or PERMISSION_PUBLIC),
            "status": 1 if data.get("status", True) else 0,
            "owner": str(data.get("owner") or ""),
            "owner_type": str(data.get("ownerType") or data.get("owner_type") or OWNER_TYPE_SYSTEM).strip(),
            "base_name": str(data.get("baseName") or data.get("base_name") or ""),
            "app_key": str(data.get("appKey") or data.get("app_key") or ""),
            "api_url": str(data.get("apiUrl") or data.get("api_url") or ""),
            "adv_setting": json.dumps(adv, ensure_ascii=False),
        }

    # ── 查询 ──────────────────────────────────────────────
    @classmethod
    def list(cls, owner_type: str = OWNER_TYPE_SYSTEM, owner: str = "",
             keyword: str = "", provider_name: str = "") -> List[Dict[str, Any]]:
        """列出模型源；默认系统源，可按所有者/关键字/供应商过滤。"""
        cls._ensure_table()
        conds: List[str] = []
        params: list = []
        if owner_type:
            conds.append("owner_type = ?")
            params.append(owner_type.strip())
        if owner:
            conds.append("owner = ?")
            params.append(owner)
        if provider_name:
            conds.append("provider_name = ?")
            params.append(provider_name)
        if keyword:
            conds.append("(name LIKE ? OR base_name LIKE ?)")
            kw = f"%{keyword}%"
            params.extend([kw, kw])
        sql = "SELECT * FROM ai_model_sources"
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY create_time ASC"
        rows = cls.query_all(sql, tuple(params))
        return [cls._row_to_dict(r) for r in rows]

    @classmethod
    def get(cls, model_id: str) -> Optional[Dict[str, Any]]:
        cls._ensure_table()
        row = cls.query_one(
            "SELECT * FROM ai_model_sources WHERE id = ?", (model_id,)
        )
        return cls._row_to_dict(row) if row else None

    @classmethod
    def get_by_name(cls, name: str, owner_type: str = OWNER_TYPE_SYSTEM) -> Optional[Dict[str, Any]]:
        cls._ensure_table()
        row = cls.query_one(
            "SELECT * FROM ai_model_sources WHERE name = ? AND owner_type = ?",
            (name, owner_type.strip()),
        )
        return cls._row_to_dict(row) if row else None

    # ── 写入 ──────────────────────────────────────────────
    @classmethod
    def create(cls, data: Dict[str, Any], create_user: str = "admin") -> Dict[str, Any]:
        cls._ensure_table()
        row = cls._dict_to_row(data)
        model_id = str(data.get("id") or _new_id())
        now = _now()
        cls.execute(
            """INSERT INTO ai_model_sources
               (id, name, type, provider_name, permission_type, status, owner, owner_type,
                base_name, app_key, api_url, adv_setting, create_user, create_time, update_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                model_id, row["name"], row["type"], row["provider_name"],
                row["permission_type"], row["status"], row["owner"], row["owner_type"],
                row["base_name"], row["app_key"], row["api_url"], row["adv_setting"],
                create_user, now, now,
            ),
        )
        return cls.get(model_id) or {}

    @classmethod
    def update(cls, model_id: str, data: Dict[str, Any],
               update_user: str = "admin") -> Optional[Dict[str, Any]]:
        cls._ensure_table()
        existing = cls.get(model_id)
        if not existing:
            return None
        row = cls._dict_to_row(data)
        cls.execute(
            """UPDATE ai_model_sources SET
                 name=?, type=?, provider_name=?, permission_type=?, status=?, owner=?,
                 owner_type=?, base_name=?, app_key=?, api_url=?, adv_setting=?, update_time=?
               WHERE id=?""",
            (
                row["name"], row["type"], row["provider_name"], row["permission_type"],
                row["status"], row["owner"], row["owner_type"], row["base_name"],
                row["app_key"], row["api_url"], row["adv_setting"], _now(), model_id,
            ),
        )
        if update_user:
            cls.execute(
                "UPDATE ai_model_sources SET create_user=? WHERE id=?",
                (update_user, model_id),
            )
        return cls.get(model_id)

    @classmethod
    def upsert(cls, data: Dict[str, Any], create_user: str = "admin") -> Dict[str, Any]:
        """按 id 存在则更新、否则创建（兼容 edit-source 无 id 的新建语义）。"""
        model_id = str(data.get("id") or "")
        if model_id and cls.get(model_id):
            updated = cls.update(model_id, data, update_user=create_user)
            return updated or {}
        return cls.create(data, create_user=create_user)

    @classmethod
    def delete(cls, model_id: str) -> bool:
        cls._ensure_table()
        return cls.execute(
            "DELETE FROM ai_model_sources WHERE id = ?", (model_id,)
        ).rowcount > 0

    @classmethod
    def count_enabled(cls, owner_type: str = OWNER_TYPE_SYSTEM) -> int:
        cls._ensure_table()
        row = cls.query_one(
            "SELECT COUNT(*) AS cnt FROM ai_model_sources WHERE owner_type=? AND status=1",
            (owner_type.strip(),),
        )
        return row["cnt"] if row else 0


ai_model_repo = AiModelRepo
