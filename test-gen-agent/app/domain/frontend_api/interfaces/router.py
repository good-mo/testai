# app/domain/frontend_api/interfaces/router.py
"""frontend_api 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.frontend_api.application.frontend_api_app_service import frontend_api_app_service

router = APIRouter(tags=["frontend_api"])


@router.post("/api/frontend/import/postman")
async def import_postman(request: Request):
    """Import Postman。"""
    try:
        body = await request.json()
        from app.domain.frontend_api.application.dto import ImportFromPostmanCommand
        cmd = ImportFromPostmanCommand(**body)
        result = frontend_api_app_service.import_postman(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/frontend/import/swagger")
async def import_swagger(request: Request):
    """Import Swagger。"""
    try:
        body = await request.json()
        from app.domain.frontend_api.application.dto import ImportFromSwaggerCommand
        cmd = ImportFromSwaggerCommand(**body)
        result = frontend_api_app_service.import_swagger(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/frontend/definitions")
def list_api_definitions(request: Request):
    """List Api Definitions。"""
    try:
        result = frontend_api_app_service.list_api_definitions()
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/frontend/definitions")
async def create_api_definition(request: Request):
    """Create Api Definition。"""
    try:
        body = await request.json()
        result = frontend_api_app_service.create_api_definition(**body)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.get("/api/frontend/definitions/{def_id}")
def get_api_definition(def_id: str, request: Request):
    """Get Api Definition。"""
    try:
        result = frontend_api_app_service.get_api_definition(def_id)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.put("/api/frontend/definitions/{def_id}")
async def update_api_definition(def_id: str, request: Request):
    """Update Api Definition。"""
    try:
        body = await request.json()
        body["def_id"] = def_id
        result = frontend_api_app_service.update_api_definition(**body)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.delete("/api/frontend/definitions/{def_id}")
def delete_api_definition(def_id: str, request: Request):
    """Delete Api Definition。"""
    try:
        from app.domain.frontend_api.application.dto import None
        cmd = None("def_id": def_id)
        result = frontend_api_app_service.delete_api_definition(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))
