"""消息应用服务（Application Service / Use Case 门面）。

负责消息领域（机器人/消息设置/站内通知/消息模板/用户列表集成）的用例编排。
"""
from __future__ import annotations

import uuid
from typing import Optional

from app.domain.common.domain_events import event_bus
from app.domain.message.application.dto import (
    MessageUserListQuery,
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
    TemplateDetailQuery,
    TemplateFieldsQuery,
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

# 消息模板默认字段定义（所有事件类型通用）
_COMMON_TEMPLATE_FIELDS = [
    {"key": "operator", "label": "操作人", "description": "执行当前操作的用户名称", "example": "张三"},
    {"key": "projectName", "label": "项目名称", "description": "所属项目名称", "example": "测试项目A"},
    {"key": "resourceName", "label": "资源名称", "description": "被操作对象的名称", "example": "用例-登录功能"},
    {"key": "operation", "label": "操作类型", "description": "当前操作的动作名称", "example": "新建用例"},
    {"key": "createTime", "label": "操作时间", "description": "操作发生的时间", "example": "2025-01-15 14:30:00"},
]

# 按事件类型扩展的额外字段
_EVENT_EXTRA_FIELDS = {
    "CASE_REVIEW": [
        {"key": "reviewResult", "label": "评审结果", "description": "用例评审的结论", "example": "通过"},
        {"key": "reviewComment", "label": "评审意见", "description": "评审人的备注", "example": "用例覆盖充分"},
    ],
    "CASE_EXECUTE": [
        {"key": "executeResult", "label": "执行结果", "description": "用例执行状态", "example": "通过"},
        {"key": "bugCount", "label": "发现缺陷数", "description": "本次执行发现的缺陷数量", "example": "2"},
    ],
    "CREATE": [
        {"key": "bugPriority", "label": "缺陷优先级", "description": "缺陷优先级", "example": "P1"},
        {"key": "bugStatus", "label": "缺陷状态", "description": "缺陷当前状态", "example": "新建"},
    ],
}

# 默认模板内容
_DEFAULT_TEMPLATE = (
    "操作人：${operator}\n"
    "项目：${projectName}\n"
    "对象：${resourceName}\n"
    "操作：${operation}\n"
    "时间：${createTime}"
)

_DEFAULT_SUBJECT_TEMPLATE = "【${projectName}】${operation}通知"


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
        from app.domain.message.domain.services.msg_config_builder import (
            build_settings_tree,
        )
        return build_settings_tree(self._repo, project_id)

    def save_message_config(self, data: dict) -> dict:
        return self._repo.upsert_task(data)

    # ── 消息模板 ─────────────────────────────────────────
    def get_template_detail(self, cmd: TemplateDetailQuery) -> dict:
        """获取消息模板详情。

        查询指定 project / task_type / event / robot 的模板配置；
        若未保存过则返回默认模板。
        """
        saved = self._repo.get_task(
            cmd.project_id, cmd.task_type, cmd.event, cmd.robot_id,
        )
        if saved:
            return {
                "template": saved.get("template", ""),
                "defaultTemplate": _DEFAULT_TEMPLATE,
                "useDefaultTemplate": bool(saved.get("use_default_template", True)),
                "subject": saved.get("subject", ""),
                "defaultSubject": f"【{cmd.robot_id}】通知",
                "useDefaultSubject": bool(saved.get("use_default_subject", True)),
                "enable": bool(saved.get("enable", False)),
                "robotId": cmd.robot_id,
                "taskType": cmd.task_type,
                "event": cmd.event,
            }
        # 未保存过 → 返回默认模板
        return {
            "template": "",
            "defaultTemplate": _DEFAULT_TEMPLATE,
            "useDefaultTemplate": True,
            "subject": "",
            "defaultSubject": _DEFAULT_SUBJECT_TEMPLATE,
            "useDefaultSubject": True,
            "enable": False,
            "robotId": cmd.robot_id,
            "taskType": cmd.task_type,
            "event": cmd.event,
        }

    def get_template_fields(self, cmd: TemplateFieldsQuery) -> list:
        """获取消息模板可用字段列表。

        返回通用字段 + 按事件类型扩展的字段，供前端模板编辑器使用。
        """
        fields = list(_COMMON_TEMPLATE_FIELDS)
        extra = _EVENT_EXTRA_FIELDS.get(cmd.event, [])
        fields.extend(extra)
        return fields

    # ── 用户列表查询集成（跨域委托 identity） ────────────
    def list_message_users(self, query: MessageUserListQuery) -> dict:
        """获取用户列表（委托 identity 域）。

        消息域在配置通知接收人时需要选择用户，
        此处跨域委托给 identity_app_service.list_users()。
        """
        from app.domain.identity.application.identity_app_service import (
            identity_app_service,
        )
        from app.domain.identity.application.dto import UserListQuery
        identity_query = UserListQuery(
            search=query.search,
            limit=query.limit,
            offset=query.offset,
        )
        return identity_app_service.list_users(identity_query)

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
