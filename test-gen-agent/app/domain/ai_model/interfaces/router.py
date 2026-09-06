# app/domain/ai_model/interfaces/router.py
"""ai_model 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.ai_model.application.ai_model_app_service import ai_model_app_service

router = APIRouter(tags=["ai_model"])


@router.get("/api/ai-model")
def list(request: Request):
    """List。"""
    try:
        from app.domain.ai_model.application.dto import ListModelsCommand
        cmd = ListModelsCommand(**dict(request.query_params))
        result = ai_model_app_service.list(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/ai-model/{model_id}")
def get(request: Request):
    """Get。"""
    try:
        from app.domain.ai_model.application.dto import GetModelCommand
        cmd = GetModelCommand(**dict(request.query_params))
        result = ai_model_app_service.get(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/ai-model")
async def create(request: Request):
    """Create。"""
    try:
        body = await request.json()
        from app.domain.ai_model.application.dto import CreateModelCommand
        cmd = CreateModelCommand(**body)
        result = ai_model_app_service.create(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.put("/api/ai-model/{model_id}")
async def update(model_id: str, request: Request):
    """Update。"""
    try:
        body = await request.json()
        body["model_id"] = model_id
        from app.domain.ai_model.application.dto import UpdateModelCommand
        cmd = UpdateModelCommand(**body)
        result = ai_model_app_service.update(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.delete("/api/ai-model/{model_id}")
def delete(model_id: str, request: Request):
    """Delete。"""
    try:
        from app.domain.ai_model.application.dto import DeleteModelCommand
        cmd = DeleteModelCommand(model_id=model_id)
        result = ai_model_app_service.delete(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))
