# app/domain/resource_pool/interfaces/router.py
"""resource_pool 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.resource_pool.application.resource_pool_app_service import resource_pool_app_service

router = APIRouter(tags=["resource_pool"])


@router.post("/api/resource-pool")
async def create(request: Request):
    """Create。"""
    try:
        body = await request.json()
        from app.domain.resource_pool.application.dto import CreatePoolCommand
        cmd = CreatePoolCommand(**body)
        result = resource_pool_app_service.create(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/resource-pool")
def list(request: Request):
    """List。"""
    try:
        from app.domain.resource_pool.application.dto import ListPoolsCommand
        cmd = ListPoolsCommand(**dict(request.query_params))
        result = resource_pool_app_service.list(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/resource-pool/{pool_id}")
def get(request: Request):
    """Get。"""
    try:
        from app.domain.resource_pool.application.dto import GetPoolCommand
        cmd = GetPoolCommand(**dict(request.query_params))
        result = resource_pool_app_service.get(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.put("/api/resource-pool/{pool_id}")
async def update(pool_id: str, request: Request):
    """Update。"""
    try:
        body = await request.json()
        body["pool_id"] = pool_id
        from app.domain.resource_pool.application.dto import UpdatePoolCommand
        cmd = UpdatePoolCommand(**body)
        result = resource_pool_app_service.update(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.delete("/api/resource-pool/{pool_id}")
def delete(pool_id: str, request: Request):
    """Delete。"""
    try:
        from app.domain.resource_pool.application.dto import DeletePoolCommand
        cmd = DeletePoolCommand("pool_id": pool_id)
        result = resource_pool_app_service.delete(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/resource-pool/{pool_id}/enable")
async def set_enable(request: Request):
    """Set Enable。"""
    try:
        body = await request.json()
        from app.domain.resource_pool.application.dto import SetEnableCommand
        cmd = SetEnableCommand(**body)
        result = resource_pool_app_service.set_enable(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))
