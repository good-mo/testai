# app/repositories/message_repo.py
"""消息通知 / 消息管理 数据访问层（Phase 3 四层对齐）。

承载三类数据（统一存于 tga.db）：
  - project_robots   项目消息机器人（站内信/邮件为系统内置，不落库）
  - message_tasks    消息设置（模块×事件×机器人 的接收人与模板）
  - notifications    站内消息（通知中心列表 / 已读 / 未读数）
"""
import json
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.database import Database
from app.repositories.base import BaseRepo


def _now() -> float:
    return time.time()


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


def _bool(v: Any) -> int:
    if isinstance(v, str):
        return 0 if v.lower() in ("false", "0", "no", "") else 1
    return 1 if v else 0


class MessageRepo(BaseRepo):
    """消息域数据访问层。"""

    db_name = "tga.db"

    # ── 建表 ─────────────────────────────────────────────
    _SCHEMAS = """
        CREATE TABLE IF NOT EXISTS project_robots (
            id TEXT PRIMARY KEY,
            project_id TEXT DEFAULT '',
            name TEXT DEFAULT '',
            platform TEXT DEFAULT 'CUSTOM',
            type TEXT DEFAULT 'CUSTOM',
            webhook TEXT DEFAULT '',
            app_key TEXT DEFAULT '',
            app_secret TEXT DEFAULT '',
            enable INTEGER DEFAULT 1,
            description TEXT DEFAULT '',
            create_user TEXT DEFAULT 'admin',
            create_time REAL,
            update_user TEXT DEFAULT 'admin',
            update_time REAL
        );
        CREATE INDEX IF NOT EXISTS idx_robots_project ON project_robots(project_id);

        CREATE TABLE IF NOT EXISTS message_tasks (
            id TEXT PRIMARY KEY,
            project_id TEXT DEFAULT '',
            task_type TEXT DEFAULT '',
            event TEXT DEFAULT '',
            robot_id TEXT DEFAULT '',
            receiver_ids TEXT DEFAULT '[]',
            subject TEXT DEFAULT '',
            template TEXT DEFAULT '',
            use_default_subject INTEGER DEFAULT 1,
            use_default_template INTEGER DEFAULT 1,
            enable INTEGER DEFAULT 0,
            create_time REAL,
            update_time REAL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_msg_task_unique
            ON message_tasks(project_id, task_type, event, robot_id);

        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY,
            type TEXT DEFAULT 'message',
            title TEXT DEFAULT '',
            sub_title TEXT DEFAULT '',
            content TEXT DEFAULT '',
            avatar TEXT DEFAULT '',
            resource_type TEXT DEFAULT '',
            resource_id TEXT DEFAULT '',
            resource_name TEXT DEFAULT '',
            operation TEXT DEFAULT '',
            receiver TEXT DEFAULT '',
            operator TEXT DEFAULT '',
            project_id TEXT DEFAULT '',
            organization_id TEXT DEFAULT '',
            status TEXT DEFAULT 'UNREAD',
            create_time REAL
        );
        CREATE INDEX IF NOT EXISTS idx_notifications_receiver ON notifications(receiver, status);
        CREATE INDEX IF NOT EXISTS idx_notifications_project ON notifications(project_id);
    """

    @classmethod
    def ensure_tables(cls) -> None:
        conn = cls.get_conn()
        for stmt in cls._SCHEMAS.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(stmt)
        conn.commit()

    # ════════════════════════════════════════════════════
    # 机器人
    # ════════════════════════════════════════════════════
    @classmethod
    def list_robots(cls, project_id: str = "") -> List[Dict[str, Any]]:
        cls.ensure_tables()
        conn = cls.get_conn()
        if project_id:
            rows = conn.execute(
                "SELECT * FROM project_robots WHERE project_id = ? OR project_id = '' ORDER BY create_time ASC",
                (project_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM project_robots ORDER BY create_time ASC"
            ).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def get_robot(cls, robot_id: str) -> Optional[Dict[str, Any]]:
        cls.ensure_tables()
        return cls.query_one("SELECT * FROM project_robots WHERE id = ?", (robot_id,))

    @classmethod
    def create_robot(cls, data: dict) -> Dict[str, Any]:
        cls.ensure_tables()
        rid = data.get("id") or _new_id()
        now = _now()
        cls.execute(
            """INSERT INTO project_robots
               (id, project_id, name, platform, type, webhook, app_key, app_secret,
                enable, description, create_user, create_time, update_user, update_time)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                rid,
                data.get("project_id", "") or data.get("projectId", ""),
                data.get("name", "未命名机器人"),
                data.get("platform", "CUSTOM"),
                data.get("type", "CUSTOM"),
                data.get("webhook", ""),
                data.get("app_key", "") or data.get("appKey", ""),
                data.get("app_secret", "") or data.get("appSecret", ""),
                _bool(data.get("enable", True)),
                data.get("description", ""),
                data.get("create_user", "admin") or data.get("createUser", "admin"),
                now,
                data.get("update_user", "admin") or data.get("updateUser", "admin"),
                now,
            ),
        )
        return cls.get_robot(rid) or {"id": rid}

    @classmethod
    def update_robot(cls, robot_id: str, data: dict) -> bool:
        cls.ensure_tables()
        allowed = ("name", "platform", "type", "webhook", "app_key",
                   "app_secret", "enable", "description", "update_user")
        # 兼容驼峰字段
        mapping = {
            "project_id": None, "projectId": None, "name": "name",
            "platform": "platform", "type": "type", "webhook": "webhook",
            "appKey": "app_key", "app_key": "app_key",
            "appSecret": "app_secret", "app_secret": "app_secret",
            "enable": "enable", "description": "description",
            "updateUser": "update_user", "update_user": "update_user",
        }
        sets = []
        params = []
        for k, v in data.items():
            col = mapping.get(k)
            if not col or col not in allowed:
                continue
            if col == "enable":
                v = _bool(v)
            sets.append(f"{col} = ?")
            params.append(v)
        if not sets:
            return False
        sets.append("update_time = ?")
        params.append(_now())
        params.append(robot_id)
        cursor = cls.execute(
            f"UPDATE project_robots SET {', '.join(sets)} WHERE id = ?", tuple(params)
        )
        return cursor.rowcount > 0

    @classmethod
    def delete_robot(cls, robot_id: str) -> bool:
        cls.ensure_tables()
        with Database.transaction(cls.db_name) as conn:
            cursor = conn.execute("DELETE FROM project_robots WHERE id = ?", (robot_id,))
            # 同步清理该机器人在消息设置中的配置
            conn.execute("DELETE FROM message_tasks WHERE robot_id = ?", (robot_id,))
        return cursor.rowcount > 0

    @classmethod
    def set_robot_enable(cls, robot_id: str, enable: bool) -> bool:
        cls.ensure_tables()
        cursor = cls.execute(
            "UPDATE project_robots SET enable = ?, update_time = ? WHERE id = ?",
            (_bool(enable), _now(), robot_id),
        )
        return cursor.rowcount > 0

    # ════════════════════════════════════════════════════
    # 消息设置（机器人 × 事件 模板/接收人）
    # ════════════════════════════════════════════════════
    @classmethod
    def list_tasks(cls, project_id: str = "", task_type: str = "",
                   robot_id: str = "") -> List[Dict[str, Any]]:
        cls.ensure_tables()
        sql = "SELECT * FROM message_tasks WHERE 1=1"
        params: list = []
        if project_id:
            sql += " AND project_id = ?"
            params.append(project_id)
        if task_type:
            sql += " AND task_type = ?"
            params.append(task_type)
        if robot_id:
            sql += " AND robot_id = ?"
            params.append(robot_id)
        sql += " ORDER BY create_time ASC"
        rows = cls.query_all(sql, tuple(params))
        for r in rows:
            try:
                r["receiver_ids"] = json.loads(r.get("receiver_ids") or "[]")
            except (ValueError, TypeError):
                r["receiver_ids"] = []
        return rows

    @classmethod
    def get_task(cls, project_id: str, task_type: str, event: str,
                 robot_id: str) -> Optional[Dict[str, Any]]:
        cls.ensure_tables()
        row = cls.query_one(
            "SELECT * FROM message_tasks WHERE project_id = ? AND task_type = ? AND event = ? AND robot_id = ?",
            (project_id, task_type, event, robot_id),
        )
        if not row:
            return None
        try:
            row["receiver_ids"] = json.loads(row.get("receiver_ids") or "[]")
        except (ValueError, TypeError):
            row["receiver_ids"] = []
        return row

    @classmethod
    def upsert_task(cls, data: dict) -> Dict[str, Any]:
        cls.ensure_tables()
        project_id = data.get("project_id", "") or data.get("projectId", "")
        task_type = data.get("task_type", "") or data.get("taskType", "")
        event = data.get("event", "")
        robot_id = data.get("robot_id", "") or data.get("robotId", "")
        now = _now()
        receiver_ids = data.get("receiverIds", data.get("receiver_ids", []))
        if not isinstance(receiver_ids, list):
            try:
                receiver_ids = json.loads(receiver_ids) if isinstance(receiver_ids, str) else []
            except (ValueError, TypeError):
                receiver_ids = []
        existing = cls.query_one(
            "SELECT id FROM message_tasks WHERE project_id=? AND task_type=? AND event=? AND robot_id=?",
            (project_id, task_type, event, robot_id),
        )
        subject = data.get("subject", "") or data.get("defaultSubject", "")
        template = data.get("template", "") or data.get("defaultTemplate", "")
        payload = (
            project_id, task_type, event, robot_id,
            json.dumps(receiver_ids, ensure_ascii=False),
            subject,
            template,
            _bool(data.get("useDefaultSubject", data.get("use_default_subject", True))),
            _bool(data.get("useDefaultTemplate", data.get("use_default_template", True))),
            _bool(data.get("enable", data.get("enable", False))),
            now, now,
        )
        if existing:
            cls.execute(
                """UPDATE message_tasks SET project_id=?, task_type=?, event=?, robot_id=?,
                   receiver_ids=?, subject=?, template=?, use_default_subject=?,
                   use_default_template=?, enable=?, update_time=? WHERE id=?""",
                payload[:10] + (now,) + (existing["id"],),
            )
        else:
            tid = _new_id()
            cls.execute(
                """INSERT INTO message_tasks
                   (id, project_id, task_type, event, robot_id, receiver_ids, subject,
                    template, use_default_subject, use_default_template, enable,
                    create_time, update_time)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (tid,) + payload,
            )
        task = cls.get_task(project_id, task_type, event, robot_id) or {}
        task.setdefault("project_id", project_id)
        return task

    # ════════════════════════════════════════════════════
    # 站内通知
    # ════════════════════════════════════════════════════
    @classmethod
    def create_notification(cls, data: dict) -> str:
        cls.ensure_tables()
        nid = _new_id()
        cls.execute(
            """INSERT INTO notifications
               (id, type, title, sub_title, content, avatar, resource_type, resource_id,
                resource_name, operation, receiver, operator, project_id, organization_id,
                status, create_time)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                nid, data.get("type", "message"), data.get("title", ""),
                data.get("sub_title", ""), data.get("content", ""),
                data.get("avatar", ""), data.get("resource_type", ""),
                data.get("resource_id", ""), data.get("resource_name", ""),
                data.get("operation", ""), data.get("receiver", ""),
                data.get("operator", ""), data.get("project_id", ""),
                data.get("organization_id", ""), data.get("status", "UNREAD"), _now(),
            ),
        )
        return nid

    @classmethod
    def list_notifications(cls, receiver: str = "", status: str = "",
                           type_: str = "", resource_type: str = "",
                           keyword: str = "", project_id: str = "",
                           limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        cls.ensure_tables()
        sql = "SELECT * FROM notifications WHERE 1=1"
        params: list = []
        if receiver:
            sql += " AND receiver = ?"
            params.append(receiver)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if type_:
            sql += " AND type = ?"
            params.append(type_)
        if resource_type:
            sql += " AND resource_type = ?"
            params.append(resource_type)
        if project_id:
            sql += " AND project_id = ?"
            params.append(project_id)
        if keyword:
            sql += " AND (title LIKE ? OR content LIKE ? OR resource_name LIKE ?)"
            like = f"%{keyword}%"
            params.extend([like, like, like])
        sql += " ORDER BY create_time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = cls.query_all(sql, tuple(params))
        return rows

    @classmethod
    def count_notifications(cls, receiver: str = "", status: str = "",
                            resource_type: str = "") -> int:
        cls.ensure_tables()
        sql = "SELECT COUNT(*) AS cnt FROM notifications WHERE 1=1"
        params: list = []
        if receiver:
            sql += " AND receiver = ?"
            params.append(receiver)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if resource_type:
            sql += " AND resource_type = ?"
            params.append(resource_type)
        row = cls.query_one(sql, tuple(params))
        return int(row["cnt"]) if row else 0

    @classmethod
    def set_read(cls, notification_id: str) -> bool:
        cls.ensure_tables()
        cursor = cls.execute(
            "UPDATE notifications SET status = 'READ' WHERE id = ?", (notification_id,)
        )
        return cursor.rowcount > 0

    @classmethod
    def set_read_all(cls, receiver: str = "", resource_type: str = "") -> int:
        cls.ensure_tables()
        sql = "UPDATE notifications SET status = 'READ' WHERE status = 'UNREAD'"
        params: list = []
        if receiver:
            sql += " AND receiver = ?"
            params.append(receiver)
        if resource_type:
            sql += " AND resource_type = ?"
            params.append(resource_type)
        cur = cls.execute(sql, tuple(params))
        return cur.rowcount or 0

    @classmethod
    def seed_welcome(cls, receiver: str = "", project_id: str = "") -> None:
        """首次部署时写入欢迎通知，保证消息中心非空。"""
        if cls.count_notifications(receiver=receiver) > 0:
            return
        cls.create_notification({
            "type": "message",
            "title": "欢迎使用 Test Generation Agent",
            "sub_title": "系统消息",
            "content": "这是平台自动生成的欢迎消息。在这里可以查看用例、缺陷、接口等业务通知。",
            "avatar": "",
            "resource_type": "SYSTEM",
            "resource_name": "系统",
            "operation": "CREATE",
            "receiver": receiver,
            "operator": "system",
            "project_id": project_id,
        })


message_repo = MessageRepo()
