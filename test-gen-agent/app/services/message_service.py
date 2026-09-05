# app/services/message_service.py
"""消息通知 / 消息管理 业务逻辑层（Phase 3 四层对齐）。

Router → Service → Repository → Database。
前端消息管理、消息中心相关路由的唯一业务入口。
"""
from typing import Any, Dict, List, Optional

from app.repositories.message_repo import message_repo
from app.domain.message.application.dto import (
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
from app.domain.message.application.message_app_service import (
    message_app_service as _ddd_msg,
)

# ── 常量 ───────────────────────────────────────────────────
# 系统内置机器人（不落库，前端需要展示且不可编辑平台）
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

# 三大功能模块 → 消息类型（与 MessageResourceType 对应）
FEATURE_MODULES = [
    {"type": "FUNCTIONAL_CASE", "name": "功能用例", "task_types": [
        {"task_type": "FUNCTIONAL_CASE_TASK", "task_type_name": "功能用例",
         "events": [("CASE_CREATE", "新建用例"), ("CASE_DELETE", "删除用例"),
                    ("CASE_UPDATE", "更新用例"), ("CASE_REVIEW", "用例评审"),
                    ("CASE_EXECUTE", "用例执行")]},
    ]},
    {"type": "BUG_MANAGEMENT", "name": "缺陷管理", "task_types": [
        {"task_type": "BUG_TASK", "task_type_name": "缺陷任务",
         "events": [("CREATE", "新建缺陷"), ("UPDATE", "更新缺陷"),
                    ("DELETE", "删除缺陷"), ("COMMENT", "缺陷评论")]},
        {"task_type": "BUG_SYNC_TASK", "task_type_name": "缺陷同步任务",
         "events": [("BUG_SYNC", "同步缺陷"), ("SYNC_RESULT", "同步结果")]},
    ]},
    {"type": "API_TEST_MANAGEMENT", "name": "接口用例", "task_types": [
        {"task_type": "API_DEFINITION_TASK", "task_type_name": "接口用例",
         "events": [("API_DEFINITION_CREATE", "新建接口"), ("API_DEFINITION_UPDATE", "更新接口"),
                    ("API_DEFINITION_DELETE", "删除接口"), ("API_DEFINITION_EXECUTE", "接口执行")]},
    ]},
]

# 模块名称映射（用于模块列表）
MODULE_META = {
    "FUNCTIONAL_CASE_TASK": {"type": "FUNCTIONAL_CASE", "name": "功能用例"},
    "CASE_REVIEW_TASK": {"type": "CASE_REVIEW", "name": "用例评审"},
    "BUG_TASK": {"type": "BUG_MANAGEMENT", "name": "缺陷管理"},
    "BUG_SYNC_TASK": {"type": "BUG_SYNC", "name": "缺陷同步"},
    "API_DEFINITION_TASK": {"type": "API_TEST_MANAGEMENT", "name": "接口用例"},
    "API_SCENARIO_TASK": {"type": "API_TEST_MANAGEMENT", "name": "接口场景"},
    "TEST_PLAN_TASK": {"type": "TEST_PLAN_MANAGEMENT", "name": "测试计划"},
    "SCHEDULE_TASK": {"type": "SCHEDULE_TASK_MANAGEMENT", "name": "定时任务"},
    "JENKINS_TASK": {"type": "JENKINS_TASK_MANAGEMENT", "name": "Jenkins 任务"},
}

# 事件中文名
EVENT_META = {
    "CREATE": "新建", "UPDATE": "更新", "DELETE": "删除", "COMMENT": "评论",
    "EXECUTE": "执行", "CASE_CREATE": "新建用例", "CASE_DELETE": "删除用例",
    "CASE_UPDATE": "更新用例", "CASE_REVIEW": "用例评审", "CASE_EXECUTE": "用例执行",
    "API_DEFINITION_CREATE": "新建接口", "API_DEFINITION_UPDATE": "更新接口",
    "API_DEFINITION_DELETE": "删除接口", "API_DEFINITION_EXECUTE": "接口执行",
    "BUG_SYNC": "同步缺陷", "SYNC_RESULT": "同步结果",
}

# 特殊接收人（前端用于过滤）
SPECIAL_RECEIVERS = [
    {"id": "OPERATOR", "name": "操作人"},
    {"id": "CREATE_USER", "name": "创建人"},
    {"id": "FOLLOW_PEOPLE", "name": "关注人"},
    {"id": "HANDLE_USER", "name": "处理人"},
]

# 消息模板字段（各类型通用的消息变量）
COMMON_FIELDS = [
    {"id": "operator", "name": "操作人", "fieldSource": "COMMON"},
    {"id": "projectName", "name": "项目名称", "fieldSource": "COMMON"},
    {"id": "organizationName", "name": "组织名称", "fieldSource": "COMMON"},
    {"id": "resourceName", "name": "资源名称", "fieldSource": "COMMON"},
    {"id": "operation", "name": "操作类型", "fieldSource": "COMMON"},
    {"id": "createTime", "name": "操作时间", "fieldSource": "COMMON"},
    {"id": "content", "name": "通知内容", "fieldSource": "COMMON"},
]


class MessageService:
    """消息管理服务：机器人 / 消息设置 / 站内通知的唯一业务入口。"""

    # ── 机器人 ──────────────────────────────────────────
    def list_robots(self, project_id: str = "") -> List[Dict[str, Any]]:
        """项目机器人列表：委托 message 域 DDD 门面（内置 + 用户自建）。"""
        return _ddd_msg.list_robots(RobotListQuery(project_id=project_id))

    def _robot_to_frontend(self, r: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": r.get("id", ""),
            "projectId": r.get("project_id", ""),
            "name": r.get("name", ""),
            "platform": r.get("platform", "CUSTOM"),
            "type": r.get("type", "CUSTOM"),
            "webhook": r.get("webhook", ""),
            "appKey": r.get("app_key", ""),
            "appSecret": r.get("app_secret", ""),
            "enable": bool(r.get("enable", 1)),
            "description": r.get("description", ""),
            "createUser": r.get("create_user", "admin"),
            "createTime": int((r.get("create_time") or 0) * 1000),
            "updateUser": r.get("update_user", ""),
            "updateTime": int((r.get("update_time") or 0) * 1000),
        }

    def get_robot(self, robot_id: str) -> Optional[Dict[str, Any]]:
        """获取单个机器人；委托 message 域 DDD 门面（含内置）。"""
        return _ddd_msg.get_robot(RobotGetCommand(robot_id=robot_id))

    def create_robot(self, data: dict) -> Dict[str, Any]:
        if data.get("platform") in ("IN_SITE", "MAIL"):
            raise ValueError("站内信/邮件为系统内置机器人，不允许创建")
        return _ddd_msg.create_robot(RobotCreateCommand(
            project_id=data.get("project_id", data.get("projectId", "")),
            name=data.get("name", ""),
            platform=data.get("platform", "CUSTOM"),
            type=data.get("type", "CUSTOM"),
            webhook=data.get("webhook", ""),
            app_key=data.get("app_key", data.get("appKey", "")),
            app_secret=data.get("app_secret", data.get("appSecret", "")),
            enable=bool(data.get("enable", True)),
            description=data.get("description", ""),
            create_user=data.get("create_user", data.get("createUser", "admin")),
        ))

    def update_robot(self, robot_id: str, data: dict) -> bool:
        return _ddd_msg.update_robot(RobotUpdateCommand(
            robot_id=robot_id, data=data,
        ))

    def delete_robot(self, robot_id: str) -> bool:
        return _ddd_msg.delete_robot(RobotDeleteCommand(robot_id=robot_id))

    def set_robot_enable(self, robot_id: str, enable: bool) -> bool:
        return _ddd_msg.set_robot_enable(RobotEnableCommand(
            robot_id=robot_id, enable=enable,
        ))

    # ── 消息设置 ─────────────────────────────────────────
    def get_message_settings(self, project_id: str) -> List[Dict[str, Any]]:
        """消息管理-消息设置 完整树：功能模块 → 任务类型 → 事件 → 机器人列。

        返回 MessageItem[]（type/name + messageTaskTypeDTOList）。
        """
        robots = self.list_robots(project_id)
        # 已保存配置 map: (task_type,event,robot_id) → task
        tasks = message_repo.list_tasks(project_id)
        task_map = {(t["task_type"], t["event"], t["robot_id"]): t for t in tasks}

        # 按 (task_type,event) 聚合所有机器人任务，用于事件级接收人展示
        event_task_list: Dict[tuple, List[Dict[str, Any]]] = {}
        for t in tasks:
            event_task_list.setdefault((t["task_type"], t["event"]), []).append(t)

        modules = []
        seen_module = {}
        for mod in FEATURE_MODULES:
            message_task_type_list = []
            for tt in mod["task_types"]:
                detail_list = []
                for event, event_name in tt["events"]:
                    config_map = {}
                    for robot in robots:
                        key = (tt["task_type"], event, robot["id"])
                        saved = task_map.get(key) or {}
                        config_map[robot["id"]] = self._build_robot_config(
                            robot, event, saved
                        )
                    # 事件级接收人：优先取「已启用机器人」的保存接收人，
                    # 否则取任一已保存接收人的机器人任务，最后退回默认。
                    saved_receivers: Optional[List[str]] = None
                    event_tasks = event_task_list.get((tt["task_type"], event), [])
                    # 1) 优先启用状态的机器人配置
                    for t in event_tasks:
                        if t.get("enable") and t.get("receiver_ids"):
                            saved_receivers = t.get("receiver_ids")
                            break
                    # 2) 任一已保存接收人的任务
                    if saved_receivers is None:
                        for t in event_tasks:
                            if t.get("receiver_ids"):
                                saved_receivers = t.get("receiver_ids")
                                break

                    detail_list.append({
                        "event": event,
                        "eventName": event_name,
                        "receivers": self._task_receivers(saved_receivers),
                        "projectRobotConfigMap": config_map,
                    })
                message_task_type_list.append({
                    "taskType": tt["task_type"],
                    "taskTypeName": tt["task_type_name"],
                    "messageTaskDetailDTOList": detail_list,
                })
            if mod["type"] not in seen_module:
                modules.append({
                    "type": mod["type"],
                    "name": mod["name"],
                    "messageTaskTypeDTOList": message_task_type_list,
                })
                seen_module[mod["type"]] = True
        return modules

    def _build_robot_config(self, robot: Dict[str, Any], event: str,
                            saved: Dict[str, Any]) -> Dict[str, Any]:
        """构造某事件下单个机器人的配置项（含默认模板）。"""
        platform = robot.get("platform", "CUSTOM")
        default_subject = f"【{robot.get('name', '')}】通知"
        default_template = (
            "操作人：${operator}\n项目：${projectName}\n"
            "对象：${resourceName}\n操作：${operation}\n时间：${createTime}"
        )
        return {
            "robotId": robot.get("id", ""),
            "robotName": robot.get("name", ""),
            "platform": platform,
            "type": robot.get("type", "CUSTOM"),
            "dingType": robot.get("type", "CUSTOM") if platform == "DING_TALK" else "CUSTOM",
            "enable": bool(saved.get("enable", False)),
            "template": saved.get("template", ""),
            "defaultTemplate": default_template,
            "useDefaultTemplate": bool(saved.get("use_default_template", True)),
            "subject": saved.get("subject", ""),
            "defaultSubject": default_subject,
            "useDefaultSubject": bool(saved.get("use_default_subject", True)),
            "previewSubject": saved.get("subject", "") or default_subject,
            "previewTemplate": saved.get("template", "") or default_template,
        }

    def _task_receivers(self, saved_receivers: Optional[List[str]] = None) -> List[Dict[str, str]]:
        if not saved_receivers:
            return [{"id": "OPERATOR", "name": "操作人"},
                    {"id": "CREATE_USER", "name": "创建人"}]
        # 特殊接收人 + 用户名
        result = []
        id_to_name = self._receiver_names(saved_receivers)
        for rid in saved_receivers:
            result.append({"id": rid, "name": id_to_name.get(rid, rid)})
        return result

    def save_message_config(self, data: dict) -> Dict[str, Any]:
        """保存单条消息设置（接收人/模板/启用）。"""
        return message_repo.upsert_task(data)

    def get_receiver_options(self, project_id: str = "", keyword: str = "") -> List[Dict[str, str]]:
        """消息接收人选项：系统内置特殊角色 + 项目成员/系统用户。"""
        result = list(SPECIAL_RECEIVERS)
        kw = (keyword or "").strip().lower()
        # 项目成员优先，其次系统用户
        seen = set()
        try:
            from app.services.project_service import project_service
            if project_id:
                for m in project_service.list_members(project_id, keyword=keyword):
                    uid = str(m.get("user_id") or m.get("id") or "")
                    name = m.get("name") or m.get("username") or ""
                    if not uid or uid in seen:
                        continue
                    if kw and kw not in str(name).lower() and kw not in str(m.get("username", "")).lower():
                        continue
                    seen.add(uid)
                    result.append({"id": uid, "name": name, "email": m.get("email", ""),
                                   "username": m.get("username", ""), "userId": uid})
        except Exception:
            pass
        try:
            from app.services.auth_service import auth_service
            for u in auth_service.list_users(search="", limit=100000):
                uid = str(u.get("id", ""))
                if not uid or uid in seen:
                    continue
                name = u.get("name") or u.get("username") or ""
                if kw and kw not in str(name).lower() and kw not in str(u.get("username", "")).lower():
                    continue
                seen.add(uid)
                result.append({"id": uid, "name": name, "email": u.get("email", ""),
                               "username": u.get("username", ""), "userId": uid})
        except Exception:
            pass
        return result

    def _receiver_names(self, receiver_ids: List[str]) -> Dict[str, str]:
        special = {r["id"]: r["name"] for r in SPECIAL_RECEIVERS}
        names = {}
        try:
            from app.services.auth_service import auth_service
            users = {
                u.get("id"): (u.get("name") or u.get("username") or u.get("id"))
                for u in auth_service.list_users(search="", limit=100000)
            }
        except Exception:
            users = {}
        for rid in receiver_ids:
            names[rid] = special.get(rid) or users.get(rid) or rid
        return names

    def get_template_detail(self, project_id: str, task_type: str, event: str,
                            robot_id: str) -> Dict[str, Any]:
        """消息模板详情（编辑页）。"""
        robot = self.get_robot(robot_id) or {}
        if not robot:
            robot = {"id": robot_id or "IN_SITE", "name": "机器人", "platform": "IN_SITE",
                     "type": "CUSTOM"}
        task = message_repo.get_task(project_id, task_type, event, robot_id)
        config = self._build_robot_config(robot, event, task or {})
        task_type_name = EVENT_META.get(task_type, task_type)
        event_name = EVENT_META.get(event, event)
        for mod in FEATURE_MODULES:
            for tt in mod["task_types"]:
                if tt["task_type"] == task_type:
                    task_type_name = tt["task_type_name"]
                    event_name = next((n for e, n in tt["events"] if e == event), event_name)
                    break
        return {
            **config,
            "projectId": project_id,
            "taskType": task_type,
            "taskTypeName": task_type_name,
            "event": event,
            "eventName": event_name,
            "robotName": robot.get("name", ""),
            "robotId": robot_id,
            "receiverIds": (task.get("receiver_ids") if task else None) or
                           ["OPERATOR", "CREATE_USER"],
            "useDefaultSubject": config["useDefaultSubject"],
            "useDefaultTemplate": config["useDefaultTemplate"],
            "enable": config["enable"],
        }

    def get_template_fields(self, task_type: str = "") -> Dict[str, Any]:
        """消息模板字段（fieldList + fieldSourceList）。"""
        return {
            "fieldList": COMMON_FIELDS,
            "fieldSourceList": [{"id": "COMMON", "name": "通用"}],
        }

    # ── 站内通知 ─────────────────────────────────────────
    def list_notifications(self, receiver: str = "", status: str = "",
                           type_: str = "", resource_type: str = "",
                           keyword: str = "", project_id: str = "",
                           current: int = 1, page_size: int = 10) -> Dict[str, Any]:
        return _ddd_msg.list_notifications(NotificationQuery(
            receiver=receiver, status=status, type_=type_,
            resource_type=resource_type, keyword=keyword, project_id=project_id,
            current=current, page_size=page_size,
        ))

    def _notification_to_frontend(self, n: Dict[str, Any]) -> Dict[str, Any]:
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

    def unread_count(self, receiver: str = "", project_id: str = "") -> int:
        return _ddd_msg.unread_count(receiver=receiver, project_id=project_id)

    def set_read(self, notification_id: str) -> bool:
        """标记单条消息已读（委托 DDD 门面）。"""
        return _ddd_msg.set_read(NotificationReadCommand(notification_id=notification_id))

    def set_read_all(self, receiver: str = "", resource_type: str = "") -> int:
        """按接收人/资源类型标记全部已读，返回更新条数（委托 DDD 门面）。"""
        return _ddd_msg.set_read_all(NotificationReadAllCommand(
            receiver=receiver, resource_type=resource_type,
        ))

    def count_by_resource(self, receiver: str = "", status: str = "") -> List[Dict[str, str]]:
        """通知中心各资源类型未读数 OptionDTO[]。"""
        result = []
        # total 总数
        total = message_repo.count_notifications(receiver=receiver, status=status or "UNREAD" if not status else status)
        result.append({"id": "total", "name": str(total)})
        resource_types = [
            ("BUG", "BUG_MANAGEMENT"), ("CASE", "CASE_MANAGEMENT"),
            ("API", "API_TEST_MANAGEMENT"), ("TEST_PLAN", "TEST_PLAN_MANAGEMENT"),
            ("SCHEDULE", "SCHEDULE_TASK_MANAGEMENT"), ("JENKINS", "JENKINS_TASK_MANAGEMENT"),
        ]
        for rid, _label in resource_types:
            cnt = message_repo.count_notifications(receiver=receiver, status=status or "UNREAD" if not status else status, resource_type=rid)
            result.append({"id": rid, "name": str(cnt)})
        return result


message_service = MessageService()
