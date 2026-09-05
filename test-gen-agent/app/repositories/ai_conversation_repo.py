# app/repositories/ai_conversation_repo.py
"""AI 对话数据访问层（Phase P2 · AI 对话 stub 真实化）。

为 ms-ai-drawer 前端「AI 对话」提供真实持久化承载：
  - ai_conversations  对话主表（list / detail / delete / update-title / add）
  - ai_conversation_messages  会话内消息历史（chat 后追加 user/assistant 消息）

原 ai_config.py 中相关接口均为返回 None / [] 的空壳 stub，
现统一落真实表，前端会话列表 / 历史加载不再为空。
"""
import json
import time
import uuid
from typing import Any, Dict, List, Optional

from app.repositories.base import BaseRepo


def _now() -> float:
    return time.time()


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


class AiConversationRepo(BaseRepo):
    """AI 对话仓库（主表 + 消息表）。"""

    db_name = "tga.db"
    table_name = "ai_conversations"

    # ── 建表 ──────────────────────────────────────────────
    @classmethod
    def _ensure_table(cls) -> None:
        conn = cls.get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_conversations (
                id TEXT PRIMARY KEY,
                title TEXT DEFAULT '新对话',
                owner TEXT DEFAULT '',
                owner_type TEXT DEFAULT 'PERSONAL',
                project_id TEXT DEFAULT '',
                module_type TEXT DEFAULT 'ai',
                meta TEXT DEFAULT '{}',
                create_user TEXT DEFAULT 'admin',
                create_time REAL,
                update_time REAL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ai_conv_owner
                ON ai_conversations(owner, create_time DESC)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_conversation_messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT DEFAULT '',
                role TEXT DEFAULT 'user',
                type TEXT DEFAULT 'text',
                content TEXT DEFAULT '',
                message_meta TEXT DEFAULT '{}',
                create_time REAL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ai_msg_conv
                ON ai_conversation_messages(conversation_id, create_time ASC)
        """)
        conn.commit()

    # ── 行 <-> dict ──────────────────────────────────────
    @staticmethod
    def _conv_to_dict(row: Any) -> Dict[str, Any]:
        meta = row["meta"] or "{}"
        try:
            meta_dict = json.loads(meta)
        except Exception:
            meta_dict = {}
        return {
            "id": row["id"],
            "title": row["title"] or "新对话",
            "owner": row["owner"] or "",
            "ownerType": (row["owner_type"] or "PERSONAL").strip(),
            "projectId": row["project_id"] or "",
            "moduleType": row["module_type"] or "ai",
            **meta_dict,
            "createUser": row["create_user"] or "admin",
            "createTime": int((row["create_time"] or 0) * 1000),
            "updateTime": int((row["update_time"] or 0) * 1000),
        }

    @staticmethod
    def _msg_to_dict(row: Any) -> Dict[str, Any]:
        msg_meta = row["message_meta"] or "{}"
        try:
            meta_dict = json.loads(msg_meta)
        except Exception:
            meta_dict = {}
        return {
            "id": row["id"],
            "conversationId": row["conversation_id"] or "",
            "role": row["role"] or "user",
            "type": row["type"] or "text",
            "content": row["content"] or "",
            "timestamp": int((row["create_time"] or 0) * 1000),
            **meta_dict,
        }

    # ── 对话：列表 ───────────────────────────────────────
    @classmethod
    def list_conversations(cls, owner: str = "",
                           owner_type: str = "PERSONAL",
                           module_type: str = "") -> List[Dict[str, Any]]:
        cls._ensure_table()
        conds: List[str] = []
        params: list = []
        if owner:
            conds.append("owner = ?")
            params.append(owner)
        if owner_type:
            conds.append("owner_type = ?")
            params.append(owner_type)
        if module_type:
            conds.append("module_type = ?")
            params.append(module_type)
        sql = "SELECT * FROM ai_conversations"
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY create_time DESC"
        rows = cls.query_all(sql, tuple(params))
        return [cls._conv_to_dict(r) for r in rows]

    @classmethod
    def get_conversation(cls, conversation_id: str) -> Optional[Dict[str, Any]]:
        cls._ensure_table()
        row = cls.query_one(
            "SELECT * FROM ai_conversations WHERE id = ?", (conversation_id,)
        )
        return cls._conv_to_dict(row) if row else None

    @classmethod
    def create_conversation(cls, title: str = "新对话",
                            owner: str = "", create_user: str = "admin",
                            project_id: str = "", module_type: str = "ai",
                            extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        cls._ensure_table()
        conv_id = _new_id()
        now = _now()
        meta = json.dumps(extra or {}, ensure_ascii=False)
        cls.execute(
            """INSERT INTO ai_conversations
               (id, title, owner, owner_type, project_id, module_type, meta,
                create_user, create_time, update_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (conv_id, title, owner, "PERSONAL", project_id, module_type,
             meta, create_user, now, now),
        )
        return cls.get_conversation(conv_id) or {}

    @classmethod
    def update_conversation(cls, conversation_id: str,
                            title: Optional[str] = None,
                            extra: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        cls._ensure_table()
        existing = cls.get_conversation(conversation_id)
        if not existing:
            return None
        sets: List[str] = ["update_time = ?"]
        params: list = [_now()]
        if title is not None:
            sets.append("title = ?")
            params.append(title)
        if extra is not None:
            try:
                old_meta = existing.get("__meta") or {}
            except Exception:
                old_meta = {}
            merged = {**old_meta, **extra}
            sets.append("meta = ?")
            params.append(json.dumps(merged, ensure_ascii=False))
        params.append(conversation_id)
        cls.execute(
            f"UPDATE ai_conversations SET {', '.join(sets)} WHERE id = ?",
            tuple(params),
        )
        return cls.get_conversation(conversation_id)

    @classmethod
    def delete_conversation(cls, conversation_id: str) -> bool:
        cls._ensure_table()
        cls.execute(
            "DELETE FROM ai_conversation_messages WHERE conversation_id = ?",
            (conversation_id,),
        )
        return cls.execute(
            "DELETE FROM ai_conversations WHERE id = ?", (conversation_id,)
        ).rowcount > 0

    # ── 消息 ─────────────────────────────────────────────
    @classmethod
    def add_message(cls, conversation_id: str, role: str = "user",
                    content: str = "", msg_type: str = "text",
                    extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        cls._ensure_table()
        msg_id = _new_id()
        now = _now()
        meta = json.dumps(extra or {}, ensure_ascii=False)
        cls.execute(
            """INSERT INTO ai_conversation_messages
               (id, conversation_id, role, type, content, message_meta, create_time)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (msg_id, conversation_id, role, msg_type, content, meta, now),
        )
        row = cls.query_one(
            "SELECT * FROM ai_conversation_messages WHERE id = ?", (msg_id,)
        )
        return cls._msg_to_dict(row) if row else {}

    @classmethod
    def list_messages(cls, conversation_id: str) -> List[Dict[str, Any]]:
        cls._ensure_table()
        rows = cls.query_all(
            """SELECT * FROM ai_conversation_messages
               WHERE conversation_id = ? ORDER BY create_time ASC""",
            (conversation_id,),
        )
        return [cls._msg_to_dict(r) for r in rows]
