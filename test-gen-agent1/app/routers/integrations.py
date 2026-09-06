# app/routers/integrations.py
"""服务集成/企微/钉钉/飞书兼容路由（工作流 C-3）。

原 app/adapters/domains/integrations.py 整体迁入 routers 层。
保持 TestPilot 兼容路径与 {code,message,data} 响应格式不变。

请求体统一改用 app/models/integration.py 建档的类型化模型，
收敛原先手写 `await read_body(request)` 的解析。
"""

import uuid

from fastapi import APIRouter, Request

from app.core.response import ok
from app.logging_config import get_logger
from app.models.integration import (
    DingTalkConfigBody,
    LarkConfigBody,
    LarkSuiteConfigBody,
    PlatformEnableBody,
    ServiceIntegrationBody,
    ServiceIntegrationDeleteBody,
    ServiceIntegrationValidateBody,
    WeComConfigBody,
)

logger = get_logger(__name__)
router = APIRouter(tags=["integrations-compat"])


@router.get("/service/integration/delete")
def service_integration_delete_get(request: Request):
    """服务集成删除（GET兼容）。"""
    return ok()


@router.get("/service/integration/validate")
def service_integration_validate_get(request: Request):
    """服务集成验证（GET兼容）。"""
    return ok()


@router.get("/service/integration/list")
def service_integration_list():
    """服务集成列表。"""
    return ok([])


@router.get("/service/integration/list/{org_id}")
def service_integration_list_path(org_id: str):
    """服务集成列表（路径参数版，前端 GET /service/integration/list/{orgId} 调用）。"""
    return ok([])


@router.post("/service/integration/add")
def service_integration_add(body: ServiceIntegrationBody = ServiceIntegrationBody()):
    """添加服务集成。"""
    return ok({"id": str(uuid.uuid4())})


@router.post("/service/integration/update")
def service_integration_update(body: ServiceIntegrationBody = ServiceIntegrationBody()):
    """更新服务集成。"""
    return ok()


@router.post("/service/integration/delete")
def service_integration_delete(body: ServiceIntegrationDeleteBody = ServiceIntegrationDeleteBody()):
    """删除服务集成。"""
    return ok()


@router.get("/service/integration/script")
def service_integration_script():
    """服务集成脚本。"""
    return ok({})


@router.post("/service/integration/validate")
def service_integration_validate(body: ServiceIntegrationValidateBody = ServiceIntegrationValidateBody()):
    """校验服务集成。"""
    return ok({"success": True})


@router.post("/service/integration/validate/")
def service_integration_validate_trailing(body: ServiceIntegrationValidateBody = ServiceIntegrationValidateBody()):
    """校验服务集成（尾斜杠）。"""
    return ok({"success": True})


# ════════════════════════════════════════════════════════════
# P2-3: SSO 平台配置（企微 / 钉钉 / 飞书 / 飞书套件）
# ════════════════════════════════════════════════════════════


@router.get("/we_com/info")
def we_com_info():
    """企微信息。"""
    return ok({})


@router.get("/we_com/info/with_detail")
def we_com_info_with_detail():
    """企微信息详情。"""
    return ok({})


@router.post("/we_com/save")
def we_com_save(body: WeComConfigBody = WeComConfigBody()):
    """保存企微配置。"""
    return ok()


@router.post("/we_com/validate")
def we_com_validate(body: WeComConfigBody = WeComConfigBody()):
    """校验企微配置。"""
    return ok({"success": True})


@router.post("/we_com/enable")
def we_com_enable(body: PlatformEnableBody = PlatformEnableBody()):
    """启用企微。"""
    return ok()


@router.post("/we_com/change/validate")
def we_com_change_validate(body: WeComConfigBody = WeComConfigBody()):
    """变更校验企微。"""
    return ok({"success": True})


# 钉钉


@router.get("/ding_talk/info")
def ding_talk_info():
    """钉钉信息。"""
    return ok({})


@router.get("/ding_talk/info/with_detail")
def ding_talk_info_with_detail():
    """钉钉信息详情。"""
    return ok({})


@router.post("/ding_talk/save")
def ding_talk_save(body: DingTalkConfigBody = DingTalkConfigBody()):
    """保存钉钉配置。"""
    return ok()


@router.post("/ding_talk/validate")
def ding_talk_validate(body: DingTalkConfigBody = DingTalkConfigBody()):
    """校验钉钉配置。"""
    return ok({"success": True})


@router.post("/ding_talk/enable")
def ding_talk_enable(body: PlatformEnableBody = PlatformEnableBody()):
    """启用钉钉。"""
    return ok()


@router.post("/ding_talk/change/validate")
def ding_talk_change_validate(body: DingTalkConfigBody = DingTalkConfigBody()):
    """变更校验钉钉。"""
    return ok({"success": True})


# 飞书


@router.get("/lark/info")
def lark_info():
    """飞书信息。"""
    return ok({})


@router.get("/lark/info/with_detail")
def lark_info_with_detail():
    """飞书信息详情。"""
    return ok({})


@router.post("/lark/save")
def lark_save(body: LarkConfigBody = LarkConfigBody()):
    """保存飞书配置。"""
    return ok()


@router.post("/lark/validate")
def lark_validate(body: LarkConfigBody = LarkConfigBody()):
    """校验飞书配置。"""
    return ok({"success": True})


@router.post("/lark/enable")
def lark_enable(body: PlatformEnableBody = PlatformEnableBody()):
    """启用飞书。"""
    return ok()


@router.post("/lark/change/validate")
def lark_change_validate(body: LarkConfigBody = LarkConfigBody()):
    """变更校验飞书。"""
    return ok({"success": True})


# 飞书套件


@router.get("/lark_suite/info")
def lark_suite_info():
    """飞书套件信息。"""
    return ok({})


@router.get("/lark_suite/info/with_detail")
def lark_suite_info_with_detail():
    """飞书套件信息详情。"""
    return ok({})


@router.post("/lark_suite/save")
def lark_suite_save(body: LarkSuiteConfigBody = LarkSuiteConfigBody()):
    """保存飞书套件配置。"""
    return ok()


@router.post("/lark_suite/validate")
def lark_suite_validate(body: LarkSuiteConfigBody = LarkSuiteConfigBody()):
    """校验飞书套件配置。"""
    return ok({"success": True})


@router.post("/lark_suite/enable")
def lark_suite_enable(body: PlatformEnableBody = PlatformEnableBody()):
    """启用飞书套件。"""
    return ok()


@router.post("/lark_suite/change/validate")
def lark_suite_change_validate(body: LarkSuiteConfigBody = LarkSuiteConfigBody()):
    """变更校验飞书套件。"""
    return ok({"success": True})


# SSO 回调


# ════════════════════════════════════════════════════════════
# 路径参数兼容路由（自 path_param_fixes.py 迁移）
# ════════════════════════════════════════════════════════════

@router.get("/service/integration/delete/{id}")
@router.post("/service/integration/delete/{id}")
def service_integration_delete_path(id: str):
    """/service/integration/delete 带路径参数（前端 RESTful 调用兼容）。"""
    return ok({"id": id, "deleted": True})


@router.get("/service/integration/script/{pluginId}")
@router.post("/service/integration/script/{pluginId}")
def service_integration_script_path(pluginId: str):
    """/service/integration/script 带路径参数（前端 RESTful 调用兼容）。"""
    return ok({"id": pluginId, "script": ""})


@router.get("/service/integration/validate/{id}")
@router.post("/service/integration/validate/{id}")
def service_integration_validate_path(id: str):
    """/service/integration/validate 带路径参数（前端 RESTful 调用兼容）。"""
    return ok({"id": id, "valid": True})


@router.get("/service/integration/validate/{plugin_id}/{org_id}")
@router.post("/service/integration/validate/{plugin_id}/{org_id}")
def service_integration_validate_org_path(plugin_id: str, org_id: str):
    """/service/integration/validate 双路径参数（前端 configModal 校验调用）。"""
    return ok({"pluginId": plugin_id, "organizationId": org_id, "valid": True})
