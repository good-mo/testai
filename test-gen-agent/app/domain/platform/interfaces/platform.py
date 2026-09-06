# app/routers/platform.py
"""业务域路由：platform 兼容路由。迁移自 app/adapters/domains/platform.py，占位 stub 原样保留。"""


from fastapi import APIRouter, Body, Request

from app.core.response import ok
from app.logging_config import get_logger
from app.domain.platform.application.dto import LicenseAddRequest, LicenseValidateBody

logger = get_logger(__name__)
router = APIRouter(tags=["adapter-platform"])


@router.get("/license/validate")
def license_validate_get(request: Request):
    """授权验证（GET兼容）。

    前端 licenseStore.getValidateLicense() 期望返回 LicenseInfo 结构：
    { status, license: { count, expired, corporation, product, ... } }。
    """
    return ok({
        "status": "valid",
        "license": {
            "corporation": "AI Test Gen",
            "expired": "2099-12-31",
            "product": "Test Generation Agent",
            "edition": "Enterprise",
            "licenseVersion": "1.0",
            "count": 100,
        },
    })


@router.get("/setting/get/platform/info")
def setting_get_platform_info():
    """平台信息（前端 qrCodeConfig.vue 的 getPlatformSourceList 调用）。

    前端期望返回 PlatformSource[] 数组，元素含 platform/enable/valid/hasConfig。
    当前无二维码平台配置被保存（save 接口均为占位 stub），返回空数组避免
    前端 data.value.forEach 崩溃。
    """
    return ok([])


@router.get("/setting/get/platform/param")
def setting_get_platform_param():
    """平台参数（登录页 SSO 平台选项）。

    前端 getPlatformParamUrl() 期望返回 OrgOptionItem[]：{ id, name }，
    tabQrCode.vue 会据此渲染企业微信/钉钉/飞书等扫码登录 tab。
    当前仅启用 LOCAL 登录（/authentication/get-list 返回 ["LOCAL"]），
    故返回空数组，避免登录页渲染出不可用的扫码登录选项。
    """
    return ok([])


# ════════════════════════════════════════════════════════════
# P2-7: 授权  /license/*
# ════════════════════════════════════════════════════════════


@router.post("/license/add")
async def license_add(body: LicenseAddRequest = Body(default=None)):
    """添加授权。"""
    # stub：license 暂不落地，仅登记请求体（body 经 LicenseAddRequest 建模）
    return ok({"success": True})


@router.post("/license/validate")
async def license_validate(body: LicenseValidateBody = Body(default=None)):
    """校验授权。"""
    # stub：license 校验暂不落地，仅登记请求体（body 经 LicenseValidateBody 建模）
    return ok({
        "status": "valid",
        "license": {
            "corporation": "AI Test Gen",
            "expired": "2099-12-31",
            "product": "Test Generation Agent",
            "edition": "Enterprise",
            "licenseVersion": "1.0",
            "count": 100,
        },
    })


# ════════════════════════════════════════════════════════════
# P2-8: 认证  /authentication/*
# ════════════════════════════════════════════════════════════

