# app/domain/performance/interfaces/router.py
"""performance 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.performance.application.performance_app_service import performance_app_service

router = APIRouter(tags=["performance"])


@router.post("/api/performance")
async def create(request: Request):
    """Create。"""
    try:
        body = await request.json()
        from app.domain.performance.application.dto import CreatePerformanceTestCommand
        cmd = CreatePerformanceTestCommand(**body)
        result = performance_app_service.create(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/performance/{test_id}")
def get(test_id: str, request: Request):
    """Get。"""
    try:
        result = performance_app_service.get(test_id)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.put("/api/performance/{test_id}/thresholds")
async def configure_thresholds(test_id: str, request: Request):
    """Configure Thresholds。"""
    try:
        body = await request.json()
        body["test_id"] = test_id
        from app.domain.performance.application.dto import ConfigureThresholdsCommand
        cmd = ConfigureThresholdsCommand(**body)
        result = performance_app_service.configure_thresholds(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/performance/{test_id}/start")
async def start(request: Request):
    """Start。"""
    try:
        body = await request.json()
        from app.domain.performance.application.dto import StartTestCommand
        cmd = StartTestCommand(**body)
        result = performance_app_service.start(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/performance/{test_id}/result")
async def record_result(request: Request):
    """Record Result。"""
    try:
        body = await request.json()
        from app.domain.performance.application.dto import RecordResultCommand
        cmd = RecordResultCommand(**body)
        result = performance_app_service.record_result(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))
