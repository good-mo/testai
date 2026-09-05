"""消息配置树构建策略。

将功能模块/任务类型/事件与机器人配置聚合为前端消息设置树。
纯领域策略：不依赖存储层、无外部副作用。
"""
from __future__ import annotations

# 功能模块 → 任务类型 → 事件定义（领域常量，与前端消息管理配置树对应）
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


def build_settings_tree(repo, project_id: str) -> list:
    """构建消息设置完整树。

    Args:
        repo: 仓储适配器（提供 list_robots / list_tasks）
        project_id: 项目 ID

    Returns:
        MessageItem[]（type/name + messageTaskTypeDTOList）
    """
    # 获取机器人列表（含内置）
    from app.domain.message.application.message_app_service import BUILTIN_ROBOTS
    robots = []
    for b in BUILTIN_ROBOTS:
        robots.append({
            "id": b["platform"], "name": b["name"], "platform": b["platform"],
            "type": "CUSTOM", "enable": True,
        })
    for r in repo.list_robots(project_id):
        robots.append(r.to_dict())

    # 已保存配置
    tasks = repo.list_tasks(project_id)
    task_map = {(t["task_type"], t["event"], t["robot_id"]): t for t in tasks}

    modules = []
    seen = set()
    for mod in FEATURE_MODULES:
        if mod["type"] in seen:
            continue
        seen.add(mod["type"])
        type_list = []
        for tt in mod["task_types"]:
            detail_list = []
            for event, event_name in tt["events"]:
                detail_list.append({
                    "event": event,
                    "eventName": event_name,
                    "projectRobotConfigMap": _build_robot_config_map(robots, task_map, tt["task_type"], event),
                })
            type_list.append({
                "taskType": tt["task_type"],
                "taskTypeName": tt["task_type_name"],
                "messageTaskDetailDTOList": detail_list,
            })
        modules.append({
            "type": mod["type"],
            "name": mod["name"],
            "messageTaskTypeDTOList": type_list,
        })
    return modules


def _build_robot_config_map(robots: list, task_map: dict,
                            task_type: str, event: str) -> dict:
    """构造某事件下所有机器人配置的映射。"""
    result = {}
    for robot in robots:
        rid = robot.get("id") or robot.get("robot_id", "")
        saved = task_map.get((task_type, event, rid)) or {}
        name = robot.get("name", "")
        result[rid] = {
            "robotId": rid,
            "robotName": name,
            "platform": robot.get("platform", "CUSTOM"),
            "type": robot.get("type", "CUSTOM"),
            "enable": bool(saved.get("enable", False)),
            "template": saved.get("template", ""),
            "defaultTemplate": "操作人：${operator}\n项目：${projectName}\n对象：${resourceName}\n操作：${operation}\n时间：${createTime}",
            "useDefaultTemplate": bool(saved.get("use_default_template", True)),
            "subject": saved.get("subject", ""),
            "defaultSubject": f"【{name}】通知",
            "useDefaultSubject": bool(saved.get("use_default_subject", True)),
        }
    return result


__all__ = ["build_settings_tree", "FEATURE_MODULES"]
