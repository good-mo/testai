# app/domain/template/interfaces/router.py
"""template 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.template.application.template_app_service import template_app_service

router = APIRouter(tags=["template"])


@router.get("/api/template/{scope_type}")
def list_templates(scope_type: str, request: Request):
    """列表查询模板。"""
    try:
        from app.domain.template.application.dto import ListTemplatesCommand
        cmd = ListTemplatesCommand(
            scope_type=scope_type,
            scope_id=request.query_params.get("scope_id", ""),
            scene=request.query_params.get("scene", "FUNCTIONAL")
        )
        result = template_app_service.list_templates(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))


@router.get("/api/template/{scope_type}/{template_id}")
def get_template(scope_type: str, template_id: str, request: Request):
    """获取模板详情。"""
    try:
        result = template_app_service.get_template_by_id(scope_type, template_id)
        if result:
            return ok(result)
        return fail("Template not found", code=404)
    except Exception as e:
        return fail(str(e))


@router.post("/api/template/{scope_type}")
async def create_template(scope_type: str, request: Request):
    """创建模板。"""
    try:
        body = await request.json()
        result = template_app_service.add_template(scope_type, body)
        return ok(result)
    except Exception as e:
        return fail(str(e))


@router.put("/api/template/{scope_type}/{template_id}")
async def update_template(scope_type: str, template_id: str, request: Request):
    """更新模板。"""
    try:
        body = await request.json()
        result = template_app_service.update_template(scope_type, template_id, body)
        return ok(result)
    except Exception as e:
        return fail(str(e))


@router.delete("/api/template/{template_id}")
def delete_template(template_id: str, request: Request):
    """删除模板。"""
    try:
        result = template_app_service.delete_template_by_id(template_id)
        return ok({"deleted": result})
    except Exception as e:
        return fail(str(e))


@router.post("/api/template/{scope_type}/{scene}/default/{template_id}")
def set_default(scope_type: str, scene: str, template_id: str, request: Request):
    """设置默认模板。"""
    try:
        from app.domain.template.application.dto import SetDefaultCommand
        cmd = SetDefaultCommand(
            scope_type=scope_type,
            scope_id=request.query_params.get("scope_id", ""),
            scene=scene,
            template_id=template_id
        )
        result = template_app_service.set_default(cmd)
        return ok({"success": result})
    except Exception as e:
        return fail(str(e))
