# app/routers/reports.py
"""报告中心路由（report 域 DDD 接入 · 阶段 B）。

路由改为调用 report 域 DDD 应用服务 `report_app_service`（参数经应用层 DTO
翻译），业务规则（格式守卫/状态机/汇总口径）已下沉到 `app/domain/report/`。

对外响应契约与重构前保持一致（零破坏、可回滚）：
  - POST /api/reports/generate        → { report_path }
  - GET  /api/reports/list            → { reports: [{name, path}] }
  - GET  /api/reports/trash/list      → { reports: [文件名], total }
  - 回收站动作返回 ok/fail，404 语义不变
领域异常经一层薄翻译映射为既有 HTTP 状态码。
"""
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.response import fail, ok
from app.domain.common.exceptions import DomainException
from app.domain.report.application.dto import (
    DownloadCommand,
    GenerateCommand,
    PurgeCommand,
    RestoreCommand,
    TrashCommand,
    TrashListQuery,
)
from app.domain.report.application.report_app_service import report_app_service

router = APIRouter(tags=["reports"])

DEFAULT_FORMATS = {"html", "junit", "markdown"}


@router.post("/api/reports/generate")
def api_generate_report(req: Optional[dict] = None):
    """生成测试报告。"""
    format_type = "html"
    if req and isinstance(req, dict):
        format_type = req.get("format", "html")
    elif hasattr(req, "format"):
        format_type = req.format

    if format_type not in DEFAULT_FORMATS:
        return fail(f"不支持的格式: {format_type}", 400)

    try:
        result = report_app_service.generate(
            GenerateCommand(format_type=format_type)
        )
    except DomainException as exc:
        # 领域校验失败（如非法格式等）
        return fail(str(exc.message or exc), exc.status_code)

    if not result:
        return fail("无用例数据，无法生成报告", 404)

    return ok({"report_path": result.get("report_path")})


@router.get("/api/reports/list")
def api_list_reports():
    """列出已生成的报告。"""
    return ok({"reports": report_app_service.list_reports()})


@router.get("/api/reports/download/{filename}")
def api_download_report(filename: str):
    """下载报告文件。"""
    report_path = report_app_service.download(
        DownloadCommand(report_name=filename)
    )
    if not report_path:
        return fail(f"报告 {filename} 不存在", 404)
    return FileResponse(report_path, filename=filename)


@router.post("/api/reports/{filename}/trash")
def api_trash_report(filename: str):
    """将报告移入回收站。"""
    try:
        report_app_service.trash(TrashCommand(report_name=filename))
    except DomainException as exc:
        return fail(str(exc.message or exc), exc.status_code)
    return ok({"trashed": True, "filename": filename})


@router.get("/api/reports/trash/list")
def api_list_trash_reports():
    """列出回收站中的报告。"""
    result = report_app_service.list_trash(TrashListQuery())
    # 维持既有契约：reports 为回收站文件名列表
    reports = [item.get("name") for item in result.get("list", [])]
    return ok({"reports": reports, "total": result.get("total", len(reports))})


@router.post("/api/reports/trash/{filename}/restore")
def api_restore_report(filename: str):
    """从回收站恢复报告。"""
    try:
        report_app_service.restore(RestoreCommand(report_name=filename))
    except DomainException as exc:
        return fail(str(exc.message or exc), exc.status_code)
    return ok({"restored": True, "filename": filename})


@router.delete("/api/reports/trash/{filename}")
def api_purge_report(filename: str):
    """从回收站彻底删除报告。"""
    try:
        report_app_service.purge(PurgeCommand(report_name=filename))
    except DomainException as exc:
        return fail(str(exc.message or exc), exc.status_code)
    return ok({"purged": True, "filename": filename})
