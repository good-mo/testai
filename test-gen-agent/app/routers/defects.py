# app/routers/defects.py
"""缺陷管理路由（Phase 3 重构 · DDD 迁移 · 阶段 B router 直连）。

本路由改为直接调用缺陷域 DDD 应用服务 `defect_app_service`
（参数经应用层 DTO 翻译），不再经 `app.services.defect_service` 薄门面中转，
与 datafactory.py / reports.py 样板保持一致。

对外响应契约与重构前保持一致（零破坏、可回滚）：
  - GET    /api/defects                     → { defects, stats, total }
  - POST   /api/defects                     → 缺陷详情
  - GET    /api/defects/{id}                → 缺陷详情 / 404
  - GET    /api/defects/trash               → { items, total }
  - PUT    /api/defects/{id}                → 更新后详情 / 404 / 400
  - DELETE /api/defects/{id}                → 彻底删除
  - POST   /api/defects/{id}/trash          → 软删入回收站
  - POST   /api/defects/{id}/restore        → 恢复
  - DELETE /api/defects/trash/{id}          → 彻底清除回收站项
  - POST   /api/defects/trash/recover       → 批量恢复
  - POST   /api/defects/trash/batch-delete  → 批量清除
领域异常经一层薄翻译映射为既有 HTTP 状态码；tags 输出仍归一为 JSON 字符串。
"""
import json
from typing import Optional

from fastapi import APIRouter

from app.core.response import fail, ok
from app.domain.common.exceptions import (
    AggregateNotFound,
    DomainValidationError,
    InvariantViolation,
)
from app.domain.defects.application.defect_app_service import defect_app_service
from app.domain.defects.application.dto import (
    CreateDefectCommand,
    DefectListQuery,
    PermanentDeleteCommand,
    UpdateDefectCommand,
)
from app.models.defect import DefectCreate, DefectIdsBody, DefectUpdate

router = APIRouter(tags=["defects"])

# 非法严重程度回落到 major（兼容 bug_add 前端可能透传第三方未知严重度）
_VALID_SEVERITIES = ("blocker", "critical", "major", "minor", "trivial")


def _row_schema(item: dict) -> dict:
    """DDD Defect.to_dict → 既有 DB 行契约（tags 归一为 JSON 字符串）。"""
    if item is None:
        return {}
    out = dict(item)
    if isinstance(out.get("tags"), list):
        out["tags"] = json.dumps(out["tags"], ensure_ascii=False)
    return out


def _not_found(defect_id: str):
    return fail(f"缺陷不存在或已删除: {defect_id}", 404)


@router.get("/api/defects")
def api_list_defects(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """列出缺陷（有效项）。"""
    result = defect_app_service.list(DefectListQuery(
        status=status or "", severity=severity or "",
        limit=int(limit or 100), offset=int(offset or 0),
    ))
    defects = [_row_schema(d) for d in result.get("list", [])]
    total = int(result.get("total", 0))
    stats = defect_app_service.stats()
    return ok({"defects": defects, "stats": stats, "total": total})


@router.post("/api/defects")
def api_create_defect(body: DefectCreate):
    """创建缺陷。"""
    severity = body.severity or "major"
    if severity not in _VALID_SEVERITIES:
        severity = "major"
    item = defect_app_service.create(CreateDefectCommand(
        title=body.title,
        description=body.description,
        severity=severity,
        status=body.status,
        file_path=body.file_path,
        test_case_id=body.test_case_id,
        error_snippet=body.error_snippet,
        assignee=body.assignee,
        tags=[],
        operator="system",
    ))
    return ok(_row_schema(item))


@router.get("/api/defects/trash")
def api_list_defect_trash(limit: int = 100, offset: int = 0):
    """列出回收站中的缺陷。"""
    result = defect_app_service.list_trash(
        limit=int(limit or 100), offset=int(offset or 0),
    )
    items = [_row_schema(d) for d in result.get("list", [])]
    return ok({"items": items, "total": int(result.get("total", 0))})


@router.get("/api/defects/{defect_id}")
def api_get_defect(defect_id: str):
    """获取单个缺陷。"""
    try:
        item = defect_app_service.get_or_raise(defect_id)
    except AggregateNotFound:
        return _not_found(defect_id)
    return ok(_row_schema(item))


@router.put("/api/defects/{defect_id}")
def api_update_defect(defect_id: str, body: DefectUpdate):
    """更新缺陷。"""
    updates = body.model_dump(exclude_unset=True)
    try:
        updated = defect_app_service.update(UpdateDefectCommand(
            defect_id=defect_id,
            title=updates.get("title"),
            description=updates.get("description"),
            severity=updates.get("severity"),
            status=updates.get("status"),
            file_path=updates.get("file_path"),
            test_case_id=updates.get("test_case_id"),
            error_snippet=updates.get("error_snippet"),
            assignee=updates.get("assignee"),
            tags=None,
            operator="system",
        ))
    except AggregateNotFound:
        return _not_found(defect_id)
    except (DomainValidationError, InvariantViolation) as exc:
        return fail(str(exc), 400)
    return ok(_row_schema(updated))


@router.delete("/api/defects/{defect_id}")
def api_delete_defect(defect_id: str):
    """删除缺陷（彻底删除）。"""
    try:
        defect_app_service.permanent_delete(PermanentDeleteCommand(defect_id=defect_id))
    except AggregateNotFound:
        return _not_found(defect_id)
    return ok({"deleted": True})


@router.post("/api/defects/{defect_id}/trash")
def api_trash_defect(defect_id: str):
    """将缺陷软删除，移入回收站。"""
    try:
        defect_app_service.soft_delete(defect_id, operator="system")
    except (AggregateNotFound, DomainValidationError):
        # 不存在/已在回收站（重复删除）保持既有 404 语义
        return _not_found(defect_id)
    return ok({"deleted": True, "defect_id": defect_id})


@router.post("/api/defects/{defect_id}/restore")
def api_restore_defect(defect_id: str):
    """从回收站恢复缺陷。"""
    try:
        defect_app_service.restore(defect_id, operator="system")
    except (AggregateNotFound, DomainValidationError):
        return _not_found(defect_id)
    return ok({"restored": True, "defect_id": defect_id})


@router.delete("/api/defects/trash/{defect_id}")
def api_purge_defect(defect_id: str):
    """从回收站彻底删除缺陷。"""
    try:
        defect_app_service.purge(defect_id)
    except AggregateNotFound:
        return _not_found(defect_id)
    return ok({"purged": True, "defect_id": defect_id})


@router.post("/api/defects/trash/recover")
def api_batch_restore_defects(body: DefectIdsBody):
    """批量从回收站恢复缺陷。"""
    restored = 0
    for did in body.ids:
        try:
            if defect_app_service.restore(did, operator="system"):
                restored += 1
        except (AggregateNotFound, DomainValidationError):
            continue
    return ok({"restored": restored})


@router.post("/api/defects/trash/batch-delete")
def api_batch_purge_defects(body: DefectIdsBody):
    """批量从回收站彻底删除缺陷。"""
    purged = 0
    for did in body.ids:
        try:
            if defect_app_service.purge(did):
                purged += 1
        except AggregateNotFound:
            continue
    return ok({"purged": purged})
