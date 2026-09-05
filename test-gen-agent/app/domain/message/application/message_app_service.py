"""消息应用服务（Application Service / Use Case 门面）。

负责消息领域（机器人/消息设置/站内通知）的用例编排。
"""
from __future__ import annotations

import uuid
from typing import Optional

from app.domain.common.domain_events import event_bus
from app.domain.message.application.dto import (
    NotificationCreateCommand,
    NotificationQuery,
    NotificationReadAllCommand,
    NotificationReadCommand,
    RobotCreateCommand,
    RobotDeleteCommand,
    RobotEnableCommand,
    RobotGetCommand,
    RobotListQuery,
    RobotUpdateCommand,
)
from app.domain.message.domain.entities.notification import Notification
from app.domain.message.domain.entities.robot import Robot
from app.domain.message.infrastructure.message_repository_impl import MessageRepoAdapter

# 系统内置机器人（不落库，前端需展示且不可编辑）
BUILTIN_ROBOTS = [
    {
        "platform": "IN_SITE",
        "name": "站内信",
        "description": "平台站内通知",
        "webhook": "",
        "type": "CUSTOM",
        "enable": True,
    },
    {
        "platform": "MAIL",
        "name": "邮件",
        "description": "邮件通知（需在系统设置中配置 SMTP）",
        "webhook": "",
        "type": "CUSTOM",
        "enable": True,
    },
]


class MessageAppService:
    """消息用例编排服务。"""

    def __init__(self, repo=None):
        self._repo = repo or MessageRepoAdapter()

    # ── 机器人 ──────────────────────────────────────────
    def list_robots(self, cmd: RobotListQuery) -> list:
        """项目机器人列表（内置 + 用户自建）。"""
        result = []
        for b in BUILTIN_ROBOTS:
            result.append(self._robot_to_frontend({
                "id": b["platform"],
                "project_id": cmd.project_id,
                "name": b["name"],
                "platform": b["platform"],
                "type": "CUSTOM",
                "webhook": "",
                "app_key": "",
                "app_secret": "",
                "enable": True,
                "description": b["description"],
                "create_user": "admin", "update_user": "admin",
                "create_time": 0, "update_time": 0,
            }))
        for robot in self._repo.list_robots(cmd.project_id):
            result.append(self._robot_to_frontend(robot.to_dict()))
        return result

    def get_robot(self, cmd: RobotGetCommand) -> Optional[dict]:
        """获取单个机器人（含内置）。"""
        for b in BUILTIN_ROBOTS:
            if b["platform"] == cmd.robot_id:
                return self._robot_to_frontend({
                    "id": b["platform"], "project_id": "",
                    "name": b["name"], "platform": b["platform"],
                    "type": "CUSTOM", "webhook": "", "app_key": "",
                    "app_secret": "", "enable": True,
                    "description": b["description"],
                    "create_user": "admin", "update_user": "admin",
                    "create_time": 0, "update_time": 0,
                })
        robot = self._repo.get_robot(cmd.robot_id)
        return self._robot_to_frontend(robot.to_dict()) if robot else None

    def create_robot(self, cmd: RobotCreateCommand) -> dict:
        """创建机器人（站内信/邮件不允许创建）。"""
        if cmd.platform in ("IN_SITE", "MAIL"):
            raise ValueError("站内信/邮件为系统内置机器人，不允许创建")
        robot = Robot(
            robot_id=str(uuid.uuid4()),
            project_id=cmd.project_id,
            name=cmd.name,
            platform=cmd.platform,
            type=cmd.type,
            webhook=cmd.webhook,
            app_key=cmd.app_key,
            app_secret=cmd.app_secret,
            enable=cmd.enable,
            description=cmd.description,
            create_user=cmd.create_user,
            update_user=cmd.create_user,
            _created=True,
        )
        saved = self._repo.create_robot(robot)
        self._publish(robot)
        return self._robot_to_frontend(saved.to_dict())

    def update_robot(self, cmd: RobotUpdateCommand) -> bool:
        robot = self._repo.get_robot(cmd.robot_id)
        if robot:
            robot.update_meta(cmd.data)
            self._publish(robot)
        return self._repo.update_robot(cmd.robot_id, cmd.data)

    def delete_robot(self, cmd: RobotDeleteCommand) -> bool:
        robot = self._repo.get_robot(cmd.robot_id)
        if robot:
            robot.mark_deleted()
            self._publish(robot)
        return self._repo.delete_robot(cmd.robot_id)

    def set_robot_enable(self, cmd: RobotEnableCommand) -> bool:
        return self._repo.set_robot_enable(cmd.robot_id, cmd.enable)

    # ── 消息设置 ─────────────────────────────────────────
    def list_message_settings(self, project_id: str) -> list:
        """消息设置完整树。"""
        # 复用既有实现逻辑，此处简化直接返回配置树结构
        # 详细实现在原 message_service 中，此处作为 DDD 门面转发
        from app.domain.message.domain.services.msg_config_builder import (
            build_settings_tree,
        )
        return build_settings_tree(self._repo, project_id)

    def save_message_config(self, data: dict) -> dict:
        return self._repo.upsert_task(data)

    # ── 站内通知 ─────────────────────────────────────────
    def create_notification(self, cmd: NotificationCreateCommand) -> dict:
        n = Notification(
            notification_id=str(uuid.uuid4()),
            type=cmd.type, title=cmd.title, sub_title=cmd.sub_title,
            content=cmd.content, avatar=cmd.avatar,
            resource_type=cmd.resource_type, resource_id=cmd.resource_id,
            resource_name=cmd.resource_name, operation=cmd.operation,
            receiver=cmd.receiver, operator=cmd.operator,
            project_id=cmd.project_id, organization_id=cmd.organization_id,
            _created=True,
        )
        nid = self._repo.create_notification(n)
        self._publish(n)
        return {"id": nid}

    def list_notifications(self, cmd: NotificationQuery) -> dict:
        rows = self._repo.list_notifications(
            receiver=cmd.receiver, status=cmd.status,
            type_=cmd.type_, resource_type=cmd.resource_type,
            keyword=cmd.keyword, project_id=cmd.project_id,
            limit=cmd.page_size, offset=(cmd.current - 1) * cmd.page_size,
        )
        total = self._repo.count_notifications(
            receiver=cmd.receiver, status=cmd.status,
            resource_type=cmd.resource_type,
        )
        items = [self._notif_to_frontend(n.to_dict()) for n in rows]
        return {"list": items, "total": total,
                "current": cmd.current, "pageSize": cmd.page_size}

    def unread_count(self, receiver: str = "", project_id: str = "") -> int:
        return self._repo.count_notifications(receiver=receiver, status="UNREAD")

    def set_read(self, cmd: NotificationReadCommand) -> bool:
        return self._repo.set_read(cmd.notification_id)

    def set_read_all(self, cmd: NotificationReadAllCommand) -> int:
        return self._repo.set_read_all(receiver=cmd.receiver,
                                       resource_type=cmd.resource_type)

    # ── 工具 ─────────────────────────────────────────────
    @staticmethod
    def _robot_to_frontend(r: dict) -> dict:
        return {
            "id": r.get("id", ""),
            "projectId": r.get("project_id", ""),
            "name": r.get("name", ""),
            "platform": r.get("platform", "CUSTOM"),
            "type": r.get("type", "CUSTOM"),
            "webhook": r.get("webhook", ""),
            "appKey": r.get("app_key", ""),
            "appSecret": r.get("app_secret", ""),
            "enable": bool(r.get("enable", True)),
            "description": r.get("description", ""),
            "createUser": r.get("create_user", "admin"),
            "createTime": int((r.get("create_time") or 0) * 1000),
            "updateUser": r.get("update_user", "admin"),
            "updateTime": int((r.get("update_time") or 0) * 1000),
        }

    @staticmethod
    def _notif_to_frontend(n: dict) -> dict:
        return {
            "id": n.get("id", ""),
            "type": n.get("type", "message"),
            "title": n.get("title", ""),
            "subTitle": n.get("sub_title", ""),
            "content": n.get("content", ""),
            "avatar": n.get("avatar", ""),
            "resourceType": n.get("resource_type", ""),
            "resourceId": n.get("resource_id", ""),
            "resourceName": n.get("resource_name", ""),
            "operation": n.get("operation", ""),
            "receiver": n.get("receiver", ""),
            "operator": n.get("operator", ""),
            "projectId": n.get("project_id", ""),
            "organizationId": n.get("organization_id", ""),
            "status": n.get("status", "UNREAD"),
            "createTime": int((n.get("create_time") or 0) * 1000),
        }

    @staticmethod
    def _publish(entity) -> None:
        for ev in entity.pull_domain_events():
            event_bus.dispatch(ev)


# 单例门面
message_app_service = MessageAppService()

__all__ = ["MessageAppService", "message_app_service"]
