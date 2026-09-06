# app/routers/auth_compat.py
"""认证兼容路由 auth_compat。迁移自 app/adapters/domains/auth.py，极简 stub 原样保留。"""


from fastapi import APIRouter, Request

from app.core.response import ok
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["adapter-auth"])


@router.get("/signout")
def signout_get(request: Request):
    """用户登出（GET兼容）。"""
    return ok()


@router.get("/authentication/get/by/type")
def authentication_get_by_type(type: str = ""):
    """按类型获取认证。

    前端 getAuthDetailByType() 期望返回 AuthItem 结构（id/enable/configuration 等），
    否则 redirectAuth() 会因 res.enable / res.configuration 缺失而异常。
    默认返回 enable=False 的认证源，前端据此提示「认证未启用」而不是崩溃。
    """
    return ok({
        "id": f"{type}-config",
        "enable": False,
        "createTime": 0,
        "updateTime": 0,
        "description": "",
        "name": type or "认证源",
        "type": type or "OIDC",
        "configuration": "{}",
    })


# ════════════════════════════════════════════════════════════
# P2-9: 个人模型  /personal/model/*
# ════════════════════════════════════════════════════════════
