# app/routers/system.py
"""系统级路由（Phase 3 重构：从 main.py 拆分）。"""
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.response import fail, ok
from app.logging_config import get_logger
from app.domain.environment.application.environment_app_service import environment_app_service

logger = get_logger(__name__)
router = APIRouter(tags=["system"])


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    """返回后端可用性 HTML fallback。"""
    return HTMLResponse("<h1>Test Generation Agent Toolkit</h1><p>API is running.</p>")


@router.get("/health")
def health():
    """健康检查。"""
    return ok({
        "status": "ok",
        "version": "0.2.0",
        "service": "tga",
    })


@router.get("/api/test-types")
def api_test_types():
    """返回支持的测试类型。"""
    return ok({
        "types": [
            {"key": "functional", "label": "功能测试", "icon": "🧪", "description": "验证业务功能正确性"},
            {"key": "api", "label": "接口测试", "icon": "🔌", "description": "验证 API 请求/响应契约"},
            {"key": "ui", "label": "UI 测试", "icon": "🎨", "description": "验证用户界面交互"},
            {"key": "performance", "label": "性能测试", "icon": "⚡", "description": "验证响应时间与吞吐量"},
            {"key": "security", "label": "安全测试", "icon": "🔒", "description": "验证注入/越权/敏感信息"},
            {"key": "compatibility", "label": "兼容性测试", "icon": "🖥️", "description": "验证跨版本/跨平台"},
            {"key": "reliability", "label": "可靠性测试", "icon": "🔧", "description": "验证幂等性/容错性"},
        ]
    })


@router.get("/api/debug/logs")
def api_debug_logs(limit: int = 100, level: Optional[str] = None):
    """调试日志查询。"""
    logs_dir = "logs"
    import os
    if not os.path.isdir(logs_dir):
        return ok({"logs": []})
    files = sorted(os.listdir(logs_dir), reverse=True)
    logs = []
    for f in files[:3]:
        path = os.path.join(logs_dir, f)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()[-limit:]
                for line in lines:
                    logs.append({"file": f, "line": line.strip()})
        except Exception:
            pass
    return ok({"logs": logs, "total": len(logs)})


@router.delete("/api/debug/logs")
def api_clear_debug_logs():
    """清空调试日志。"""
    import os
    logs_dir = "logs"
    if not os.path.isdir(logs_dir):
        return ok({"cleared": 0})
    count = 0
    for f in os.listdir(logs_dir):
        path = os.path.join(logs_dir, f)
        try:
            os.remove(path)
            count += 1
        except Exception:
            pass
    return ok({"cleared": count})


@router.get("/api/alerts")
def api_list_alerts(limit: int = 50, severity: Optional[str] = None):
    """告警列表。"""
    from app.domain.environment.application.dto import ListAlertsQuery
    query = ListAlertsQuery(limit=limit, level=severity)
    alerts = environment_app_service.list_alerts(query)
    return ok({"alerts": alerts, "total": len(alerts)})


@router.post("/api/alerts/{alert_id}/resolve")
def api_resolve_alert(alert_id: str):
    """解决告警。"""
    from app.domain.environment.application.dto import ResolveAlertCommand
    cmd = ResolveAlertCommand(alert_id=alert_id)
    result = environment_app_service.resolve_alert(cmd)
    if not result:
        return fail(f"告警 {alert_id} 不存在", 404)
    return ok({"resolved": True, "alert_id": alert_id})
