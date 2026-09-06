# app/routers/scripts.py
"""脚本健康度路由（script 域 DDD 接入 · 阶段 B router 直连）。

路由改为直接调用 script 域 DDD 应用服务 `script_app_service`
（参数经应用层 DTO 翻译），不再经 `script_service` 薄门面中转，
与 datafactory.py / reports.py 样板保持一致。

对外响应契约与重构前保持一致（零破坏、可回滚）：
  - GET  /api/scripts                → { scripts, total }
  - POST /api/scripts                → 脚本详情
  - GET  /api/scripts/{id}           → 脚本详情 / 404
  - PUT  /api/scripts/{id}           → 更新后详情 / 404
  - DELETE /api/scripts/{id}         → { deleted, script_id } / 404
领域异常经薄翻译映射为既有 HTTP 状态码。
"""
import asyncio

from fastapi import APIRouter, Depends

from app.core.response import fail, ok
from app.domain.common.exceptions import AggregateNotFound, DomainException
from app.domain.script.application.dto import (
    AutoRepairCommand,
    DeleteCommand,
    EvaluateSelectorCommand,
    GetCommand,
    ListExecutionsCommand,
    RecommendStrategyCommand,
    RecordExecutionCommand,
    RegisterCommand,
    ScriptQuery,
    UpdateCommand,
)
from app.domain.script.application.script_app_service import script_app_service
from app.domain.script.application.dto import (
    ExecutionRecordCreate,
    LocatorEvalRequest,
    ScriptCreate,
    ScriptExecutionsQuery,
    ScriptListQuery,
    ScriptUpdate,
)

router = APIRouter(tags=["scripts"])


def _not_found(script_id: str):
    return fail(f"脚本 {script_id} 不存在", 404)


@router.get("/api/scripts")
def api_list_scripts(query: ScriptListQuery = Depends()):
    """列出所有脚本。"""
    scripts = script_app_service.list(ScriptQuery(
        status=query.status, search=query.search,
        limit=query.limit, offset=query.offset,
    ))
    return ok({"scripts": scripts, "total": len(scripts)})


@router.post("/api/scripts")
def api_create_script(req: ScriptCreate):
    """创建新脚本。"""
    try:
        script = script_app_service.register(RegisterCommand(
            name=req.name, file_path=req.file_path, framework=req.framework,
            description=req.description, locators=req.locators or [],
        ))
    except DomainException as exc:
        return fail(exc.message or str(exc), exc.status_code or 400)
    return ok(script)


@router.get("/api/scripts/{script_id}")
def api_get_script(script_id: str):
    """获取脚本详情。"""
    try:
        script = script_app_service.get(GetCommand(script_id=script_id))
    except AggregateNotFound:
        return _not_found(script_id)
    return ok(script)


@router.put("/api/scripts/{script_id}")
def api_update_script(script_id: str, req: ScriptUpdate):
    """更新脚本。"""
    try:
        script = script_app_service.update(UpdateCommand(
            script_id=script_id, **req.model_dump(exclude_none=True),
        ))
    except AggregateNotFound:
        return _not_found(script_id)
    if not script:
        return _not_found(script_id)
    return ok(script)


@router.delete("/api/scripts/{script_id}")
def api_delete_script(script_id: str):
    """删除脚本。"""
    try:
        deleted = script_app_service.delete(DeleteCommand(script_id=script_id))
    except AggregateNotFound:
        deleted = False
    if not deleted:
        return _not_found(script_id)
    return ok({"deleted": True, "script_id": script_id})


@router.post("/api/scripts/{script_id}/executions")
def api_record_script_execution(script_id: str, req: ExecutionRecordCreate):
    """记录一次脚本执行。"""
    try:
        result = script_app_service.record_execution(RecordExecutionCommand(
            script_id=script_id, success=req.success, duration=req.duration,
            error_type=req.error_type, error_message=req.error_message,
            locator_failures=req.locator_failures,
        ))
    except AggregateNotFound:
        return _not_found(script_id)
    return ok(result)


@router.post("/api/scripts/{script_id}/repair/{locator_name}")
async def api_repair_locator(script_id: str, locator_name: str):
    """自动修复定位器。"""
    result = await asyncio.to_thread(
        script_app_service.auto_repair,
        AutoRepairCommand(script_id=script_id, locator_name=locator_name),
    )
    return ok(result)


@router.get("/api/scripts/{script_id}/executions")
def api_list_script_executions(
    script_id: str, query: ScriptExecutionsQuery = Depends(),
):
    """列出脚本执行历史。"""
    executions = script_app_service.list_executions(
        ListExecutionsCommand(script_id=script_id, limit=query.limit),
    )
    return ok({"executions": executions, "total": len(executions)})


@router.post("/api/locators/evaluate")
def api_evaluate_locator(req: LocatorEvalRequest):
    """评估定位器策略。"""
    evaluation = script_app_service.evaluate_selector(
        EvaluateSelectorCommand(strategy=req.strategy, selector=req.selector),
    )
    recommendation = script_app_service.recommend_strategy(
        RecommendStrategyCommand(selector=req.selector, strategy=req.strategy),
    )
    return ok({"evaluation": evaluation, "recommendation": recommendation})


@router.get("/api/scripthealth/stats")
async def api_script_health_stats():
    """脚本健康度整体统计。"""
    return ok(await asyncio.to_thread(script_app_service.get_stats))
