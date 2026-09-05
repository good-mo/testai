# app/routers/project_compat_environment.py
"""project_compat 拆分：项目环境管理 /project/environment/*（P4 超大文件拆分）。

自 app/routers/project_compat.py 按业务域搬移，纯路由搬移、行为不变，
响应沿用统一 ok()/fail()/_paginate() 与 read_body() 辅助函数。
"""

import json
import time
import uuid

from fastapi import APIRouter, Body, Request

from app.core.response import fail, ok, read_body, read_form_or_json
from app.logging_config import get_logger
from app.models.environment import (
    ProjDbValidateBody,
    ProjEnvExportBody,
    ProjEnvGroupBody,
    ProjEnvIdBody,
    ProjEnvMoveBody,
    ProjEnvQueryBody,
    ProjEnvUpsertBody,
)
from app.services.apitest_service import apitest_service as _apitest_svc
from app.services.project_service import project_service

logger = get_logger(__name__)
router = APIRouter(tags=["adapter-project-environment"])


"""project_compat 拆分：environment 域路由（P4 超大文件拆分）。

自 app/routers/project_compat.py 按域搬移，纯搬移、行为不变。
"""


@router.get("/project/environment/get")
def project_environment_get(id: str = ""):
    """获取项目环境。"""
    env = _apitest_svc.get_environment(id) if id else None
    return ok(env or {})

@router.get("/project/environment/get/")
def project_environment_get_trailing(id: str = ""):
    """获取项目环境（尾斜杠）。"""
    env = _apitest_svc.get_environment(id) if id else None
    return ok(env or {})

@router.get("/project/environment/get/entry")
@router.post("/project/environment/get/entry", operation_id="project_environment_get_entry_post")
async def project_environment_get_entry(request: Request, id: str = "",
                                        body: ProjEnvIdBody = Body(default=None)):
    """获取项目环境入口。"""
    if request.method == "POST" and body is not None:
        id = body.id or id
    env = _apitest_svc.get_environment(id) if id else None
    if env:
        return ok(_apitest_svc.env_detail_to_frontend(env))
    return ok({})

@router.post("/project/environment/delete")
def project_environment_delete():
    """删除项目环境。"""
    return ok()

@router.delete("/project/environment/delete/")
def project_environment_delete_del(id: str = ""):
    """删除项目环境 DELETE。"""
    return ok()

@router.post("/project/environment/edit/pos")
def project_environment_edit_pos(body: ProjEnvMoveBody):
    """环境拖拽排序。"""
    if body.moveId:
        _apitest_svc.update_environment(body.moveId, updated_at=time.time())
    return ok()

@router.get("/project/environment/export")
def project_environment_export(project_id: str = ""):
    """导出环境。"""
    return ok({"fileName": "environment.json", "content": "{}"})

@router.get("/project/environment/database/driver-options/")
def project_environment_database_driver_options(project_id: str = ""):
    """数据库驱动选项。"""
    drivers = [
        {"id": "system&com.mysql.cj.jdbc.Driver", "name": "MySQL"},
        {"id": "system&oracle.jdbc.OracleDriver", "name": "Oracle"},
        {"id": "system&org.postgresql.Driver", "name": "PostgreSQL"},
        {"id": "system&com.microsoft.sqlserver.jdbc.SQLServerDriver", "name": "SQL Server"},
        {"id": "system&org.h2.Driver", "name": "H2"},
        {"id": "system&org.sqlite.JDBC", "name": "SQLite"},
    ]
    return ok(drivers)

@router.post("/project/environment/database/validate")
def project_environment_database_validate(body: ProjDbValidateBody):
    """数据库连接校验。"""
    # 基本校验：检查必需字段
    if not body.dbUrl or not body.username:
        return fail("数据库连接信息不完整", 400)
    return ok({"success": True, "message": "连接成功"})

@router.get("/project/environment/group/list")
@router.post("/project/environment/group/list", operation_id="project_environment_group_list_post")
async def project_environment_group_list(request: Request, project_id: str = "",
                                         body: ProjEnvQueryBody = Body(default=None)):
    """环境组列表。"""
    if request.method == "POST" and body is not None:
        project_id = body.effective_project_id or project_id
        keyword = body.keyword
    else:
        keyword = ""
    groups = _apitest_svc.list_env_groups(project_id=project_id, keyword=keyword)
    items = []
    for g in groups:
        items.append({
            "id": g.get("id", ""),
            "name": g.get("name", ""),
            "description": g.get("description", ""),
            "projectId": g.get("project_id", ""),
            "mock": False,
            "pos": g.get("pos", 0),
        })
    return ok(items)

@router.post("/project/environment/group/add")
def project_environment_group_add(body: ProjEnvGroupBody):
    """添加环境组。"""
    env_group_project = body.effective_env_group_project
    group = _apitest_svc.create_env_group(
        name=body.name,
        description=body.description,
        project_id=body.effective_project_id,
        env_group_project=env_group_project,
    )
    if group:
        return ok({
            "id": group.get("id", ""),
            "name": group.get("name", ""),
            "description": group.get("description", ""),
            "projectId": group.get("project_id", ""),
            "mock": False,
            "environmentGroupInfo": group.get("env_group_project", []),
        })
    return ok({"id": str(uuid.uuid4())})

@router.post("/project/environment/group/update")
def project_environment_group_update(body: ProjEnvGroupBody):
    """更新环境组。"""
    group_id = body.id
    if not group_id:
        # 没有 id，视为新增（与 group/add 兼容，仅认 envGroupProject 字段）
        env_group_project = body.envGroupProject or []
        group = _apitest_svc.create_env_group(
            name=body.name,
            description=body.description,
            project_id=body.effective_project_id,
            env_group_project=env_group_project,
        )
        if group:
            return ok({
                "id": group.get("id", ""),
                "name": group.get("name", ""),
                "description": group.get("description", ""),
                "projectId": group.get("project_id", ""),
                "mock": False,
                "environmentGroupInfo": group.get("env_group_project", []),
            })
        return ok({"id": ""})

    updates = {}
    present = body.model_dump(exclude_unset=True)
    for k in ("name", "description"):
        if k in present:
            updates[k] = present[k]
    if "project_id" in present:
        updates["project_id"] = present["project_id"]
    if "projectId" in present:
        updates["project_id"] = present["projectId"]
    if "envGroupProject" in present:
        updates["env_group_project"] = present["envGroupProject"]
    if "environmentGroupInfo" in present and not updates.get("env_group_project"):
        updates["env_group_project"] = present["environmentGroupInfo"]

    try:
        group = _apitest_svc.update_env_group(group_id, **updates)
    except Exception:
        group = None
    if not group:
        return fail("环境组不存在", 404)
    return ok({
        "id": group.get("id", ""),
        "name": group.get("name", ""),
        "description": group.get("description", ""),
        "projectId": group.get("project_id", ""),
        "mock": False,
        "environmentGroupInfo": group.get("env_group_project", []),
    })

@router.get("/project/environment/group/get")
def project_environment_group_get(id: str = ""):
    """获取环境组。"""
    return ok({})

@router.get("/project/environment/group/get/")
def project_environment_group_get_trailing(id: str = ""):
    """获取环境组（尾斜杠）。"""
    return ok({})

@router.post("/project/environment/group/delete/")
def project_environment_group_delete(id: str = "", body: ProjEnvIdBody = Body(default=None)):
    """删除环境组。"""
    if body is not None and body.id:
        id = body.id
    result = _apitest_svc.delete_env_group(id) if id else False
    return ok({"id": id, "deleted": result})

@router.post("/project/environment/group/edit/pos")
def project_environment_group_edit_pos(body: ProjEnvMoveBody):
    """环境组拖拽排序。"""
    if body.moveId:
        _apitest_svc.update_env_group(body.moveId, pos=int(time.time()))
    return ok()

@router.get("/project/environment/group/get-project/")
def project_environment_group_get_project(id: str = ""):
    """获取环境组项目。"""
    projects = project_service.list(limit=200)
    items = [{"id": p.get("id", ""), "name": p.get("name", "")} for p in projects]
    return ok(items)

@router.get("/project/environment/scripts/")
async def project_environment_scripts(request: Request, project_id: str = "",
                                      body: ProjEnvQueryBody = Body(default=None)):
    """环境脚本。"""
    if request.method == "POST" and body is not None:
        project_id = body.effective_project_id or project_id
    return ok([])

@router.get("/project/environment/group/delete/{group_id}")
def project_environment_group_delete_path(group_id: str):
    """删除环境组（带路径参数）。"""
    result = _apitest_svc.delete_env_group(group_id)
    return ok({"id": group_id, "deleted": result})

@router.get("/project/environment/group/get/{group_id}")
def project_environment_group_get_path(group_id: str):
    """获取环境组详情（带路径参数）。"""
    group = _apitest_svc.get_env_group(group_id)
    if not group:
        return fail("环境组不存在", 404)
    return ok({
        "id": group.get("id", ""),
        "name": group.get("name", ""),
        "description": group.get("description", ""),
        "projectId": group.get("project_id", ""),
        "envGroupProject": group.get("env_group_project", []),
        "environmentGroupInfo": group.get("env_group_project", []),
    })

@router.get("/project/environment/scripts/{project_id}")
def project_environment_scripts_path(project_id: str):
    """获取环境脚本（带路径参数）。"""
    return ok([])

@router.get("/project/environment/database/driver-options/{organization_id}")
def project_environment_driver_options_path(organization_id: str):
    """获取数据库驱动选项（带路径参数）。"""
    drivers = [
        {"id": "system&com.mysql.cj.jdbc.Driver", "name": "MySQL"},
        {"id": "system&oracle.jdbc.OracleDriver", "name": "Oracle"},
        {"id": "system&org.postgresql.Driver", "name": "PostgreSQL"},
        {"id": "system&com.microsoft.sqlserver.jdbc.SQLServerDriver", "name": "SQL Server"},
        {"id": "system&org.h2.Driver", "name": "H2"},
        {"id": "system&org.sqlite.JDBC", "name": "SQLite"},
    ]
    return ok(drivers)

@router.get("/project/environment/group/get-project/{organization_id}")
def project_environment_group_get_project_path(organization_id: str):
    """获取环境组项目（带路径参数）。"""
    projects = project_service.list(limit=200)
    items = [{"id": p.get("id", ""), "name": p.get("name", "")} for p in projects]
    return ok(items)

@router.post("/project/environment/list", operation_id="project_environment_list_post")
@router.get("/project/environment/list", operation_id="project_environment_list_get")
async def project_environment_list(request: Request,
                                   body: ProjEnvQueryBody = Body(default=None)):
    """获取项目环境列表。"""
    if request.method == "POST" and body is not None:
        project_id = body.effective_project_id
        keyword = body.keyword
    else:
        params = dict(request.query_params)
        project_id = params.get("projectId", "")
        keyword = params.get("keyword", "")
    envs = _apitest_svc.list_environments(project_id=project_id)
    items = []
    for e in envs:
        # 关键词过滤
        if keyword:
            if keyword.lower() not in (e.get("name", "") or "").lower() and                keyword.lower() not in (e.get("description", "") or "").lower():
                continue
        items.append(_apitest_svc.env_detail_to_frontend(e))
    return ok(items)

@router.post("/project/environment/add")
async def project_environment_add(request: Request):
    """新增项目环境。"""
    body = await read_form_or_json(request)
    m = ProjEnvUpsertBody.model_validate(body)
    config = m.config or {}
    http_config = config.get("httpConfig") or []
    base_url = ""
    if http_config:
        base_url = http_config[0].get("url", "") or http_config[0].get("hostname", "") or ""
    env = _apitest_svc.create_environment(
        name=m.name,
        base_url=base_url,
        headers={},
        variables={},
        project_id=m.projectId or m.project_id,
        description=m.description,
        config=config,
    )
    # 返回前端格式
    frontend_env = _apitest_svc.env_detail_to_frontend(env)
    return ok(frontend_env)

@router.post("/project/environment/update")
async def project_environment_update(request: Request):
    """更新项目环境。"""
    body = await read_form_or_json(request)
    m = ProjEnvUpsertBody.model_validate(body)
    env_id = m.id
    updates = {}
    present = m.model_dump(exclude_unset=True)
    for k in ("name", "description", "project_id"):
        if k in present:
            updates[k] = present[k]
    if "projectId" in present:
        updates["project_id"] = present["projectId"]
    if "config" in present:
        updates["config"] = present["config"]
    try:
        env = _apitest_svc.update_environment(env_id, **updates)
    except Exception:
        env = None
    if not env:
        return fail("环境不存在", code=404)
    # 返回前端格式
    frontend_env = _apitest_svc.env_detail_to_frontend(env)
    return ok(frontend_env)

@router.get("/project/environment/get/{env_id}")
def project_environment_get_path(env_id: str):
    """获取环境详情。"""
    env = _apitest_svc.get_environment(env_id)
    if not env:
        return fail("环境不存在", code=404)
    # 转换为前端期望的 EnvDetailItem 格式（含 config 结构）
    frontend_env = _apitest_svc.env_detail_to_frontend(env)
    return ok(frontend_env)

@router.post("/project/environment/delete/{env_id}", operation_id="project_environment_delete_post")
@router.get("/project/environment/delete/{env_id}", operation_id="project_environment_delete_get")
def project_environment_delete_path(env_id: str):
    """删除环境。"""
    _apitest_svc.delete_environment(env_id)
    return ok(None)

@router.post("/project/environment/import")
async def project_environment_import(request: Request):
    """导入环境。"""
    content_type = request.headers.get("content-type", "").lower()
    body = {}
    if "multipart/form-data" in content_type:
        form = await request.form()
        request_field = form.get("request")
        if request_field is not None:
            if hasattr(request_field, "read"):
                raw = await request_field.read()
                try:
                    body = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
                except (json.JSONDecodeError, TypeError):
                    body = {}
            else:
                try:
                    body = json.loads(request_field)
                except (json.JSONDecodeError, TypeError):
                    body = {}
    else:
        body = await read_body(request)
    data = body.get("request", body)
    if data.get("name"):
        env = _apitest_svc.import_environment(data, project_id=data.get("projectId", ""))
        if env:
            return ok(_apitest_svc.env_detail_to_frontend(env))
    return ok(None)

@router.post("/project/environment/export")
def project_environment_export_path(body: ProjEnvExportBody):
    """导出环境。"""
    select_ids = body.selectIds
    if select_ids:
        envs = []
        for eid in select_ids:
            env = _apitest_svc.export_environment(eid)
            if env:
                envs.append(env)
        return ok({"envs": envs})
    return ok({"envs": []})

@router.get("/project/environment/get-options")
def project_environment_get_options():
    """获取环境目录列表。"""
    envs = _apitest_svc.list_environments()
    return ok([
        {"id": e.get("id"), "name": e.get("name")} for e in envs
    ])

@router.get("/project/environment/get-options/{project_id}")
def project_environment_get_options_by_project(project_id: str):
    """获取项目环境目录列表。"""
    envs = _apitest_svc.list_environments(project_id=project_id)
    return ok([
        {"id": e.get("id"), "name": e.get("name")} for e in envs
    ])
