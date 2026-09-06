# app/routers/test_compat.py
"""测试兼容路由 test_compat。迁移自 app/adapters/domains/test.py，占位 stub 原样保留。"""

import uuid

from fastapi import APIRouter, Request

from app.core.response import ok, read_body
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["adapter-test"])


def get_enabled_fake_count(project_id: str = "") -> int:
    """获取启用中的误报规则数量。"""
    from app.domain.fake_error.application.fake_error_app_service import fake_error_service
    return fake_error_service.get_enabled_count(project_id)


@router.get("/fake/error/list")
@router.post("/fake/error/list")
async def fake_error_list(request: Request, project_id: str = ""):
    """错误注入列表。"""
    from app.domain.fake_error.application.fake_error_app_service import fake_error_service
    if request.method == "POST":
        body = await read_body(request)
        project_id = (body or {}).get("projectId", project_id) or ""
    return ok(fake_error_service.list_rules(project_id))


@router.post("/fake/error/add")
async def fake_error_add(request: Request):
    """添加错误注入。

    前端 addTemplate 发送数组 body；read_body 将数组归一化为 {"ids": [...]}，
    需提取 ids 恢复原始数组。
    """
    from app.domain.fake_error.application.fake_error_app_service import fake_error_service
    body = await read_body(request)
    # read_body 会把原始数组体归一化为 {"ids": [...]}
    if isinstance(body, dict) and "ids" in body and isinstance(body["ids"], list):
        items = body["ids"]
    else:
        items = body if isinstance(body, list) else [body]
    project_id = body.get("projectId", "") if isinstance(body, dict) else ""
    created = fake_error_service.add_rules(items, project_id)
    return ok(created if isinstance(body, list) or "ids" in body else created[0] if created else {"id": str(uuid.uuid4())})


@router.post("/fake/error/update")
async def fake_error_update(request: Request):
    """更新错误注入。

    前端编辑发送数组 body；read_body 将数组归一化为 {"ids": [...]}，
    需提取 ids 恢复原始数组。
    """
    from app.domain.fake_error.application.fake_error_app_service import fake_error_service
    body = await read_body(request)
    # read_body 会把原始数组体归一化为 {"ids": [...]}
    if isinstance(body, dict) and "ids" in body and isinstance(body["ids"], list):
        items = body["ids"]
    else:
        items = body if isinstance(body, list) else [body]
    updated = fake_error_service.update_rules(items)
    return ok(updated if isinstance(body, list) or "ids" in body else updated[0] if updated else {})


@router.post("/fake/error/delete")
async def fake_error_delete(request: Request):
    """删除错误注入。"""
    from app.domain.fake_error.application.fake_error_app_service import fake_error_service
    body = await read_body(request)
    ids = body.get("selectIds", []) if isinstance(body, dict) else []
    fake_error_service.delete_rules(ids)
    return ok()


@router.post("/fake/error/update/enable")
async def fake_error_update_enable(request: Request):
    """启用/禁用错误注入。"""
    from app.domain.fake_error.application.fake_error_app_service import fake_error_service
    body = await read_body(request)
    ids = body.get("selectIds", []) if isinstance(body, dict) else []
    enable = body.get("enable", True) if isinstance(body, dict) else True
    fake_error_service.update_enable(ids, enable)
    return ok()


# ════════════════════════════════════════════════════════════
# P0-9: WebSocket（基础 /ws/api 已移至 path_param_fixes.py）


# ════════════════════════════════════════════════════════════
# P0-10: 通用状态
# ════════════════════════════════════════════════════════════

