# app/domain/workflow/interfaces/router.py
"""workflow 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.workflow.application.workflow_app_service import workflow_app_service

router = APIRouter(tags=["workflow"])


@router.get("/api/workflow/{scope_type}")
def list_statuses(scope_type: str, request: Request):
    """列表查询工作流状态。"""
    try:
        from app.domain.workflow.application.dto import ListStatusesCommand
        cmd = ListStatusesCommand(
            scope_type=scope_type,
            scope_id=request.query_params.get("scope_id", ""),
            scene=request.query_params.get("scene", "")
        )
        result = workflow_app_service.list(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))


@router.get("/api/workflow/{scope_type}/{status_id}")
def get_status(scope_type: str, status_id: str, request: Request):
    """获取状态详情。"""
    try:
        from app.domain.workflow.application.dto import GetStatusCommand
        cmd = GetStatusCommand(
            scope_type=scope_type,
            status_id=status_id
        )
        result = workflow_app_service.get(cmd)
        if result:
            return ok(result)
        return fail("Status not found", code=404)
    except Exception as e:
        return fail(str(e))


@router.post("/api/workflow/{scope_type}")
async def create_status(scope_type: str, request: Request):
    """创建状态。"""
    try:
        body = await request.json()
        from app.domain.workflow.application.dto import CreateStatusCommand
        cmd = CreateStatusCommand(
            scope_type=scope_type,
            scope_id=body.get("scope_id", ""),
            scene=body.get("scene", ""),
            name=body.get("name", ""),
            remark=body.get("remark", ""),
            create_user=body.get("create_user", "admin")
        )
        result = workflow_app_service.create(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))


@router.put("/api/workflow/{scope_type}/{status_id}")
async def update_status(scope_type: str, status_id: str, request: Request):
    """更新状态。"""
    try:
        body = await request.json()
        from app.domain.workflow.application.dto import UpdateStatusCommand
        cmd = UpdateStatusCommand(
            scope_type=scope_type,
            status_id=status_id,
            name=body.get("name"),
            remark=body.get("remark"),
            status_definitions=body.get("status_definitions")
        )
        result = workflow_app_service.update(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))


@router.delete("/api/workflow/{scope_type}/{status_id}")
def delete_status(scope_type: str, status_id: str, request: Request):
    """删除状态。"""
    try:
        from app.domain.workflow.application.dto import DeleteStatusCommand
        cmd = DeleteStatusCommand(
            scope_type=scope_type,
            status_id=status_id
        )
        result = workflow_app_service.delete(cmd)
        return ok({"deleted": result})
    except Exception as e:
        return fail(str(e))


@router.post("/api/workflow/{scope_type}/{status_id}/sort")
async def sort_statuses(scope_type: str, status_id: str, request: Request):
    """排序状态。"""
    try:
        body = await request.json()
        from app.domain.workflow.application.dto import SortStatusesCommand
        cmd = SortStatusesCommand(
            scope_type=scope_type,
            status_ids=body.get("status_ids", [])
        )
        result = workflow_app_service.sort(cmd)
        return ok({"success": result})
    except Exception as e:
        return fail(str(e))


@router.post("/api/workflow/{scope_type}/{status_id}/flows")
async def update_flows(scope_type: str, status_id: str, request: Request):
    """更新状态流转。"""
    try:
        body = await request.json()
        from app.domain.workflow.application.dto import UpdateFlowsCommand
        cmd = UpdateFlowsCommand(
            scope_type=scope_type,
            status_id=status_id,
            target_ids=body.get("target_ids", [])
        )
        result = workflow_app_service.update_flows(cmd)
        return ok({"success": result})
    except Exception as e:
        return fail(str(e))


@router.post("/api/workflow/{scope_type}/{status_id}/definition/{definition_id}")
def set_definition(scope_type: str, status_id: str, definition_id: str, request: Request):
    """设置状态定义。"""
    try:
        from app.domain.workflow.application.dto import SetDefinitionCommand
        cmd = SetDefinitionCommand(
            scope_type=scope_type,
            status_id=status_id,
            definition_id=definition_id,
            enable=request.query_params.get("enable", "true").lower() == "true"
        )
        result = workflow_app_service.set_definition(cmd)
        return ok({"success": result})
    except Exception as e:
        return fail(str(e))


@router.post("/api/workflow/{scope_type}/seed")
def seed_defaults(scope_type: str, request: Request):
    """初始化默认状态。"""
    try:
        from app.domain.workflow.application.dto import SeedDefaultsCommand
        cmd = SeedDefaultsCommand(
            scope_type=scope_type,
            scope_id=request.query_params.get("scope_id", ""),
            scene=request.query_params.get("scene", "")
        )
        result = workflow_app_service.seed_defaults(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))
