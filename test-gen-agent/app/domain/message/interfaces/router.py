# app/domain/message/interfaces/router.py
"""message 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.message.application.message_app_service import message_app_service

router = APIRouter(tags=["message"])


# ── 机器人 ────────────────────────────────────────────────

@router.get("/api/message/robots")
def list_robots(request: Request):
    """List Robots。"""
    try:
        from app.domain.message.application.dto import RobotListQuery
        cmd = RobotListQuery(**dict(request.query_params))
        result = message_app_service.list_robots(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/message/robot/{robot_id}")
def get_robot(robot_id: str, request: Request):
    """Get Robot。"""
    try:
        from app.domain.message.application.dto import RobotGetCommand
        cmd = RobotGetCommand(robot_id=robot_id)
        result = message_app_service.get_robot(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/message/robot")
async def create_robot(request: Request):
    """Create Robot。"""
    try:
        body = await request.json()
        from app.domain.message.application.dto import RobotCreateCommand
        cmd = RobotCreateCommand(**body)
        result = message_app_service.create_robot(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.put("/api/message/robot/{robot_id}")
async def update_robot(robot_id: str, request: Request):
    """Update Robot。"""
    try:
        body = await request.json()
        body["robot_id"] = robot_id
        from app.domain.message.application.dto import RobotUpdateCommand
        cmd = RobotUpdateCommand(**body)
        result = message_app_service.update_robot(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.delete("/api/message/robot/{robot_id}")
def delete_robot(robot_id: str, request: Request):
    """Delete Robot。"""
    try:
        from app.domain.message.application.dto import RobotDeleteCommand
        cmd = RobotDeleteCommand(robot_id=robot_id)
        result = message_app_service.delete_robot(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/message/robot/{robot_id}/enable")
async def set_robot_enable(robot_id: str, request: Request):
    """Set Robot Enable。"""
    try:
        body = await request.json()
        body["robot_id"] = robot_id
        from app.domain.message.application.dto import RobotEnableCommand
        cmd = RobotEnableCommand(**body)
        result = message_app_service.set_robot_enable(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

# ── 消息设置 ──────────────────────────────────────────────

@router.get("/api/message/settings/{project_id}")
def list_message_settings(project_id: str, request: Request):
    """List Message Settings。"""
    try:
        result = message_app_service.list_message_settings(project_id)
        return ok(result)
    except Exception as e:
        return fail(str(e))

# ── 消息模板 ──────────────────────────────────────────────

@router.get("/api/message/template/detail")
def get_template_detail(request: Request):
    """获取消息模板详情。

    Query params: project_id, task_type, event, robot_id
    """
    try:
        from app.domain.message.application.dto import TemplateDetailQuery
        cmd = TemplateDetailQuery(**dict(request.query_params))
        result = message_app_service.get_template_detail(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/message/template/fields")
def get_template_fields(request: Request):
    """获取消息模板可用字段。

    Query params: task_type (optional), event (optional)
    """
    try:
        from app.domain.message.application.dto import TemplateFieldsQuery
        cmd = TemplateFieldsQuery(**dict(request.query_params))
        result = message_app_service.get_template_fields(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

# ── 用户列表查询集成（跨域委托 identity） ─────────────────

@router.get("/api/message/users")
def list_message_users(request: Request):
    """获取用户列表（消息域接收人选择）。

    委托 identity 域查询，供消息通知配置时选择接收人。
    Query params: search (optional), limit (optional), offset (optional)
    """
    try:
        from app.domain.message.application.dto import MessageUserListQuery
        params = dict(request.query_params)
        if "limit" in params:
            params["limit"] = int(params["limit"])
        if "offset" in params:
            params["offset"] = int(params["offset"])
        query = MessageUserListQuery(**params)
        result = message_app_service.list_message_users(query)
        return ok(result)
    except Exception as e:
        return fail(str(e))
