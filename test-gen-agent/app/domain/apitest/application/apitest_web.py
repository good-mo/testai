"""接口测试域 → Web 适配层（阶段 B/C 迁移桥接）。

背景
----
`app/domain/apitest/` 的 DDD 聚合与 `apitest_app_service` 门面已就绪（阶段 A），
但其应用层命令（dataclass）与 `app/routers/apitest.py` 直接消费 `ApitestService`
的薄包装签名并不一致。本模块把「既有 Web/Service 契约」翻译为「领域门面命令」，
并维持与旧路径完全一致的返回语义：

  - 查询/单查缺失 → 返回 None（不抛领域异常，保持 404 由 Web 层判定）
  - 删除/恢复时对象不存在或不在回收站 → 返回 False（保持旧 `{"success": false}`）
  - 创建/更新 → 返回聚合 to_dict（与仓库行字段对齐）
  - 列表 → 返回既有行 list（不含 total，total 由调用方独立获取）
  - 回收站计数 → 从 DDD list_trash total 提取（语义与旧 COUNT 对齐）

如此 router / compat 调用点无需改动即可获得 DDD 规则守护，实现双轨并存下的
渐进切换（阶段 B：Router→门面；阶段 C：Service 变薄）。
"""
from __future__ import annotations

from typing import Optional

from app.domain.apitest.application.apitest_app_service import apitest_app_service
from app.domain.apitest.application.dto import (
    CaseListQuery,
    CreateApiCaseCommand,
    CreateDefinitionCommand,
    CreateScenarioCommand,
    CreateVersionCommand,
    DefinitionListQuery,
    DeleteCaseCommand,
    DeleteDefinitionCommand,
    DeleteScenarioCommand,
    RestoreCaseCommand,
    RestoreDefinitionCommand,
    RestoreScenarioCommand,
    ScenarioListQuery,
    UpdateApiCaseCommand,
    UpdateDefinitionCommand,
    UpdateScenarioCommand,
)
from app.domain.common.exceptions import AggregateNotFound

_OPERATOR = "system"

_STRUCT_FIELDS = {
    "definition": {"headers", "query", "params", "tags"},
    "api_case": {"request", "asserts", "pre_scripts", "post_scripts",
                 "pre_sql", "post_sql", "variables", "logic_controllers", "tags"},
    "scenario": {"steps", "tags"},
    "mock": {"response_headers"},
}


def _unstruct(payload: dict, kind: str) -> dict:
    """把 normalize_payload 序列化过的 JSON 字符串字段还原为结构。

    领域聚合直接消费 dict/list；而 Web 层经 normalize_payload 会把
    dict/list 字段 JSON 序列化（仓库 TEXT 列存储）。此处还原，保证
    聚合构造/校验拿到真实结构。
    """
    import json
    out = dict(payload)
    for f in _STRUCT_FIELDS.get(kind, set()):
        v = out.get(f)
        if isinstance(v, str):
            try:
                out[f] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                out[f] = None
    return out


def _safe(fn, on_missing):
    """把领域缺失异常翻译回旧契约的默认值。"""
    try:
        return fn()
    except AggregateNotFound:
        return on_missing


# ── ApiDefinition ─────────────────────────────────────────
def create_definition(payload: dict) -> Optional[dict]:
    payload = _unstruct(payload, "definition")
    return apitest_app_service.create_definition(CreateDefinitionCommand(
        name=payload.get("name", "未命名接口定义"),
        protocol=payload.get("protocol", "HTTP"),
        method=payload.get("method", "GET"),
        path=payload.get("path", ""),
        headers=payload.get("headers"),
        body=payload.get("body", ""),
        query=payload.get("query"),
        params=payload.get("params"),
        description=payload.get("description", ""),
        tags=payload.get("tags") or [],
        module_id=payload.get("module_id", ""),
        project_id=payload.get("project_id", ""),
        version=payload.get("version", "v1"),
        operator=_OPERATOR,
    ))


def update_definition(definition_id: str, payload: dict) -> Optional[dict]:
    payload = _unstruct(payload, "definition")
    cmd = UpdateDefinitionCommand(
        definition_id=definition_id,
        name=payload.get("name"),
        protocol=payload.get("protocol"),
        method=payload.get("method"),
        path=payload.get("path"),
        headers=payload.get("headers"),
        body=payload.get("body"),
        query=payload.get("query"),
        params=payload.get("params"),
        description=payload.get("description"),
        tags=payload.get("tags"),
        module_id=payload.get("module_id"),
        operator=_OPERATOR,
    )
    # 仅传入 payload 中真实出现的字段，避免聚合无谓触发事件
    for f in ("name", "protocol", "method", "path", "headers", "body",
              "query", "params", "description", "tags", "module_id"):
        if f not in payload:
            setattr(cmd, f, None)
    return _safe(lambda: apitest_app_service.update_definition(cmd), None)


def delete_definition(definition_id: str) -> bool:
    return _safe(lambda: apitest_app_service.delete_definition(
        DeleteDefinitionCommand(definition_id=definition_id, operator=_OPERATOR)), False)


def restore_definition(definition_id: str) -> bool:
    return _safe(lambda: apitest_app_service.restore_definition(
        RestoreDefinitionCommand(definition_id=definition_id, operator=_OPERATOR)), False)


def list_definitions(keyword: str = "", limit: int = 100, offset: int = 0,
                     project_id: str = "", include_latest_only: bool = True,
                     protocols: Optional[list] = None,
                     module_ids: Optional[list] = None) -> list:
    """列表接口定义 → DDD 门面（行字段契约与旧仓库一致）。"""
    result = apitest_app_service.list_definitions(DefinitionListQuery(
        keyword=keyword, project_id=project_id, limit=limit, offset=offset,
        include_latest_only=include_latest_only,
        protocols=protocols, module_ids=module_ids,
    ))
    return result.get("list", [])


def count_definitions(project_id: str = "", **kwargs) -> int:
    """统计接口定义数 → DDD 门面 total（含过滤参数透传）。"""
    q = DefinitionListQuery(
        keyword=kwargs.get("keyword", ""), project_id=project_id,
        limit=1,  # 仅取 total，不拉行
        protocols=kwargs.get("protocols"),
        module_ids=kwargs.get("module_ids"),
    )
    # total 与 keyword 等过滤后的真实数对齐（经 DDD 仓库透传 ApitestRepo）
    result = apitest_app_service.list_definitions(q)
    return result.get("total", 0)


def list_definition_versions(ref_id: str) -> list:
    """接口定义版本列表 → DDD 门面。"""
    return apitest_app_service.list_definition_versions(ref_id)


def create_definition_version(definition_id: str,
                              version: str = "") -> Optional[dict]:
    """创建接口定义版本 → DDD 门面（缺失对象返回 None）。"""
    return _safe(lambda: apitest_app_service.create_definition_version(
        CreateVersionCommand(
            definition_id=definition_id, version=version,
            operator=_OPERATOR)), None)


def list_trash_definitions(project_id: str = "", limit: int = 100) -> list:
    """列出回收站中的接口定义 → DDD 门面。"""
    result = apitest_app_service.list_trash_definitions(
        project_id=project_id, limit=limit)
    return result.get("list", [])


def count_trash_definitions(project_id: str = "") -> int:
    """统计回收站中的接口定义数 → 从 DDD list_trash total 获取。"""
    result = apitest_app_service.list_trash_definitions(
        project_id=project_id, limit=1)
    return result.get("total", 0)


def batch_delete_definitions(ids: list) -> int:
    """批量软删接口定义 → 逐条经 DDD 门面删除。"""
    n = 0
    for did in ids or []:
        if delete_definition(did):
            n += 1
    return n


def batch_restore_definitions(ids: list) -> int:
    """批量恢复回收站中的接口定义 → 逐条经 DDD 门面恢复。"""
    n = 0
    for did in ids or []:
        if restore_definition(did):
            n += 1
    return n


# ── ApiCase ────────────────────────────────────────────────
def create_api_case(payload: dict) -> Optional[dict]:
    payload = _unstruct(payload, "api_case")
    return apitest_app_service.create_api_case(CreateApiCaseCommand(
        name=payload.get("name", "未命名接口用例"),
        api_definition_id=payload.get("api_definition_id", ""),
        request=payload.get("request"),
        asserts=payload.get("asserts"),
        pre_scripts=payload.get("pre_scripts"),
        post_scripts=payload.get("post_scripts"),
        pre_sql=payload.get("pre_sql"),
        post_sql=payload.get("post_sql"),
        variables=payload.get("variables"),
        logic_controllers=payload.get("logic_controllers"),
        environment_id=payload.get("environment_id", ""),
        priority=payload.get("priority", "P2"),
        description=payload.get("description", ""),
        project_id=payload.get("project_id", ""),
        operator=_OPERATOR,
    ))


def update_api_case(case_id: str, payload: dict) -> Optional[dict]:
    payload = _unstruct(payload, "api_case")
    cmd = UpdateApiCaseCommand(
        case_id=case_id,
        name=payload.get("name"),
        api_definition_id=payload.get("api_definition_id"),
        request=payload.get("request"),
        asserts=payload.get("asserts"),
        pre_scripts=payload.get("pre_scripts"),
        post_scripts=payload.get("post_scripts"),
        pre_sql=payload.get("pre_sql"),
        post_sql=payload.get("post_sql"),
        variables=payload.get("variables"),
        logic_controllers=payload.get("logic_controllers"),
        environment_id=payload.get("environment_id"),
        priority=payload.get("priority"),
        status=payload.get("status"),
        description=payload.get("description"),
        project_id=payload.get("project_id"),
        operator=_OPERATOR,
    )
    for f in ("name", "api_definition_id", "request", "asserts", "pre_scripts",
              "post_scripts", "pre_sql", "post_sql", "variables",
              "logic_controllers", "environment_id", "priority", "status",
              "description", "project_id"):
        if f not in payload:
            setattr(cmd, f, None)
    return _safe(lambda: apitest_app_service.update_api_case(cmd), None)


def delete_api_case(case_id: str) -> bool:
    return _safe(lambda: apitest_app_service.delete_api_case(
        DeleteCaseCommand(case_id=case_id, operator=_OPERATOR)), False)


def restore_api_case(case_id: str) -> bool:
    return _safe(lambda: apitest_app_service.restore_api_case(
        RestoreCaseCommand(case_id=case_id, operator=_OPERATOR)), False)


def list_api_cases(keyword: str = "", limit: int = 100,
                   offset: int = 0, project_id: str = "",
                   api_definition_id: str = "", **kwargs) -> list:
    """列表接口用例 → DDD 门面（含 api_definition_id 过滤透传）。"""
    result = apitest_app_service.list_api_cases(CaseListQuery(
        keyword=keyword, project_id=project_id,
        api_definition_id=api_definition_id,
        limit=limit, offset=offset,
    ))
    return result.get("list", [])


def count_api_cases(project_id: str = "", **kwargs) -> int:
    """统计接口用例数 → DDD 门面 total（含 api_definition_id/keyword 过滤）。"""
    q = CaseListQuery(
        keyword=kwargs.get("keyword", ""), project_id=project_id,
        api_definition_id=kwargs.get("api_definition_id", ""),
        limit=1,  # 仅取 total，不拉行
    )
    result = apitest_app_service.list_api_cases(q)
    return result.get("total", 0)


def list_trash_cases(project_id: str = "", limit: int = 100) -> list:
    """列出回收站中的接口用例 → DDD 门面。"""
    result = apitest_app_service.list_trash_cases(
        project_id=project_id, limit=limit)
    return result.get("list", [])


def count_trash_cases(project_id: str = "") -> int:
    """统计回收站中的接口用例数 → 从 DDD list_trash total 获取。"""
    result = apitest_app_service.list_trash_cases(
        project_id=project_id, limit=1)
    return result.get("total", 0)


def batch_delete_cases(ids: list) -> int:
    """批量软删接口用例 → 逐条经 DDD 门面删除。"""
    n = 0
    for cid in ids or []:
        if delete_api_case(cid):
            n += 1
    return n


def batch_restore_cases(ids: list) -> int:
    """批量恢复回收站中的接口用例 → 逐条经 DDD 门面恢复。"""
    n = 0
    for cid in ids or []:
        if restore_api_case(cid):
            n += 1
    return n


# ── Scenario ───────────────────────────────────────────────
def create_scenario(payload: dict) -> Optional[dict]:
    payload = _unstruct(payload, "scenario")
    return apitest_app_service.create_scenario(CreateScenarioCommand(
        name=payload.get("name", "未命名接口场景"),
        steps=payload.get("steps"),
        description=payload.get("description", ""),
        environment_id=payload.get("environment_id", ""),
        project_id=payload.get("project_id", ""),
        operator=_OPERATOR,
    ))


def update_scenario(scenario_id: str, payload: dict) -> Optional[dict]:
    payload = _unstruct(payload, "scenario")
    cmd = UpdateScenarioCommand(
        scenario_id=scenario_id,
        name=payload.get("name"),
        steps=payload.get("steps"),
        description=payload.get("description"),
        status=payload.get("status"),
        environment_id=payload.get("environment_id"),
        project_id=payload.get("project_id"),
        operator=_OPERATOR,
    )
    for f in ("name", "steps", "description", "status", "environment_id", "project_id"):
        if f not in payload:
            setattr(cmd, f, None)
    return _safe(lambda: apitest_app_service.update_scenario(cmd), None)


def delete_scenario(scenario_id: str) -> bool:
    return _safe(lambda: apitest_app_service.delete_scenario(
        DeleteScenarioCommand(scenario_id=scenario_id, operator=_OPERATOR)), False)


def restore_scenario(scenario_id: str) -> bool:
    return _safe(lambda: apitest_app_service.restore_scenario(
        RestoreScenarioCommand(scenario_id=scenario_id, operator=_OPERATOR)), False)


def list_scenarios(keyword: str = "", limit: int = 100,
                   offset: int = 0, project_id: str = "", **kwargs) -> list:
    """列表接口场景 → DDD 门面。"""
    result = apitest_app_service.list_scenarios(ScenarioListQuery(
        keyword=keyword, project_id=project_id,
        limit=limit, offset=offset,
    ))
    return result.get("list", [])


def count_scenarios(project_id: str = "", **kwargs) -> int:
    """统计接口场景数 → DDD 门面 total（含 keyword 过滤）。"""
    q = ScenarioListQuery(
        keyword=kwargs.get("keyword", ""), project_id=project_id,
        limit=1,  # 仅取 total，不拉行
    )
    result = apitest_app_service.list_scenarios(q)
    return result.get("total", 0)


def list_trash_scenarios(project_id: str = "", limit: int = 100) -> list:
    """列出回收站中的接口场景 → DDD 门面。"""
    result = apitest_app_service.list_trash_scenarios(
        project_id=project_id, limit=limit)
    return result.get("list", [])


def count_trash_scenarios(project_id: str = "") -> int:
    """统计回收站中的接口场景数 → 从 DDD list_trash total 获取。"""
    result = apitest_app_service.list_trash_scenarios(
        project_id=project_id, limit=1)
    return result.get("total", 0)


def batch_delete_scenarios(ids: list) -> int:
    """批量软删接口场景 → 逐条经 DDD 门面删除。"""
    n = 0
    for sid in ids or []:
        if delete_scenario(sid):
            n += 1
    return n


def batch_restore_scenarios(ids: list) -> int:
    """批量恢复回收站中的接口场景 → 逐条经 DDD 门面恢复。"""
    n = 0
    for sid in ids or []:
        if restore_scenario(sid):
            n += 1
    return n


# ── 单查（仅路由 Web 层使用）──────────────────────────────
def get_definition(definition_id: str) -> Optional[dict]:
    return apitest_app_service.get_definition(definition_id)


def get_api_case(case_id: str) -> Optional[dict]:
    return apitest_app_service.get_api_case(case_id)


def get_scenario(scenario_id: str) -> Optional[dict]:
    return apitest_app_service.get_scenario(scenario_id)


# ── Mock 服务 ────────────────────────────────────────────
def create_mock(payload: dict) -> Optional[dict]:
    from app.domain.apitest.application.apitest_app_service import apitest_app_service
    from app.domain.apitest.application.dto import CreateMockCommand
    payload = _unstruct(payload, "mock")
    cmd = CreateMockCommand(
        name=payload.get("name", "未命名Mock服务"),
        api_definition_id=payload.get("api_definition_id", ""),
        method=payload.get("method", "GET"),
        path=payload.get("path", ""),
        status_code=payload.get("status_code", 200),
        response_body=payload.get("response_body", ""),
        response_headers=payload.get("response_headers"),
        delay_ms=payload.get("delay_ms", 0),
        active=payload.get("active", 1),
        description=payload.get("description", ""),
        project_id=payload.get("project_id", ""),
        match_type=payload.get("match_type", "exact"),
        match_script=payload.get("match_script", ""),
    )
    return apitest_app_service.create_mock(cmd)


def update_mock(mock_id: str, payload: dict) -> Optional[dict]:
    from app.domain.apitest.application.apitest_app_service import apitest_app_service
    from app.domain.apitest.application.dto import UpdateMockCommand
    payload = _unstruct(payload, "mock")
    cmd = UpdateMockCommand(
        mock_id=mock_id,
        name=payload.get("name"),
        api_definition_id=payload.get("api_definition_id"),
        method=payload.get("method"),
        path=payload.get("path"),
        status_code=payload.get("status_code"),
        response_body=payload.get("response_body"),
        response_headers=payload.get("response_headers"),
        delay_ms=payload.get("delay_ms"),
        active=payload.get("active"),
        description=payload.get("description"),
        project_id=payload.get("project_id"),
        match_type=payload.get("match_type"),
        match_script=payload.get("match_script"),
    )
    # 仅传入 payload 中真实出现的字段
    for f in ("name", "api_definition_id", "method", "path", "status_code",
              "response_body", "response_headers", "delay_ms", "active",
              "description", "project_id", "match_type", "match_script"):
        if f not in payload:
            setattr(cmd, f, None)
    return _safe(lambda: apitest_app_service.update_mock(cmd), None)


def delete_mock(mock_id: str) -> bool:
    from app.domain.apitest.application.apitest_app_service import apitest_app_service
    from app.domain.apitest.application.dto import DeleteMockCommand
    return _safe(lambda: apitest_app_service.delete_mock(
        DeleteMockCommand(mock_id=mock_id)), False)


def restore_mock(mock_id: str) -> bool:
    from app.domain.apitest.application.apitest_app_service import apitest_app_service
    from app.domain.apitest.application.dto import RestoreMockCommand
    return _safe(lambda: apitest_app_service.restore_mock(
        RestoreMockCommand(mock_id=mock_id)), False)


def purge_mock(mock_id: str) -> bool:
    from app.domain.apitest.application.apitest_app_service import apitest_app_service
    from app.domain.apitest.application.dto import PurgeMockCommand
    return _safe(lambda: apitest_app_service.purge_mock(
        PurgeMockCommand(mock_id=mock_id)), False)


def get_mock(mock_id: str) -> Optional[dict]:
    from app.domain.apitest.application.apitest_app_service import apitest_app_service
    return apitest_app_service.get_mock(mock_id)


def list_mocks(payload: dict = None) -> dict:
    """Mock 列表（keyword/limit/offset/project_id → DDD 门面）。"""
    from app.domain.apitest.application.apitest_app_service import apitest_app_service
    from app.domain.apitest.application.dto import MockListQuery
    payload = payload or {}
    result = apitest_app_service.list_mocks(MockListQuery(
        keyword=payload.get("keyword", ""),
        project_id=payload.get("project_id", ""),
        limit=payload.get("limit", 100),
        offset=payload.get("offset", 0),
    ))
    return result


def count_mocks(project_id: str = "", **kwargs) -> int:
    from app.domain.apitest.application.apitest_app_service import apitest_app_service
    return apitest_app_service.count_mocks(project_id=project_id, **kwargs)


def list_trash_mocks(project_id: str = "", limit: int = 100) -> dict:
    from app.domain.apitest.application.apitest_app_service import apitest_app_service
    result = apitest_app_service.list_trash_mocks(
        project_id=project_id, limit=limit)
    return result


def count_trash_mocks(project_id: str = "") -> int:
    from app.domain.apitest.application.apitest_app_service import apitest_app_service
    return apitest_app_service.count_trash_mocks(project_id=project_id)


def batch_delete_mocks(ids: list) -> int:
    from app.domain.apitest.application.apitest_app_service import apitest_app_service
    from app.domain.apitest.application.dto import BatchDeleteMocksCommand
    return apitest_app_service.batch_delete_mocks(
        BatchDeleteMocksCommand(ids=list(ids or [])))


def batch_restore_mocks(ids: list) -> int:
    from app.domain.apitest.application.apitest_app_service import apitest_app_service
    from app.domain.apitest.application.dto import BatchRestoreMocksCommand
    return apitest_app_service.batch_restore_mocks(
        BatchRestoreMocksCommand(ids=list(ids or [])))


def batch_purge_mocks(ids: list) -> int:
    from app.domain.apitest.application.apitest_app_service import apitest_app_service
    from app.domain.apitest.application.dto import BatchPurgeMocksCommand
    return apitest_app_service.batch_purge_mocks(
        BatchPurgeMocksCommand(ids=list(ids or [])))


def run_mock_request(method: str = "GET", path: str = "/", base_path: str = "",
                     query_params: dict = None, request_body: str = "") -> Optional[dict]:
    from app.domain.apitest.application.apitest_app_service import apitest_app_service
    from app.domain.apitest.application.dto import RunMockRequestCommand
    return apitest_app_service.run_mock_request(RunMockRequestCommand(
        method=method, path=path, base_path=base_path,
        query_params=query_params, request_body=request_body,
    ))


# ═══════════════════════════════════════════════════
# module stats / purge / batch_purge / batch_update / rollback_definition
# 阶段 C 续：将 apitest_service 仍直连 ApitestRepo 的旁路方法收进 DDD 门面。
# 复用 app_service 的 batch_op_by_repo / purge_by_repo 薄门面，保持既有
# 返回语义（purge/batch_update/batch_purge 逐资源透传既有 ApitestRepo）。
# ═══════════════════════════════════════════════════

def purge_definition(definition_id: str) -> bool:
    """物理删除接口定义（回收站 purge）→ 经 DDD 门面。"""
    return apitest_app_service.purge_by_repo(definition_id, "definition")


def purge_case(case_id: str) -> bool:
    """物理删除接口用例（回收站 purge）→ 经 DDD 门面。"""
    return apitest_app_service.purge_by_repo(case_id, "case")


def purge_scenario(scenario_id: str) -> bool:
    """物理删除场景（回收站 purge）→ 经 DDD 门面。"""
    return apitest_app_service.purge_by_repo(scenario_id, "scenario")


def batch_purge_definitions(ids: list) -> int:
    """批量物理删除接口定义 → 经 DDD 门面。"""
    return apitest_app_service.batch_op_by_repo(
        list(ids or []), "purge", "definition")


def batch_update_definitions(ids: list, **fields) -> int:
    """批量更新接口定义 → 经 DDD 门面。"""
    return apitest_app_service.batch_op_by_repo(
        list(ids or []), "update", "definition", **fields)


def batch_purge_cases(ids: list) -> int:
    """批量物理删除接口用例 → 经 DDD 门面。"""
    return apitest_app_service.batch_op_by_repo(
        list(ids or []), "purge", "case")


def batch_update_cases(ids: list, **fields) -> int:
    """批量更新接口用例 → 经 DDD 门面。"""
    return apitest_app_service.batch_op_by_repo(
        list(ids or []), "update", "case", **fields)


def batch_purge_scenarios(ids: list) -> int:
    """批量物理删除场景 → 经 DDD 门面。"""
    return apitest_app_service.batch_op_by_repo(
        list(ids or []), "purge", "scenario")


def batch_update_scenarios(ids: list, **fields) -> int:
    """批量更新场景 → 经 DDD 门面。"""
    return apitest_app_service.batch_op_by_repo(
        list(ids or []), "update", "scenario", **fields)


def rollback_definition(definition_id: str, version_id: str) -> Optional[dict]:
    """接口定义回滚到指定版本 → 经 DDD 门面。"""
    return apitest_app_service.rollback_definition(definition_id, version_id)


def count_definitions_by_module(protocols=None) -> dict:
    """按模块统计接口定义数 {module_id: count} → 经 DDD 门面。"""
    return apitest_app_service.count_definitions_by_module(protocols=protocols)


def count_modules(module_type: str = "api") -> int:
    """统计模块数量 → 经 DDD 门面。"""
    return apitest_app_service.count_modules(module_type)


def count_definitions_total(protocols=None) -> int:
    """统计接口定义总数（可选按协议过滤）→ 经 DDD 门面。"""
    return apitest_app_service.count_definitions_total(protocols=protocols)


def count_cases_for_definition(definition_id: str) -> int:
    """统计某接口定义下的接口用例数 → 经 DDD 门面。"""
    return apitest_app_service.count_cases_for_definition(definition_id)
