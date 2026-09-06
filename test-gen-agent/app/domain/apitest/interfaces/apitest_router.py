# app/routers/apitest.py
"""接口测试路由（Phase 3 重构：从 main.py 拆分）。"""
import asyncio
import json

from fastapi import APIRouter, Request

from app.apitest.store.payload_guard import normalize_payload
from app.core.response import fail, ok, read_body
from app.models.apitest import (
    ApiCaseCreate,
    ApiCaseUpdate,
    ApiDebugRequest,
    ApiDefinitionCreate,
    ApiDefinitionRollback,
    ApiDefinitionUpdate,
    ApiDefinitionVersionCreate,
    ApiEnvironmentCreate,
    ApiEnvironmentUpdate,
    BatchIdsBody,
    BatchUpdateBody,
    ImportApiRequest,
    MockCreate,
    MockUpdate,
    ModuleAddBody,
    ModuleDeleteBody,
    ModuleMoveBody,
    ModuleUpdateBody,
    RunBody,
    ScenarioCreate,
    ScenarioRunRequest,
    ScenarioUpdate,
)
from app.domain.apitest.application.apitest_app_service import apitest_service

router = APIRouter(tags=["apitest"])


def _payload(body, strip_generated=True) -> dict:
    """把类型化 Pydantic 请求体导出为 store 层可消费的字典。

    等价于旧实现 read_body()/read_writable_body()：
      - 仅保留客户端实际发送的字段（exclude_unset），避免把模型默认值灌入 store
      - strip_generated=True 时剔除服务端自增字段 id/ids（写操作收口）
    """
    data = dict(body.model_dump(exclude_unset=True))
    if strip_generated:
        data.pop("id", None)
        data.pop("ids", None)
    return data


@router.get("/api/apitest/stats")
def api_apitest_stats():
    """接口测试统计。"""
    return ok(apitest_service.dashboard_stats())


# ── 接口定义管理 ──────────────────────────────────────────

@router.get("/api/apitest/definitions")
def api_list_definitions(keyword: str = "", limit: int = 100, offset: int = 0,
                               project_id: str = "", include_all_versions: bool = False):
    items = apitest_service.list_definitions(keyword, limit, offset, project_id=project_id,
                                   include_latest_only=not include_all_versions)
    return ok({"items": items, "total": apitest_service.count_definitions(project_id)})


@router.post("/api/apitest/definitions")
async def api_create_definition(body: ApiDefinitionCreate):
    payload = _payload(body)
    if "name" not in payload or not payload["name"]:
        payload["name"] = "未命名接口定义"
    item = apitest_service.create_definition(
        **normalize_payload("definition", payload))
    return ok(item)


@router.get("/api/apitest/definitions/{definition_id}")
def api_get_definition(definition_id: str):
    item = apitest_service.get_definition(definition_id)
    if not item or item.get("deleted"):
        return fail("接口定义不存在", 404)
    return ok(item)


@router.put("/api/apitest/definitions/{definition_id}")
async def api_update_definition(definition_id: str, body: ApiDefinitionUpdate):
    item = apitest_service.update_definition(
        definition_id, **normalize_payload("definition", _payload(body)))
    if not item:
        return fail("接口定义不存在", 404)
    return ok(item)


@router.delete("/api/apitest/definitions/{definition_id}")
def api_delete_definition(definition_id: str):
    result = apitest_service.delete_definition(definition_id)
    return ok({"success": result})


# ── 接口定义版本管理 ───────────────────────────────────────

@router.get("/api/apitest/definitions/{definition_id}/versions")
def api_list_definition_versions(definition_id: str):
    """列出接口定义的所有版本。"""
    item = apitest_service.get_definition(definition_id)
    if not item:
        return fail("接口定义不存在", 404)
    ref_id = item.get("ref_id") or definition_id
    versions = apitest_service.list_definition_versions(ref_id)
    return ok({"items": versions})


@router.post("/api/apitest/definitions/{definition_id}/versions")
async def api_create_definition_version(
        definition_id: str,
        body: ApiDefinitionVersionCreate = ApiDefinitionVersionCreate()):
    """为接口定义创建新版本。"""
    version = body.version
    item = apitest_service.create_definition_version(definition_id, version)
    if not item:
        return fail("接口定义不存在", 404)
    return ok(item)


@router.post("/api/apitest/definitions/{definition_id}/rollback")
async def api_rollback_definition(
        definition_id: str,
        body: ApiDefinitionRollback = ApiDefinitionRollback()):
    """回滚接口定义到指定版本。"""
    version_id = body.version_id
    if not version_id:
        return fail("缺少 version_id 参数", 400)
    item = apitest_service.rollback_definition(definition_id, version_id)
    if not item:
        return fail("回滚失败，版本或接口不存在", 404)
    return ok(item)


# ── 接口用例管理 ──────────────────────────────────────────

@router.get("/api/apitest/cases")
def api_list_api_cases(keyword: str = "", limit: int = 100, offset: int = 0,
                             project_id: str = ""):
    items = apitest_service.list_api_cases(keyword, limit, offset, project_id=project_id)
    return ok({"items": items, "total": apitest_service.count_api_cases(project_id)})


@router.post("/api/apitest/cases")
async def api_create_api_case(body: ApiCaseCreate):
    payload = _payload(body)
    if "name" not in payload or not payload["name"]:
        payload["name"] = "未命名接口用例"
    # 将 method/path 等请求元信息合并到 request 字段中
    # create_api_case 不接受 method/path 等顶层参数，需要把它们放入 request dict
    req_meta = {}
    for k in ("method", "path", "protocol", "headers", "query", "body_type", "body"):
        if k in payload:
            req_meta[k] = payload.pop(k)
    if req_meta:
        # 合并已有 request 字段
        existing_request = payload.get("request") or {}
        if isinstance(existing_request, str):
            try:
                existing_request = json.loads(existing_request)
            except (json.JSONDecodeError, TypeError):
                existing_request = {}
        if isinstance(existing_request, dict):
            existing_request.update(req_meta)
        else:
            existing_request = req_meta
        payload["request"] = existing_request
    item = apitest_service.create_api_case(
        **normalize_payload("api_case", payload))
    return ok(item)


@router.get("/api/apitest/cases/{case_id}")
def api_get_api_case(case_id: str):
    item = apitest_service.get_api_case(case_id)
    if not item or item.get("deleted"):
        return fail("接口用例不存在", 404)
    return ok(item)


@router.put("/api/apitest/cases/{case_id}")
async def api_update_api_case(case_id: str, body: ApiCaseUpdate):
    item = apitest_service.update_api_case(
        case_id, **normalize_payload("api_case", _payload(body)))
    if not item:
        return fail("接口用例不存在", 404)
    return ok(item)


@router.delete("/api/apitest/cases/{case_id}")
def api_delete_api_case(case_id: str):
    result = apitest_service.delete_api_case(case_id)
    return ok({"success": result})


@router.post("/api/apitest/cases/{case_id}/run")
def api_run_api_case(case_id: str, req: RunBody = RunBody()):
    env_id = req.environment_id or req.environmentId
    result = apitest_service.run_case(case_id, env_id)
    return ok(result)


# ── 接口场景编排 ──────────────────────────────────────────

@router.get("/api/apitest/scenarios")
def api_list_scenarios(keyword: str = "", limit: int = 100, offset: int = 0,
                             project_id: str = ""):
    items = apitest_service.list_scenarios(keyword, limit, offset, project_id=project_id)
    return ok({"items": items, "total": apitest_service.count_scenarios(project_id)})


@router.post("/api/apitest/scenarios")
async def api_create_scenario(body: ScenarioCreate):
    payload = _payload(body)
    if "name" not in payload or not payload["name"]:
        payload["name"] = "未命名接口场景"
    item = apitest_service.create_scenario(
        **normalize_payload("scenario", payload))
    return ok(item)


@router.get("/api/apitest/scenarios/{scenario_id}")
def api_get_scenario(scenario_id: str):
    item = apitest_service.get_scenario(scenario_id)
    if not item or item.get("deleted"):
        return fail("接口场景不存在", 404)
    return ok(item)


@router.put("/api/apitest/scenarios/{scenario_id}")
async def api_update_scenario(scenario_id: str, body: ScenarioUpdate):
    item = apitest_service.update_scenario(
        scenario_id, **normalize_payload("scenario", _payload(body)))
    if not item:
        return fail("接口场景不存在", 404)
    return ok(item)


@router.delete("/api/apitest/scenarios/{scenario_id}")
def api_delete_scenario(scenario_id: str):
    result = apitest_service.delete_scenario(scenario_id)
    return ok({"success": result})


@router.post("/api/apitest/scenarios/{scenario_id}/run")
def api_run_scenario(scenario_id: str, req: ScenarioRunRequest = None):
    sc = apitest_service.get_scenario(scenario_id)
    if not sc:
        return fail("接口场景不存在", 404)
    env_id = req.environment_id if req else ""
    result = apitest_service.run_scenario(sc, environment_id=env_id)
    return ok(result)


# ── Mock 服务 ─────────────────────────────────────────────

@router.get("/api/apitest/mocks")
def api_list_mocks(keyword: str = "", limit: int = 100, offset: int = 0,
                         project_id: str = ""):
    items = apitest_service.list_mocks(keyword, limit, offset, project_id=project_id)
    return ok({"items": items, "total": apitest_service.count_mocks(project_id)})


@router.post("/api/apitest/mocks")
async def api_create_mock(body: MockCreate):
    payload = _payload(body)
    if "name" not in payload or not payload["name"]:
        payload["name"] = "未命名Mock服务"
    item = apitest_service.create_mock(**normalize_payload("mock", payload))
    return ok(item)


@router.get("/api/apitest/mocks/{mock_id}")
def api_get_mock(mock_id: str):
    """获取 Mock 详情。"""
    item = apitest_service.get_mock(mock_id)
    if not item or item.get("deleted"):
        return fail("Mock 不存在", 404)
    return ok(item)


@router.put("/api/apitest/mocks/{mock_id}")
async def api_update_mock(mock_id: str, body: MockUpdate):
    item = apitest_service.update_mock(
        mock_id, **normalize_payload("mock", _payload(body)))
    if not item:
        return fail("Mock 不存在", 404)
    return ok(item)


@router.delete("/api/apitest/mocks/{mock_id}")
def api_delete_mock(mock_id: str):
    result = apitest_service.delete_mock(mock_id)
    return ok({"success": result})


# ── 环境管理 ─────────────────────────────────────────────

@router.get("/api/apitest/environments")
def api_list_environments(project_id: str = ""):
    items = apitest_service.list_environments(project_id=project_id)
    return ok({"items": items, "total": apitest_service.count_environments(project_id=project_id)})


@router.post("/api/apitest/environments")
async def api_create_environment(body: ApiEnvironmentCreate):
    payload = _payload(body)
    if "name" not in payload or not payload["name"]:
        payload["name"] = "未命名环境"
    # 收口未知字段（如前端多传的 current/pageSize），避免 store 层
    # 抛 TypeError 打成 500
    item = apitest_service.create_environment(
        **normalize_payload("environment", payload))
    return ok(item)


@router.get("/api/apitest/environments/{env_id}")
def api_get_environment(env_id: str):
    """获取环境详情。"""
    item = apitest_service.get_environment(env_id)
    if not item or item.get("deleted"):
        return fail("环境不存在", 404)
    return ok(item)


@router.put("/api/apitest/environments/{env_id}")
async def api_update_environment(env_id: str, body: ApiEnvironmentUpdate):
    # 收口未知字段，避免 unknown column 打成 500
    item = apitest_service.update_environment(
        env_id, **normalize_payload("environment", _payload(body)))
    if not item:
        return fail("环境不存在", 404)
    return ok(item)


@router.delete("/api/apitest/environments/{env_id}")
def api_delete_environment(env_id: str):
    result = apitest_service.delete_environment(env_id)
    return ok({"success": result})


@router.get("/api/apitest/environments/{env_id}/export")
def api_export_environment(env_id: str):
    """导出环境配置。"""
    data = apitest_service.export_environment(env_id)
    if not data:
        return fail("环境不存在", 404)
    return ok(data)


@router.post("/api/apitest/environments/import")
async def api_import_environment(req: Request):
    """导入环境配置。"""
    body = await read_body(req)
    if not isinstance(body, dict):
        body = {}
    # 项目维度：优先取显式 project_id，其次取前端驼峰 projectId，最后
    # 回退到待导入数据自身携带的 data.project_id。
    project_id = body.get("project_id") or body.get("projectId") or ""
    if not project_id and isinstance(body.get("data"), dict):
        project_id = body["data"].get("project_id", "")
    # store 期望的是待导入的环境对象本身；若请求把环境包在 data 信封里
    # （前端与 /api/environments/import 都这么做），需先解包。
    data = dict(body["data"]) if isinstance(body.get("data"), dict) else dict(body)
    if project_id and "project_id" not in data:
        data["project_id"] = project_id
    item = apitest_service.import_environment(data, project_id=project_id)
    if not item:
        return fail("导入失败，请检查数据格式", 400)
    return ok(item)


# ── 接口导入与调试 ────────────────────────────────────────

@router.post("/api/apitest/import")
async def api_import_api(req: ImportApiRequest):
    content = req.content or ""
    fmt = req.format or "auto"
    project_id = req.project_id or ""
    result = await asyncio.to_thread(apitest_service.import_content, content, fmt)
    if project_id and result.get("imported", 0) > 0:
        # 更新导入的接口定义的 project_id
        for def_item in apitest_service.list_definitions(limit=100):
            if "project_id" in def_item and not def_item.get("project_id"):
                apitest_service.update_definition(def_item["id"], project_id=project_id)
    return ok(result)


@router.post("/api/apitest/debug")
async def api_debug(req: ApiDebugRequest):
    result = await asyncio.to_thread(
        apitest_service.debug_api_call,
        method=req.method,
        url=req.url,
        headers=req.headers,
        params=req.params,
        body=req.body,
        body_type=req.body_type,
        timeout=req.timeout,
    )
    return ok(result)


@router.get("/api/apitest/meta")
def api_apitest_meta():
    return ok({
        "assert_types": list(apitest_service.get_assert_types().items()),
        "protocols": ["HTTP", "TCP", "SQL", "DUBBO"],
        "script_languages": ["python", "groovy", "beanshell"],
        "logic_controllers": ["loop", "condition", "wait", "transaction"],
        "import_formats": ["auto", "postman", "swagger"],
    })

# ── 文件导入（multipart 支持）─────────────────────────────
@router.post("/api/apitest/import/file")
async def api_import_api_file(request: Request):
    """从文件导入接口定义（支持 multipart/form-data 文件上传）。"""
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" not in content_type:
        return fail("请使用 multipart/form-data 格式上传文件", 400)

    form = await request.form()
    file = form.get("file")
    fmt = form.get("format", "auto")
    project_id = form.get("project_id", "")

    if not file or not hasattr(file, "filename"):
        return fail("未找到文件", 400)

    filename = file.filename or ""
    content_bytes = await file.read()
    try:
        content = content_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        return fail(f"文件内容解码失败: {e}", 400)

    # 根据文件扩展名自动推断格式
    if fmt == "auto" and filename:
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext in ("yaml", "yml"):
            # YAML 格式尝试转 JSON
            try:
                import yaml
                data = yaml.safe_load(content)
                content = json.dumps(data, ensure_ascii=False)
            except ImportError:
                pass
            except Exception:
                pass
        elif ext == "har":
            fmt = "har"
        elif ext == "json":
            pass  # 自动识别

    result = await asyncio.to_thread(apitest_service.import_content, content, fmt, project_id)
    return ok(result)

# ════════════════════════════════════════════════════════════
# 模块管理
# ════════════════════════════════════════════════════════════

@router.get("/api/apitest/modules/{scope}")
def api_list_modules(scope: str, project_id: str = ""):
    """列出模块树。scope: definition/case/scenario"""
    tree = apitest_service.build_module_tree(scope)
    return ok({"modules": tree})


@router.post("/api/apitest/modules/{scope}/add")
async def api_add_module(scope: str, body: ModuleAddBody = ModuleAddBody()):
    """新增模块。"""
    item = apitest_service.add_module(
        scope=scope,
        name=body.name,
        parent_id=body.parent_id or "root",
        project_id=body.project_id,
    )
    return ok(item)


@router.post("/api/apitest/modules/{scope}/update")
async def api_update_module(scope: str, body: ModuleUpdateBody = ModuleUpdateBody()):
    """更新模块。"""
    mod_id = body.id
    name = body.name
    if not mod_id or not name:
        return fail("缺少 id 或 name", 400)
    updated = apitest_service.update_module(mod_id, name)
    return ok({"success": updated})


@router.post("/api/apitest/modules/{scope}/delete")
async def api_delete_module(scope: str, body: ModuleDeleteBody = ModuleDeleteBody()):
    """删除模块。"""
    mod_id = body.id
    if not mod_id:
        return fail("缺少 id", 400)
    deleted = apitest_service.delete_module(mod_id)
    return ok({"success": deleted})


@router.post("/api/apitest/modules/{scope}/move")
async def api_move_module(scope: str, body: ModuleMoveBody = ModuleMoveBody()):
    """移动模块。"""
    mod_id = body.id
    new_parent = body.parent_id or body.parentId or ""
    if not mod_id:
        return fail("缺少 id", 400)
    item = apitest_service.get_module(mod_id)
    if not item:
        return fail("模块不存在", 404)
    # Use move_module to change parent
    # drop_position=0 表示放入 drop 节点作为子节点
    updated = apitest_service.move_module(mod_id, new_parent or "root", 0)
    return ok({"success": updated})


@router.get("/api/apitest/modules/{scope}/count")
def api_count_modules(scope: str, project_id: str = ""):
    """模块计数。"""
    return ok({"count": apitest_service.count_modules(scope)})


# ════════════════════════════════════════════════════════════
# 批量操作
# ════════════════════════════════════════════════════════════

@router.post("/api/apitest/batch/definitions/delete")
async def api_batch_delete_definitions(req: Request):
    """批量软删除接口定义。"""
    ids = BatchIdsBody.model_validate(await read_body(req)).ids
    count = apitest_service.batch_delete_definitions(ids)
    return ok({"success": True, "deleted": count})


@router.post("/api/apitest/batch/cases/delete")
async def api_batch_delete_cases(req: Request):
    """批量软删除接口用例。"""
    ids = BatchIdsBody.model_validate(await read_body(req)).ids
    count = apitest_service.batch_delete_cases(ids)
    return ok({"success": True, "deleted": count})


@router.post("/api/apitest/batch/scenarios/delete")
async def api_batch_delete_scenarios(req: Request):
    """批量软删除接口场景。"""
    ids = BatchIdsBody.model_validate(await read_body(req)).ids
    count = apitest_service.batch_delete_scenarios(ids)
    return ok({"success": True, "deleted": count})


@router.post("/api/apitest/batch/mocks/delete")
async def api_batch_delete_mocks(req: Request):
    """批量软删除 Mock。"""
    ids = BatchIdsBody.model_validate(await read_body(req)).ids
    count = apitest_service.batch_delete_mocks(ids)
    return ok({"success": True, "deleted": count})


@router.post("/api/apitest/batch/definitions/purge")
async def api_batch_purge_definitions(req: Request):
    """批量彻底删除接口定义。"""
    ids = BatchIdsBody.model_validate(await read_body(req)).ids
    count = apitest_service.batch_purge_definitions(ids)
    return ok({"success": True, "purged": count})


@router.post("/api/apitest/batch/cases/purge")
async def api_batch_purge_cases(req: Request):
    """批量彻底删除接口用例。"""
    ids = BatchIdsBody.model_validate(await read_body(req)).ids
    count = apitest_service.batch_purge_cases(ids)
    return ok({"success": True, "purged": count})


@router.post("/api/apitest/batch/scenarios/purge")
async def api_batch_purge_scenarios(req: Request):
    """批量彻底删除接口场景。"""
    ids = BatchIdsBody.model_validate(await read_body(req)).ids
    count = apitest_service.batch_purge_scenarios(ids)
    return ok({"success": True, "purged": count})


@router.post("/api/apitest/batch/mocks/purge")
async def api_batch_purge_mocks(req: Request):
    """批量彻底删除 Mock。"""
    ids = BatchIdsBody.model_validate(await read_body(req)).ids
    count = apitest_service.batch_purge_mocks(ids)
    return ok({"success": True, "purged": count})


@router.post("/api/apitest/batch/definitions/update")
async def api_batch_update_definitions(req: Request):
    """批量更新接口定义。"""
    body = BatchUpdateBody.model_validate(await read_body(req))
    count = apitest_service.batch_update_definitions(body.ids, **{
        k: v for k, v in body.model_dump(exclude_unset=True).items()
        if k != "ids"
    })
    return ok({"success": True, "updated": count})


@router.post("/api/apitest/batch/cases/update")
async def api_batch_update_cases(req: Request):
    """批量更新接口用例。"""
    body = BatchUpdateBody.model_validate(await read_body(req))
    count = apitest_service.batch_update_cases(body.ids, **{
        k: v for k, v in body.model_dump(exclude_unset=True).items()
        if k != "ids"
    })
    return ok({"success": True, "updated": count})


@router.post("/api/apitest/batch/scenarios/update")
async def api_batch_update_scenarios(req: Request):
    """批量更新接口场景。"""
    body = BatchUpdateBody.model_validate(await read_body(req))
    count = apitest_service.batch_update_scenarios(body.ids, **{
        k: v for k, v in body.model_dump(exclude_unset=True).items()
        if k != "ids"
    })
    return ok({"success": True, "updated": count})


@router.post("/api/apitest/batch/definitions/recover")
async def api_batch_recover_definitions(req: Request):
    """批量从回收站恢复接口定义。"""
    ids = BatchIdsBody.model_validate(await read_body(req)).ids
    count = apitest_service.batch_restore_definitions(ids)
    return ok({"success": True, "restored": count})


@router.post("/api/apitest/batch/cases/recover")
async def api_batch_recover_cases(req: Request):
    """批量从回收站恢复接口用例。"""
    ids = BatchIdsBody.model_validate(await read_body(req)).ids
    count = apitest_service.batch_restore_cases(ids)
    return ok({"success": True, "restored": count})


@router.post("/api/apitest/batch/scenarios/recover")
async def api_batch_recover_scenarios(req: Request):
    """批量从回收站恢复接口场景。"""
    ids = BatchIdsBody.model_validate(await read_body(req)).ids
    count = apitest_service.batch_restore_scenarios(ids)
    return ok({"success": True, "restored": count})


@router.post("/api/apitest/batch/mocks/recover")
async def api_batch_recover_mocks(req: Request):
    """批量从回收站恢复 Mock。"""
    ids = BatchIdsBody.model_validate(await read_body(req)).ids
    count = apitest_service.batch_restore_mocks(ids)
    return ok({"success": True, "restored": count})


# ════════════════════════════════════════════════════════════
# 关注/取消关注
# ════════════════════════════════════════════════════════════

@router.post("/api/apitest/definitions/{definition_id}/follow")
def api_follow_definition(definition_id: str):
    """关注接口定义。"""
    result = apitest_service.follow_resource("definition", definition_id)
    return ok({"success": result})


@router.post("/api/apitest/definitions/{definition_id}/unfollow")
def api_unfollow_definition(definition_id: str):
    """取消关注接口定义。"""
    result = apitest_service.unfollow_resource("definition", definition_id)
    return ok({"success": result})


@router.get("/api/apitest/definitions/{definition_id}/followers")
def api_list_definition_followers(definition_id: str):
    """接口定义关注者。"""
    followers = apitest_service.list_followers("definition", definition_id)
    return ok({"followers": followers})


@router.post("/api/apitest/cases/{case_id}/follow")
def api_follow_case(case_id: str):
    """关注接口用例。"""
    result = apitest_service.follow_resource("case", case_id)
    return ok({"success": result})


@router.post("/api/apitest/cases/{case_id}/unfollow")
def api_unfollow_case(case_id: str):
    """取消关注接口用例。"""
    result = apitest_service.unfollow_resource("case", case_id)
    return ok({"success": result})


@router.get("/api/apitest/cases/{case_id}/followers")
def api_list_case_followers(case_id: str):
    """接口用例关注者。"""
    followers = apitest_service.list_followers("case", case_id)
    return ok({"followers": followers})


@router.post("/api/apitest/scenarios/{scenario_id}/follow")
def api_follow_scenario(scenario_id: str):
    """关注接口场景。"""
    result = apitest_service.follow_resource("scenario", scenario_id)
    return ok({"success": result})


@router.post("/api/apitest/scenarios/{scenario_id}/unfollow")
def api_unfollow_scenario(scenario_id: str):
    """取消关注接口场景。"""
    result = apitest_service.unfollow_resource("scenario", scenario_id)
    return ok({"success": result})


@router.get("/api/apitest/scenarios/{scenario_id}/followers")
def api_list_scenario_followers(scenario_id: str):
    """接口场景关注者。"""
    followers = apitest_service.list_followers("scenario", scenario_id)
    return ok({"followers": followers})


# ════════════════════════════════════════════════════════════
# 操作历史分页
# ════════════════════════════════════════════════════════════

@router.get("/api/apitest/operation-history")
def api_operation_history(resource_type: str = "", resource_id: str = "",
                                 project_id: str = "", page: int = 1, page_size: int = 10):
    """操作历史分页。"""
    offset = (page - 1) * page_size
    items = apitest_service.list_operation_logs(
        resource_type, resource_id, project_id, limit=page_size, offset=offset,
    )
    total = apitest_service.count_operation_logs(
        resource_type=resource_type, resource_id=resource_id, project_id=project_id,
    )
    return ok({
        "list": items,
        "total": total,
        "current": page,
        "pageSize": page_size,
    })


# ════════════════════════════════════════════════════════════
# 测试执行记录（测试数据落库查询，便于调试与测试）
# ════════════════════════════════════════════════════════════

@router.get("/api/apitest/execution-logs")
def api_list_execution_logs(exec_type: str = "", target_id: str = "", limit: int = 100):
    """查询测试执行记录（用例/场景运行落库数据）。"""
    items = apitest_service.list_execution_logs(exec_type, target_id, limit)
    return ok({
        "items": items,
        "total": len(items),
    })


@router.delete("/api/apitest/execution-logs")
def api_clear_execution_logs(exec_type: str = ""):
    """清空测试执行记录。"""
    return ok({"deleted": apitest_service.clear_execution_logs(exec_type)})


# ════════════════════════════════════════════════════════════
# 转存选项
# ════════════════════════════════════════════════════════════

@router.get("/api/apitest/transfer/options")
def api_transfer_options(project_id: str = ""):
    """转存选项（模块/项目列表）。"""
    return ok({
        "projects": [],
        "modules": [],
    })
