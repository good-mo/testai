# app/domain/identity/interfaces/log_router.py
"""操作日志相关路由（DDD 架构）。"""

from fastapi import APIRouter

from app.core.response import ok
from app.domain.identity.application.identity_app_service import identity_app_service

router = APIRouter(tags=["identity-log"])


@router.get("/organization/log/user/list/{org_id}")
def organization_log_user_list_path(org_id: str):
    """组织日志用户列表（带路径参数）。"""
    # 从 identity 域获取用户列表
    from app.domain.identity.application.dto import UserListQuery
    query = UserListQuery(search="", page=1, page_size=1000)
    result = identity_app_service.list_users(query)
    users = result.get("list", [])
    return ok(users)
