"""消息聚合仓储实现（Adapter / Anti-Corruption Layer）。"""
from __future__ import annotations

from typing import List, Optional

from app.domain.message.domain.entities.notification import Notification
from app.domain.message.domain.entities.robot import Robot
from app.domain.message.infrastructure.message_store import MessageRepo


class MessageRepoAdapter:
    """将既有 MessageRepo 封装为面向聚合的仓储接口。"""

    # ── 机器人 ─────────────────────────────────────────
    def list_robots(self, project_id: str = "") -> List[Robot]:
        rows = MessageRepo.list_robots(project_id)
        return [Robot.from_dict(dict(r)) for r in rows]

    def get_robot(self, robot_id: str) -> Optional[Robot]:
        row = MessageRepo.get_robot(robot_id)
        return Robot.from_dict(dict(row)) if row else None

    def create_robot(self, robot: Robot) -> Robot:
        data = robot.to_dict()
        row = MessageRepo.create_robot(data)
        return Robot.from_dict(dict(row)) if row else robot

    def update_robot(self, robot_id: str, data: dict) -> bool:
        return MessageRepo.update_robot(robot_id, data)

    def delete_robot(self, robot_id: str) -> bool:
        return MessageRepo.delete_robot(robot_id)

    def set_robot_enable(self, robot_id: str, enable: bool) -> bool:
        return MessageRepo.set_robot_enable(robot_id, enable)

    # ── 消息设置 ───────────────────────────────────────
    def list_tasks(self, project_id: str = "", task_type: str = "",
                   robot_id: str = "") -> list:
        return MessageRepo.list_tasks(project_id, task_type, robot_id)

    def get_task(self, project_id: str, task_type: str, event: str,
                 robot_id: str) -> Optional[dict]:
        return MessageRepo.get_task(project_id, task_type, event, robot_id)

    def upsert_task(self, data: dict) -> dict:
        return MessageRepo.upsert_task(data)

    # ── 站内通知 ───────────────────────────────────────
    def create_notification(self, notification: Notification) -> str:
        data = notification.to_dict()
        return MessageRepo.create_notification(data)

    def list_notifications(self, receiver: str = "", status: str = "",
                           type_: str = "", resource_type: str = "",
                           keyword: str = "", project_id: str = "",
                           limit: int = 50, offset: int = 0) -> List[Notification]:
        rows = MessageRepo.list_notifications(
            receiver=receiver, status=status, type_=type_,
            resource_type=resource_type, keyword=keyword, project_id=project_id,
            limit=limit, offset=offset,
        )
        return [Notification.from_dict(dict(r)) for r in rows]

    def count_notifications(self, receiver: str = "", status: str = "",
                            resource_type: str = "") -> int:
        return MessageRepo.count_notifications(
            receiver=receiver, status=status, resource_type=resource_type,
        )

    def set_read(self, notification_id: str) -> bool:
        return MessageRepo.set_read(notification_id)

    def set_read_all(self, receiver: str = "", resource_type: str = "") -> int:
        return MessageRepo.set_read_all(receiver=receiver, resource_type=resource_type)

    def seed_welcome(self, receiver: str = "", project_id: str = "") -> None:
        MessageRepo.seed_welcome(receiver=receiver, project_id=project_id)


__all__ = ["MessageRepoAdapter"]
