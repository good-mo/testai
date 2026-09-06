# app/routers/system.py
"""系统级路由（Phase 3 重构：从 main.py 拆分）。"""
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.response import fail, ok
from app.logging_config import get_logger
from app.services.environment_service import environment_service

logger = get_logger(__name__)
router = APIRouter(tags=["system"])


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    """返回后端可用性 HTML fallback。

    精简 Web 控制台（templates/index.html + static/）已删除，统一由
    /ms/ 前缀的 TestPilot 前端承载页面；根路径保留 HTML 契约，
    便于健康探测与老客户端兼容。
    """
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
    from app.core.response import ok
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


# 注意：此处曾注册 `GET /ms` 与 `GET /ms/{full_path:path}` 的占位透传路由。
# 由于 system_router 在 app/main.py 的业务路由阶段就被 include，其 catch-all
# 会抢先于 main.py 末尾注册的 SPA 回退路由命中，导致 /ms/xxx 全部返回
# `{"code":200,...,"data":null}`（Content-Type: application/json）而非 index.html，
# 浏览器把 JSON 当页面渲染 → TestPilot 前端白屏/打不开。
# 前端页面与静态资源统一由 app/main.py 的 ms_frontend 提供，这里不再重复注册。


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
    alerts = environment_service.list_alerts(limit=limit, level=severity)
    return ok({"alerts": alerts, "total": len(alerts)})


@router.post("/api/alerts/{alert_id}/resolve")
def api_resolve_alert(alert_id: str):
    """解决告警。"""
    result = environment_service.resolve_alert(alert_id)
    if not result:
        return fail(f"告警 {alert_id} 不存在", 404)
    return ok({"resolved": True, "alert_id": alert_id})
