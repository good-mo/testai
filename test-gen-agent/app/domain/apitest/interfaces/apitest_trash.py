# app/routers/apitest_trash.py
"""接口测试-回收站与操作日志路由（自 apitest.py 拆分，控制文件行数 <800）。"""
import asyncio

from fastapi import APIRouter, Body

from app.core.response import ok
from app.models.apitest import BatchIdsBody
from app.domain.apitest.application.apitest_app_service import apitest_service

router = APIRouter(tags=["apitest"])


# ── 回收站 ────────────────────────────────────────────────

@router.get("/api/apitest/trash/definitions")
def api_list_trash_definitions(project_id: str = "", limit: int = 100):
    """列出回收站中的接口定义。"""
    items = apitest_service.list_trash_definitions(project_id, limit)
    total = apitest_service.count_trash_definitions(project_id)
    return ok({"items": items, "total": total})


@router.post("/api/apitest/trash/definitions/{definition_id}/restore")
def api_restore_definition(definition_id: str):
    """恢复回收站中的接口定义。"""
    result = apitest_service.restore_definition(definition_id)
    return ok({"success": result})


@router.post("/api/apitest/trash/definitions/batch-restore")
def api_batch_restore_definitions(body: BatchIdsBody = Body(default=None)):
    """批量恢复回收站中的接口定义。"""
    ids = body.ids if body else []
    count = apitest_service.batch_restore_definitions(ids)
    return ok({"success": True, "restored": count})


@router.delete("/api/apitest/trash/definitions/{definition_id}")
def api_purge_definition(definition_id: str):
    """彻底删除回收站中的接口定义。"""
    result = apitest_service.purge_definition(definition_id)
    return ok({"success": result})


@router.get("/api/apitest/trash/cases")
def api_list_trash_cases(project_id: str = "", limit: int = 100):
    """列出回收站中的接口用例。"""
    items = apitest_service.list_trash_cases(project_id, limit)
    total = apitest_service.count_trash_cases(project_id)
    return ok({"items": items, "total": total})


@router.post("/api/apitest/trash/cases/{case_id}/restore")
def api_restore_case(case_id: str):
    """恢复回收站中的接口用例。"""
    result = apitest_service.restore_case(case_id)
    return ok({"success": result})


@router.post("/api/apitest/trash/cases/batch-restore")
def api_batch_restore_cases(body: BatchIdsBody = Body(default=None)):
    """批量恢复回收站中的接口用例。"""
    ids = body.ids if body else []
    count = apitest_service.batch_restore_cases(ids)
    return ok({"success": True, "restored": count})


@router.delete("/api/apitest/trash/cases/{case_id}")
def api_purge_case(case_id: str):
    """彻底删除回收站中的接口用例。"""
    result = apitest_service.purge_case(case_id)
    return ok({"success": result})


@router.get("/api/apitest/trash/scenarios")
def api_list_trash_scenarios(project_id: str = "", limit: int = 100):
    """列出回收站中的接口场景。"""
    items = apitest_service.list_trash_scenarios(project_id, limit)
    total = apitest_service.count_trash_scenarios(project_id)
    return ok({"items": items, "total": total})


@router.post("/api/apitest/trash/scenarios/{scenario_id}/restore")
def api_restore_scenario(scenario_id: str):
    """恢复回收站中的接口场景。"""
    result = apitest_service.restore_scenario(scenario_id)
    return ok({"success": result})


@router.post("/api/apitest/trash/scenarios/batch-restore")
def api_batch_restore_scenarios(body: BatchIdsBody = Body(default=None)):
    """批量恢复回收站中的接口场景。"""
    ids = body.ids if body else []
    count = apitest_service.batch_restore_scenarios(ids)
    return ok({"success": True, "restored": count})


@router.delete("/api/apitest/trash/scenarios/{scenario_id}")
def api_purge_scenario(scenario_id: str):
    """彻底删除回收站中的接口场景。"""
    result = apitest_service.purge_scenario(scenario_id)
    return ok({"success": result})


@router.get("/api/apitest/trash/mocks")
def api_list_trash_mocks(project_id: str = "", limit: int = 100):
    """列出回收站中的 Mock 服务。"""
    items = apitest_service.list_trash_mocks(project_id, limit)
    total = apitest_service.count_trash_mocks(project_id)
    return ok({"items": items, "total": total})


@router.post("/api/apitest/trash/mocks/{mock_id}/restore")
def api_restore_mock(mock_id: str):
    """恢复回收站中的 Mock 服务。"""
    result = apitest_service.restore_mock(mock_id)
    return ok({"success": result})


@router.post("/api/apitest/trash/mocks/batch-restore")
def api_batch_restore_mocks(body: BatchIdsBody = Body(default=None)):
    """批量恢复回收站中的 Mock 服务。"""
    ids = body.ids if body else []
    count = apitest_service.batch_restore_mocks(ids)
    return ok({"success": True, "restored": count})


@router.delete("/api/apitest/trash/mocks/{mock_id}")
def api_purge_mock(mock_id: str):
    """彻底删除回收站中的 Mock 服务。"""
    result = apitest_service.purge_mock(mock_id)
    return ok({"success": result})


# ── 操作日志 ──────────────────────────────────────────────

@router.get("/api/apitest/logs")
def api_list_operation_logs(resource_type: str = "", resource_id: str = "",
                                  project_id: str = "", limit: int = 100):
    """列出操作日志。"""
    items = apitest_service.list_operation_logs(resource_type, resource_id, project_id, limit)
    return ok({"items": items, "total": len(items)})


@router.delete("/api/apitest/logs")
async def api_clear_operation_logs(days: int = 30):
    """清理指定天数之前的操作日志。

    days 语义：仅清理 created_at 早于 now - days*86400 的记录。
    传 days<=0 表示清空全部（便于前端「清空日志」按钮一步到位）。
    """
    if days is None or days < 0:
        days = 30
    await asyncio.to_thread(apitest_service.clear_operation_logs, days)
    return ok({"success": True, "cleared_days": days})
