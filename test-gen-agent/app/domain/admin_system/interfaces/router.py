# app/domain/admin_system/interfaces/router.py
"""admin_system 域路由适配器。"""
from fastapi import APIRouter, Request

from app.core.response import ok, fail
from app.domain.admin_system.application.admin_app_service import admin_system_app_service

router = APIRouter(tags=["admin_system"])


@router.post("/api/admin/organization/{org_id}/enable")
async def enable_organization(request: Request):
    """Enable Organization。"""
    try:
        body = await request.json()
        from app.domain.admin_system.application.dto import EnableOrgCommand
        cmd = EnableOrgCommand(**body)
        result = admin_system_app_service.enable_organization(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.post("/api/admin/organization/{org_id}/disable")
async def disable_organization(request: Request):
    """Disable Organization。"""
    try:
        body = await request.json()
        from app.domain.admin_system.application.dto import DisableOrgCommand
        cmd = DisableOrgCommand(**body)
        result = admin_system_app_service.disable_organization(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))

@router.delete("/api/admin/organization/{org_id}/member/{user_id}")
def remove_org_member(org_id: str, user_id: str, request: Request):
    """Remove Org Member。"""
    try:
        from app.domain.admin_system.application.dto import RemoveMemberCommand
        cmd = RemoveMemberCommand("org_id": org_id, "user_id": user_id)
        result = admin_system_app_service.remove_org_member(cmd)
        return ok(result)
    except Exception as e:
        return fail(str(e))
