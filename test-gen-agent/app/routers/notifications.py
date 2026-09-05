# app/routers/notifications.py
"""消息通知 / 消息管理 路由（四层架构：Router → Service → Repository）。

覆盖：
- 消息中心站内通知：列表 / 未读 / 已读 / 全部已读
- 消息管理-消息设置：配置树 / 接收人 / 模板详情 / 字段
机器人 CRUD 路由位于 project_compat.py（`/project/robot/*`），经同一 message_service 收口。
"""

from fastapi import APIRouter, Body, Request

from app.core.helpers import current_user
from app.core.response import fail, ok
from app.logging_config import get_logger
from app.models.message import (
    MessageTaskSaveBody,
    NotificationPageQuery,
    NotificationReadBody,
)
from app.services.message_service import message_service

logger = get_logger(__name__)
router = APIRouter(tags=["message-notifications"])


def _receiver(request: Request) -> str:
    """通知接收人：默认当前用户 ID。"""
    user = current_user(request)
    return str(user.get("id", "")) if user else ""


# ════════════════════════════════════════════════════════════
# 一、消息中心（站内通知）
# ════════════════════════════════════════════════════════════

@router.get("/notification/read/all")
@router.post("/notification/read/all")
async def notification_read_all(
        request: Request,
        body: NotificationReadBody = Body(default=None)):
    """全部已读。resourceType 可选。"""
    resource_type = request.query_params.get("resourceType", "")
    if not resource_type and body is not None:
        resource_type = body.resourceType or body.resource_type
    receiver = body.receiver if body is not None else ""
    if not receiver:
        receiver = _receiver(request)
    updated = message_service.set_read_all(receiver, resource_type)
    return ok({"updated": updated})


@router.get("/notification/read/{item_id}")
def notification_read_item_get(item_id: str, request: Request):
    """单条消息已读（GET）。"""
    message_service.set_read(item_id)
    return ok({"id": item_id, "read": True})


@router.post("/notification/read/{notification_id}")
def notification_read_path(notification_id: str):
    """标记消息通知为已读（POST 兼容，GET 由上方 item_id 路由统一处理）。"""
    message_service.set_read(notification_id)
    return ok({"id": notification_id, "read": True})


@router.get("/notification/count")
def notification_count(request: Request):
    """通知数量（未读数）。"""
    receiver = _receiver(request)
    return ok({"count": message_service.unread_count(receiver=receiver)})


@router.post("/notification/count")
async def notification_count_post(
        request: Request,
        body: NotificationPageQuery = Body(default=None)):
    """通知数量（POST 兼容）。"""
    receiver = body.receiver if body is not None else ""
    if not receiver:
        receiver = _receiver(request)
    return ok({"count": message_service.unread_count(receiver=receiver)})


@router.get("/notification/list/all/page")
def notification_list_all_page(request: Request):
    """通知分页列表（GET 兼容）。"""
    q = request.query_params
    receiver = q.get("receiver", "") or _receiver(request)
    result = message_service.list_notifications(
        receiver=receiver,
        status=q.get("status", ""),
        type_=q.get("type", ""),
        resource_type=q.get("resourceType", q.get("resource_type", "")),
        keyword=q.get("keyword", ""),
        project_id=q.get("projectId", q.get("project_id", "")),
        current=int(q.get("current", 1)),
        page_size=int(q.get("pageSize", 10)),
    )
    return ok(result)


@router.post("/notification/list/all/page")
async def notification_list_all_page_post(
        request: Request,
        body: NotificationPageQuery = Body(default=None)):
    """通知分页列表（POST 兼容，前端消息中心使用）。"""
    if body is None:
        receiver, status, type_, resource_type, keyword, project_id = "", "", "", "", "", ""
        current, page_size = 1, 10
    else:
        sent = body.model_fields_set
        receiver = body.receiver or ""
        status = body.status or ""
        type_ = body.type or ""
        resource_type = body.resourceType or body.resource_type or ""
        keyword = body.keyword or ""
        project_id = body.projectId or body.project_id or ""
        # 页码/每页条数：优先驼峰标准名，其次兼容旧别名 page/page_size
        if "current" in sent:
            current = int(body.current or 1)
        elif "page" in sent and body.page is not None:
            current = int(body.page)
        else:
            current = int(body.current or 1)
        if "pageSize" in sent:
            page_size = int(body.pageSize or 10)
        elif "page_size" in sent and body.page_size is not None:
            page_size = int(body.page_size)
        else:
            page_size = int(body.pageSize or 10)
    if not receiver:
        receiver = _receiver(request)
    result = message_service.list_notifications(
        receiver=receiver,
        status=status,
        type_=type_,
        resource_type=resource_type,
        keyword=keyword,
        project_id=project_id,
        current=current,
        page_size=page_size,
    )
    return ok(result)


@router.get("/notification/un-read")
def notification_un_read(request: Request):
    """未读通知（列表）。"""
    receiver = _receiver(request)
    return ok(message_service.list_notifications(
        receiver=receiver, status="UNREAD", page_size=50,
    )["list"])


@router.get("/notification/un-read/{project_id}")
def notification_unread_by_project(project_id: str, request: Request):
    """项目未读通知数。前端 getMessageUnReadCount(projectId)。"""
    receiver = _receiver(request)
    return ok(message_service.unread_count(receiver=receiver, project_id=project_id))


@router.post("/api/message/list")
@router.get("/api/message/list")
def api_message_list(request: Request):
    """站内消息列表（navbar message-box：message/notice/todo 三类）。"""
    receiver = _receiver(request)
    items = message_service.list_notifications(
        receiver=receiver, page_size=100,
    )["list"]
    # 前端 tab 只有 message/notice/todo
    out = []
    type_order = {"message": 0, "notice": 1, "todo": 2}
    for it in items:
        t = it.get("type", "message")
        if t not in type_order:
            t = "notice"
        out.append({
            "id": it.get("id"),
            "type": t,
            "title": it.get("title", ""),
            "subTitle": it.get("subTitle", ""),
            "avatar": it.get("avatar", ""),
            "content": it.get("content", ""),
            "time": _fmt_time(it.get("createTime", 0)),
            "status": 0 if it.get("status") == "UNREAD" else 1,
            "messageType": 1 if t == "notice" else 2 if t == "todo" else 0,
        })
    return ok(out)


def _fmt_time(ms: int) -> str:
    import datetime
    try:
        return datetime.datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


@router.post("/api/message/read")
async def api_message_read(
        body: NotificationReadBody = Body(default=None)):
    """消息已读。body: {ids: []}。"""
    ids = (body.ids or []) if body is not None else []
    if isinstance(ids, (int, str)):
        ids = [ids]
    for mid in ids:
        message_service.set_read(str(mid))
    return ok()


@router.post("/api/message/read/{item_id}")
@router.get("/api/message/read/{item_id}")
def api_message_read_path(item_id: str):
    """消息已读（带路径参数）。"""
    message_service.set_read(item_id)
    return ok({"id": item_id, "read": True})


@router.get("/api/chat/list")
@router.post("/api/chat/list")
def api_chat_list():
    """站内会话列表（消息中心辅助）。"""
    return ok([])


# ════════════════════════════════════════════════════════════
# 二、消息设置（消息管理页面）
# ════════════════════════════════════════════════════════════

@router.get("/notice/message/task/get")
def notice_message_task_get(project_id: str = ""):
    """获取消息任务配置（无路径参数兼容）。"""
    return ok(message_service.get_message_settings(project_id))


@router.get("/notice/message/task/get/{project_id}")
def notice_message_task_get_path(project_id: str):
    """获取消息任务配置（带路径参数）。"""
    return ok(message_service.get_message_settings(project_id))


@router.post("/notice/message/task/save")
async def notice_message_task_save(
        body: MessageTaskSaveBody = Body(default=None)):
    """保存消息任务配置（单条：接收人/模板/启用）。"""
    if body is None or (not body.model_fields_set and not body.model_extra):
        return fail("请求体不能为空", 400)
    try:
        # 仅保留客户端实际携带字段（含驼峰/下划线双命名），
        # 交由 message_repo.upsert_task 按「驼峰优先、下划线兜底」读取。
        saved = message_service.save_message_config(body.model_dump(exclude_unset=True))
        return ok(saved)
    except Exception as e:
        logger.warning("保存消息配置失败: %s", e)
        return fail("保存失败", 400)


@router.get("/notice/message/task/get/user")
def notice_message_task_get_user(project_id: str = "", keyword: str = ""):
    """消息任务用户列表（无路径参数兼容）。"""
    return ok(message_service.get_receiver_options(project_id, keyword))


@router.get("/notice/message/task/get/user/{project_id}")
def notice_message_task_get_user_path(project_id: str, keyword: str = ""):
    """消息任务用户列表（带路径参数）。"""
    return ok(message_service.get_receiver_options(project_id, keyword))


@router.get("/notice/message/template/detail/{project_id}")
def notice_message_template_detail_path(project_id: str, request: Request):
    """获取消息模板详情。taskType/event/robotId 来自 query。"""
    q = request.query_params
    task_type = q.get("taskType", q.get("task_type", ""))
    event = q.get("event", "")
    robot_id = q.get("robotId", q.get("robot_id", ""))
    detail = message_service.get_template_detail(project_id, task_type, event, robot_id)
    return ok(detail)


@router.get("/notice/template/get/fields/{project_id}")
def notice_template_get_fields_path(project_id: str, request: Request):
    """获取消息模板字段。taskType 来自 query。"""
    task_type = request.query_params.get("taskType", request.query_params.get("task_type", ""))
    return ok(message_service.get_template_fields(task_type))


@router.get("/notice/template/get/fields")
def notice_template_get_fields(request: Request, project_id: str = ""):
    """获取消息模板字段（无路径参数兼容）。"""
    task_type = request.query_params.get("taskType", request.query_params.get("task_type", ""))
    return ok(message_service.get_template_fields(task_type))


@router.get("/notice/message/template/detail")
def notice_message_template_detail(request: Request, project_id: str = ""):
    """获取消息模板详情（无路径参数兼容）。taskType/event/robotId 来自 query。"""
    q = request.query_params
    if not project_id:
        project_id = q.get("projectId", q.get("project_id", ""))
    task_type = q.get("taskType", q.get("task_type", ""))
    event = q.get("event", "")
    robot_id = q.get("robotId", q.get("robot_id", ""))
    detail = message_service.get_template_detail(project_id, task_type, event, robot_id)
    return ok(detail)


# ════════════════════════════════════════════════════════════
# 三、操作日志用户列表（辅助，接入真实用户）
# ════════════════════════════════════════════════════════════

@router.get("/organization/log/user/list/{org_id}")
def organization_log_user_list_path(org_id: str):
    """组织日志用户列表（带路径参数）。"""
    users = message_service.get_receiver_options()
    return ok(users)
