# app/domain/test_insight/interfaces/router.py
"""test_insight 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.test_insight.application.test_insight_app_service import test_insight_app_service

router = APIRouter(tags=["test_insight"])


@router.post("/api/test-insight/trace")
async def record_trace(request: Request):
    """Record Trace。"""
    try:
        body = await request.json()
        from app.domain.test_insight.application.dto import RecordTraceCommand
        cmd = RecordTraceCommand(**body)
        result = test_insight_app_service.record_trace(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/test-insight/trace/{trace_id}")
def get(trace_id: str, request: Request):
    """Get。"""
    try:
        result = test_insight_app_service.get(trace_id)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/test-insight/traces")
def list(request: Request):
    """List。"""
    try:
        from app.domain.test_insight.application.dto import TraceListQuery
        cmd = TraceListQuery(**dict(request.query_params))
        result = test_insight_app_service.list(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/test-insight/coverage/{file_path}")
def prove_coverage(file_path: str, request: Request):
    """Prove Coverage。"""
    try:
        result = test_insight_app_service.prove_coverage(file_path)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/test-insight/stats")
def stats(request: Request):
    """Stats。"""
    try:
        result = test_insight_app_service.stats()
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/test-insight/value")
def get_value(request: Request):
    """Get Value。"""
    try:
        result = test_insight_app_service.get_value()
        return ok(result)
    except Exception as e:
        return fail(str(e))
