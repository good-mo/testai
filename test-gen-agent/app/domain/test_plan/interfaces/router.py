# app/domain/test_plan/interfaces/router.py
"""test_plan 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.test_plan.application.test_plan_app_service import test_plan_app_service

router = APIRouter(tags=["test_plan"])


@router.post("/api/test-plan")
async def create(request: Request):
    """Create。"""
    try:
        body = await request.json()
        from app.domain.test_plan.application.dto import CreatePlanCommand
        cmd = CreatePlanCommand(**body)
        result = test_plan_app_service.create(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/test-plan/{plan_id}")
def get(plan_id: str, request: Request):
    """Get。"""
    try:
        result = test_plan_app_service.get(plan_id)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.put("/api/test-plan/{plan_id}")
async def update(plan_id: str, request: Request):
    """Update。"""
    try:
        body = await request.json()
        body["plan_id"] = plan_id
        from app.domain.test_plan.application.dto import UpdatePlanCommand
        cmd = UpdatePlanCommand(**body)
        result = test_plan_app_service.update(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/test-plan/{plan_id}/status")
async def change_status(request: Request):
    """Change Status。"""
    try:
        body = await request.json()
        from app.domain.test_plan.application.dto import ChangeStatusCommand
        cmd = ChangeStatusCommand(**body)
        result = test_plan_app_service.change_status(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/test-plan/{plan_id}/archive")
async def archive(plan_id: str, request: Request):
    """Archive。"""
    try:
        result = test_plan_app_service.archive(plan_id)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.delete("/api/test-plan/{plan_id}")
def delete(plan_id: str, request: Request):
    """Delete。"""
    try:
        result = test_plan_app_service.delete(plan_id)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/test-plan/{plan_id}/case")
async def add_case(request: Request):
    """Add Case。"""
    try:
        body = await request.json()
        from app.domain.test_plan.application.dto import AddCaseCommand
        cmd = AddCaseCommand(**body)
        result = test_plan_app_service.add_case(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.delete("/api/test-plan/{plan_id}/case/{case_id}")
def remove_case(plan_id: str, case_id: str, request: Request):
    """Remove Case。"""
    try:
        from app.domain.test_plan.application.dto import RemoveCaseCommand
        cmd = RemoveCaseCommand("plan_id": plan_id, "case_id": case_id)
        result = test_plan_app_service.remove_case(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))
