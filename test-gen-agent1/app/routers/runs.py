# app/routers/runs.py
"""运行记录路由（runs 域 DDD 接入 · 阶段 B router 直连）。

路由改为直接调用 runs 域 DDD 应用服务 `run_record_app_service`
（参数经应用层 DTO 翻译），不再经 `run_service` 薄门面中转，
与 datafactory.py / reports.py 样板保持一致。

对外响应契约与重构前保持一致（零破坏、可回滚）：
  - GET  /api/runs         → { records, total }
  - GET  /api/runs/stats   → { ... }
  - GET  /api/runs/{id}    → 记录详情 / 404
  - DELETE /api/runs       → { cleared }
passed 字段归一为 int 0/1（兼容既有 /api/runs 契约）。
"""
import asyncio

from fastapi import APIRouter, Depends

from app.core.response import fail, ok
from app.domain.runs.application.dto import (
    ClearRunRecordsCommand,
    RunRecordListQuery,
)
from app.domain.runs.application.run_record_app_service import (
    run_record_app_service,
)
from app.models.runs import RunClearQuery, RunQuery

router = APIRouter(tags=["runs"])


def _row(rec: dict) -> dict:
    """把 DDD 聚合视图归一为既有 DB 扁平行契约（passed 0/1 int）。"""
    if rec is None:
        return {}
    out = dict(rec)
    out["passed"] = 1 if out.get("passed") else 0
    return out


def _rows(records: list) -> list:
    return [_row(r) for r in records]


@router.get("/api/runs")
def api_list_runs(query: RunQuery = Depends()):
    """列出所有运行记录。"""
    result = run_record_app_service.list(RunRecordListQuery(
        file_path=query.file_path or "",
        source=query.source or "",
        passed=query.passed,
        search=query.search or "",
        limit=query.limit,
        offset=query.offset,
    ))
    records = _rows(result.get("list", []))
    total = result.get("total", len(records))
    return ok({"records": records, "total": total})


@router.get("/api/runs/stats")
async def api_run_stats():
    """运行记录统计。"""
    return ok(await asyncio.to_thread(run_record_app_service.stats))


@router.get("/api/runs/{record_id}")
def api_get_run(record_id: str):
    """获取单条运行记录详情。"""
    record = run_record_app_service.get(record_id)
    if not record:
        return fail(f"记录 {record_id} 不存在", 404)
    return ok(_row(record))


@router.delete("/api/runs")
def api_clear_runs(query: RunClearQuery = Depends()):
    """清空运行记录。

    支持按 source 定向清理（如只清 single/project/websocket/task 中的某一来源）；
    未指定 source 时清空全部记录。
    """
    cleared = run_record_app_service.clear(
        ClearRunRecordsCommand(source=query.source or ""),
    )
    return ok({"cleared": cleared})
