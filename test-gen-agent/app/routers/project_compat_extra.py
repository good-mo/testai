# app/routers/project_compat_extra.py
"""project_compat 拆分：模板/自定义字段与功能函数/状态流（P4 超大文件拆分）。

自 app/routers/project_compat.py 按业务域搬移，纯路由搬移、行为不变，
响应沿用统一 ok()/fail()/_paginate() 与 read_body() 辅助函数。
"""

import uuid
from typing import Dict

from fastapi import APIRouter, Request

from app.core.response import fail, ok, page_result, read_body
from app.logging_config import get_logger
from app.models.workflow import (
    WorkflowDefinitionUpdateBody,
    WorkflowFlowUpdateBody,
    WorkflowStatusAddBody,
    WorkflowStatusDeleteBody,
    WorkflowStatusSortBody,
    WorkflowStatusUpdateBody,
)
from app.services.project_service import project_service
from app.services.template_service import template_service
from app.services.workflow_service import workflow_service

logger = get_logger(__name__)
router = APIRouter(tags=["adapter-project-extra"])


"""project_compat 拆分：template,custom,status 域路由（P4 超大文件拆分）。

自 app/routers/project_compat.py 按域搬移，纯搬移、行为不变。
"""

async def _common_script_page(project_id: str = "", keyword: str = "", current: int = 1, page_size: int = 10):
    """公共脚本分页公共逻辑。"""
    items = project_service.list_custom_funcs(project_id=project_id, keyword=keyword)
    return page_result(items, len(items), current=current, page_size=page_size)
def _default_template_status() -> Dict:
    """默认模板启用状态（前端: Record<string, boolean>，键为模板场景类型）。"""
    return {
        "FUNCTIONAL": True,
        "API": False,
        "UI": False,
        "TEST_PLAN": False,
        "BUG": True,
    }

@router.get("/project/custom/field/delete")
def project_custom_field_delete_get():
    """项目自定义字段删除（GET兼容）。"""
    return ok()

@router.get("/project/status/flow/setting/status/delete")
def project_status_flow_status_delete_get():
    """项目状态流设置状态删除（GET兼容）。"""
    return ok()

@router.post("/project/custom/func/status")
async def project_custom_func_status_post(request: Request):
    """项目自定义函数状态（更新状态）。"""
    body = await read_body(request)
    func_id = body.get("id", "")
    status = body.get("status", "")
    if not func_id or not status:
        return fail("缺少 id 或 status", 400)
    success = project_service.update_custom_func_status(func_id, status)
    return ok({"id": func_id, "status": status}) if success else fail("函数不存在", 404)

@router.post("/project/template/add")
async def project_template_add(request: Request):
    """添加项目模板（前端 addTemplate.vue 创建保存）。

    入参: ActionTemplateManage { name, remark, scene, scopeId, customFields, systemFields, ... }。
    真实落库后返回带 id 的模板对象。
    """
    body = await read_body(request)
    template = template_service.add_template("PROJECT", body)
    if template is None:
        return fail("保存模板失败", 500)
    return ok(template)

@router.post("/project/template/update")
async def project_template_update(request: Request):
    """更新项目模板（前端 addTemplate.vue 编辑保存）。"""
    body = await read_body(request)
    template_id = body.get("id", "")
    if not template_id:
        return fail("模板 id 不能为空", 400)
    template = template_service.update_template("PROJECT", template_id, body)
    return ok(template) if template else fail("模板不存在", 404)

@router.post("/project/template/delete")
async def project_template_delete(request: Request):
    """删除项目模板。"""
    body = await read_body(request)
    template_id = body.get("id", "")
    if not template_id:
        return fail("模板 id 不能为空", 400)
    deleted = template_service.delete_template(template_id)
    return ok({"id": template_id, "deleted": deleted})

@router.get("/project/template/get")
def project_template_get(id: str = ""):
    """获取项目模板详情。"""
    if not id:
        return ok({})
    return ok(template_service.get_template("PROJECT", id) or {})

@router.get("/project/template/list")
def project_template_list(project_id: str = "", template_type: str = ""):
    """项目模板列表（无路径参数兼容）。"""
    if not project_id:
        return ok([])
    return ok(template_service.list_templates("PROJECT", project_id, template_type))

@router.post("/project/template/enable/config")
async def project_template_enable_config(request: Request):
    """启用模板配置。"""
    await read_body(request)
    return ok()

@router.post("/project/template/set-default")
async def project_template_set_default(request: Request):
    """设置默认模板。"""
    await read_body(request)
    return ok()

@router.post("/project/template/img/preview")
async def project_template_img_preview(request: Request):
    """模板图片预览。"""
    await read_body(request)
    return ok({})

@router.post("/project/template/upload/temp/img")
def project_template_upload_temp_img():
    """模板临时图片上传。"""
    return ok({"id": str(uuid.uuid4())})

@router.post("/project/custom/field/add")
async def project_custom_field_add(request: Request):
    """添加自定义字段（项目管理-模板-字段设置页面）。

    入参: AddOrUpdateField { name, scene, type, remark, scopeId, options, enableOptionKey, ... }。
    返回: 创建的字段对象（含 id）。
    """
    body = await read_body(request)
    field_id = body.get("id") or str(uuid.uuid4())
    field = project_service.upsert_custom_field(field_id, body)
    return ok(field)

@router.post("/project/custom/field/update")
async def project_custom_field_update(request: Request):
    """更新自定义字段（项目管理-模板-字段设置页面）。

    入参: AddOrUpdateField { id, name, scene, type, remark, options, enableOptionKey, ... }。
    返回: 更新后的字段对象。
    """
    body = await read_body(request)
    if not body.get("id"):
        return fail("字段 id 不能为空", code=400)
    field = project_service.upsert_custom_field(body.get("id"), body)
    return ok(field)

@router.post("/project/custom/field/delete")
async def project_custom_field_delete(request: Request):
    """删除自定义字段。"""
    body = await read_body(request)
    field_id = body.get("id")
    if not field_id:
        return fail("字段 id 不能为空", code=400)
    deleted = project_service.delete_custom_field(field_id)
    return ok({"id": field_id, "deleted": deleted})

@router.get("/project/custom/field/get")
def project_custom_field_get(id: str = ""):
    """获取自定义字段。"""
    if not id:
        return ok({})
    return ok(project_service.get_custom_field(id) or {})

@router.get("/project/custom/field/list")
def project_custom_field_list(project_id: str = ""):
    """自定义字段列表。"""
    return ok(project_service.list_custom_fields(project_id, ""))

@router.get("/project/status/flow/setting/get")
def project_status_flow_setting_get(project_id: str = ""):
    """项目状态流设置（无路径参数兼容）。"""
    if not project_id:
        return ok([])
    return ok(workflow_service.list_statuses("PROJECT", project_id, "FUNCTIONAL"))

@router.post("/project/status/flow/setting/status/add")
async def project_status_flow_setting_status_add(request: Request):
    """添加项目工作流状态。

    前端 addWorkStatusModal 发送 { scopeId, scene, name, remark, allTransferTo }，
    真实落库后返回带 id/pos 等字段的状态对象。
    """
    m = WorkflowStatusAddBody.model_validate(await read_body(request))
    status = workflow_service.add_status(
        name=m.effective_name, scene=m.effective_scene, scope_id=m.effective_scope_id,
        scope_type="PROJECT", remark=m.effective_remark,
        all_transfer_to=m.effective_all_transfer_to,
    )
    return ok(status)

@router.post("/project/status/flow/setting/status/update")
async def project_status_flow_setting_status_update(request: Request):
    """更新项目工作流状态。"""
    m = WorkflowStatusUpdateBody.model_validate(await read_body(request))
    status_id = m.effective_status_id
    if not status_id:
        return fail("状态 id 不能为空", 400)
    result = workflow_service.update_status(
        status_id, name=m.effective_name, remark=m.effective_remark,
        status_definitions=m.effective_status_definitions,
    )
    return ok(result) if result else fail("状态不存在", 404)

@router.post("/project/status/flow/setting/status/delete")
async def project_status_flow_setting_status_delete(request: Request):
    """删除项目工作流状态。"""
    m = WorkflowStatusDeleteBody.model_validate(await read_body(request))
    status_id = m.effective_status_id
    if status_id:
        workflow_service.delete_status(status_id)
    return ok({"id": status_id, "deleted": True})

@router.post("/project/status/flow/setting/status/sort")
async def project_status_flow_setting_status_sort(request: Request):
    """状态流状态排序。"""
    m = WorkflowStatusSortBody.model_validate(await read_body(request))
    status_ids = m.effective_status_ids
    if status_ids:
        workflow_service.sort_statuses(status_ids)
    return ok()

@router.post("/project/status/flow/setting/status/flow/update")
async def project_status_flow_setting_status_flow_update(request: Request):
    """更新状态流转关系。"""
    m = WorkflowFlowUpdateBody.model_validate(await read_body(request))
    source_id = m.effective_source_id
    target_ids = m.effective_target_ids
    if source_id:
        workflow_service.update_flows(str(source_id), target_ids)
    return ok()

@router.post("/project/status/flow/setting/status/definition/update")
async def project_status_flow_setting_status_definition_update(request: Request):
    """设置状态为初始态/结束态。

    前端 setProjectWorkState 发送 { statusId, definitionId, enable }。
    definitionId: "START" / "END"。
    """
    m = WorkflowDefinitionUpdateBody.model_validate(await read_body(request))
    status_id = m.effective_status_id
    definition_id = m.effective_definition_id
    enable = m.effective_enable
    if not status_id or not definition_id:
        return fail("缺少参数", 400)
    success = workflow_service.set_definition(status_id, definition_id, enable)
    return ok() if success else fail("状态不存在", 404)

@router.post("/project/custom/func/add")
async def project_custom_func_add(request: Request):
    """添加自定义函数。"""
    body = await read_body(request)
    name = body.get("name", "未命名函数")
    script = body.get("script", "")
    func_type = body.get("type", "HTTP")
    description = body.get("description", "")
    project_id = body.get("projectId", "")
    status = body.get("status", "DRAFT")
    tags = body.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    params = body.get("params", "[]")
    result = body.get("result", "")

    # 获取当前用户
    current_user = "admin"
    try:
        from app.auth.router import get_current_user as _get_user
        user = await _get_user(request)
        if user:
            current_user = user.get("username", "admin")
    except Exception:
        pass

    func_id = uuid.uuid4().hex[:12]
    project_service.create_custom_func(
        func_id=func_id, name=name, script=script,
        func_type=func_type, description=description,
        status=status, project_id=project_id, tags=tags,
        params=params, result=result, create_user=current_user,
    )
    return ok({"id": func_id, "name": name})

@router.post("/project/custom/func/update")
async def project_custom_func_update(request: Request):
    """更新自定义函数。"""
    body = await read_body(request)
    func_id = body.get("id", "")
    if not func_id:
        return fail("缺少 id", 400)

    # 构建可更新字段
    updates = {}
    for field in ["name", "script", "type", "description", "status"]:
        if field in body:
            updates[field] = body[field]
    if "tags" in body:
        updates["tags"] = body.get("tags", [])
    if "params" in body:
        updates["params"] = body.get("params", "[]")
    if "result" in body:
        updates["result"] = body.get("result", "")

    current_user = "admin"
    try:
        from app.auth.router import get_current_user as _get_user
        user = await _get_user(request)
        if user:
            current_user = user.get("username", "admin")
    except Exception:
        pass

    success = project_service.update_custom_func(func_id, updates, update_user=current_user)
    return ok() if success else fail("函数不存在", 404)

@router.post("/project/custom/func/delete")
async def project_custom_func_delete(request: Request):
    """删除自定义函数。"""
    body = await read_body(request)
    func_id = body.get("id", body.get("funcId", ""))
    if not func_id:
        return fail("缺少 id", 400)
    success = project_service.delete_custom_func(func_id)
    return ok({"id": func_id, "deleted": success})

@router.get("/project/custom/func/page")
async def project_custom_func_page(project_id: str = ""):
    """自定义函数分页（GET兼容）。"""
    return await _common_script_page(project_id=project_id)

@router.post("/project/custom/func/page")
async def project_custom_func_page_post(request: Request):
    """自定义函数分页（POST，前端主用）。"""
    body = await read_body(request)
    project_id = body.get("projectId", body.get("project_id", ""))
    keyword = body.get("keyword", "")
    current = body.get("current", 1)
    page_size = body.get("pageSize", 10)
    return await _common_script_page(
        project_id=project_id,
        keyword=keyword,
        current=current,
        page_size=page_size,
    )

@router.get("/project/custom/func/detail")
def project_custom_func_detail(id: str = ""):
    """自定义函数详情。"""
    item = project_service.get_custom_func(id) if id else None
    return ok(item or {})

@router.get("/project/custom/func/status")
def project_custom_func_status(project_id: str = ""):
    """自定义函数状态。"""
    rows = project_service.list_custom_func_status(project_id=project_id)
    return ok([{"id": r.get("id", ""), "name": r.get("name", ""), "status": r.get("status", "")} for r in rows])

@router.get("/project/custom/func/columns-option/")
def project_custom_func_columns_option(project_id: str = ""):
    """自定义函数列选项。"""
    return ok([])

@router.get("/project/custom/func/history/page")
def project_custom_func_history_page(project_id: str = ""):
    """自定义函数历史（GET兼容）。"""
    return page_result([], len([]), current=1, page_size=10)

@router.post("/project/custom/func/history/page")
async def project_custom_func_history_page_post(request: Request):
    """自定义函数历史（POST，前端主用）。"""
    body = await read_body(request)
    current = body.get("current", 1)
    page_size = body.get("pageSize", 10)
    return page_result([], len([]), current=current, page_size=page_size)

@router.get("/project/custom/field/list/{project_id}/{scene}")
@router.post("/project/custom/field/list/{project_id}/{scene}")
def project_custom_field_list_path(project_id: str, scene: str):
    """获取项目自定义字段列表（带路径参数）。

    前端调用: /project/custom/field/list/{scopedId}/{scene}，scopedId 为项目ID，
    scene 为场景(FUNCTIONAL/BUG/API 等)。返回字段对象数组。
    """
    scene = scene or "FUNCTIONAL"
    fields = project_service.list_custom_fields(project_id, scene)
    return ok(fields)

@router.get("/project/custom/func/delete/{func_id}")
@router.post("/project/custom/func/delete/{func_id}")
def project_custom_func_delete_path(func_id: str):
    """删除项目自定义功能（带路径参数）。"""
    success = project_service.delete_custom_func(func_id)
    return ok({"id": func_id, "deleted": success})

@router.get("/project/status/flow/setting/status/sort/{project_id}/{status_id}")
@router.post("/project/status/flow/setting/status/sort/{project_id}/{status_id}")
async def project_status_flow_sort_path(project_id: str, status_id: str, request: Request):
    """项目状态流排序（带路径参数）。

    前端调用: POST /project/status/flow/setting/status/sort/{scopedId}/{scene}，
    body 为排序后的状态 ID 数组。
    """
    m = WorkflowStatusSortBody.model_validate(await read_body(request))
    status_ids = [d for d in m.effective_status_ids if d]
    if status_ids:
        workflow_service.sort_statuses(status_ids)
    return ok({"project_id": project_id, "scene": status_id, "sorted": True})

@router.get("/project/template/delete/{template_id}")
@router.post("/project/template/delete/{template_id}")
def project_template_delete_path(template_id: str):
    """删除项目模板（带路径参数）。

    前端调用点: deleteProjectTemplate -> /project/template/delete/{id}。
    """
    deleted = template_service.delete_template(template_id)
    return ok({"id": template_id, "deleted": deleted})

@router.get("/project/template/get/{template_id}")
@router.post("/project/template/get/{template_id}")
def project_template_get_path(template_id: str):
    """获取项目模板（带路径参数）。

    前端调用点: getProjectTemplateInfo -> /project/template/get/{id}，
    返回完整模板详情（name/customFields/systemFields 等），供编辑/预览页渲染。
    """
    return ok(template_service.get_template("PROJECT", template_id) or {})

@router.get("/project/template/list/{project_id}/{scene}")
@router.post("/project/template/list/{project_id}/{scene}")
def project_template_list_path(project_id: str, scene: str):
    """获取项目模板列表（带路径参数）。

    前端调用点: getProjectTemplateList -> /project/template/list/{projectId}/{scene}，
    scene 为 FUNCTIONAL/BUG/API 等场景，返回模板数组（表格 useTable 依赖数组）。
    """
    return ok(template_service.list_templates("PROJECT", project_id, scene))

@router.get("/project/template/set-default/{project_id}/{template_id}")
@router.post("/project/template/set-default/{project_id}/{template_id}")
def project_template_set_default_path(project_id: str, template_id: str):
    """设置项目默认模板（带路径参数）。

    前端调用点: setDefaultTemplate -> /project/template/set-default/{projectId}/{id}。
    """
    template = template_service.get_template("PROJECT", template_id)
    if template is None:
        return fail("模板不存在", 404)
    scene = template.get("scene") or "FUNCTIONAL"
    success = template_service.set_default("PROJECT", project_id, scene, template_id)
    return ok({"template_id": template_id, "project_id": project_id, "set_default": success})

@router.get("/project/custom/func/columns-option/{project_id}")
def project_custom_func_columns_option_path(project_id: str):
    """获取公共脚本列选项（带路径参数）。"""
    # 返回用户下拉选项（数据统一下沉 auth_service，路由层不再手写 SQL）
    try:
        from app.services.auth_service import auth_service
        users = auth_service.list_users(limit=1000)
        user_option = [
            {"value": u.get("id", ""), "text": u.get("name") or u.get("username", "")}
            for u in users
        ]
        if not user_option:
            user_option = [{"value": "admin", "text": "admin"}]
    except Exception:
        user_option = [{"value": "admin", "text": "admin"}]
    return ok({"userOption": user_option})

@router.get("/project/custom/func/detail/{func_id}")
def project_custom_func_detail_path(func_id: str):
    """获取公共脚本详情（带路径参数）。"""
    item = project_service.get_custom_func(func_id)
    return ok(item if item else {})

@router.get("/project/status/flow/setting/get/{scoped_id}/{scene}")
def project_status_flow_setting_get_path(scoped_id: str, scene: str):
    """获取项目状态流设置（带路径参数）。

    返回 WorkFlowType[]（新建/处理中/已完成等状态列表），
    供模板工作流表格展示状态行与列。
    """
    items = workflow_service.list_statuses("PROJECT", scoped_id, scene)
    if not items:
        items = workflow_service.seed_default_statuses("PROJECT", scoped_id, scene)
    return ok(items)

@router.get("/project/template/enable/config/{scoped_id}")
def project_template_enable_config_path(scoped_id: str):
    """获取项目模板启用配置（带路径参数）。"""
    return ok(_default_template_status())

@router.get("/project/custom/field/delete/{id}")
@router.post("/project/custom/field/delete/{id}")
def project_custom_field_delete_path(id: str):
    """/project/custom/field/delete 带路径参数（前端 RESTful 调用兼容）。

    前端调用: /project/custom/field/delete/{id}，从数据库删除自定义字段。
    """
    deleted = project_service.delete_custom_field(id)
    return ok({"id": id, "deleted": deleted})

@router.get("/project/custom/field/get/{id}")
@router.post("/project/custom/field/get/{id}")
def project_custom_field_get_path(id: str):
    """/project/custom/field/get 带路径参数（前端 RESTful 调用兼容）。

    前端调用: /project/custom/field/get/{id}，返回字段详情对象。
    """
    field = project_service.get_custom_field(id)
    return ok(field if field is not None else {})

@router.get("/project/status/flow/setting/status/delete/{id}")
@router.post("/project/status/flow/setting/status/delete/{id}")
def project_status_flow_setting_status_delete_path(id: str):
    """/project/status/flow/setting/status/delete 带路径参数（前端 RESTful 调用兼容）。"""
    workflow_service.delete_status(id)
    return ok({"id": id, "deleted": True})
