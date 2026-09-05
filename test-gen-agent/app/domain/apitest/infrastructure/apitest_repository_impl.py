"""Apitest 聚合仓储实现（Adapter 防腐层）。

把面向聚合的仓储接口翻译为既有 ApitestRepo 命令，实现防腐层
（Anti-Corruption Layer）。复用已验证的存储逻辑，同时让领域层获得
聚合级读写语义；后续如需换存储仅替换本文件。

四个聚合根仓储各一个适配器，均代理至 ApitestRepo：
  - ApiDefinitionRepoAdapter   → api_definitions 表
  - ApiCaseRepoAdapter         → api_cases 表
  - ScenarioRepoAdapter        → api_scenarios 表
  - MockRepoAdapter            → api_mocks 表
"""
from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from app.domain.apitest.domain.entities.api_case import ApiCase
from app.domain.apitest.domain.entities.mock import ApiMock
from app.domain.apitest.domain.entities.api_definition import ApiDefinition
from app.domain.apitest.domain.entities.scenario import Scenario
from app.repositories.apitest_repo import ApitestRepo


# ── ApiDefinition 仓储 ─────────────────────────────────
class ApiDefinitionRepoAdapter:
    """将既有 ApitestRepo 封装为面向聚合的 ApiDefinition 仓储。"""

    def next_id(self) -> str:
        return uuid.uuid4().hex[:12]

    # ── 读：聚合重建 ────────────────────────────────
    def find_by_id(self, definition_id: str,
                   include_deleted: bool = False) -> Optional[ApiDefinition]:
        row = ApitestRepo.get_definition(definition_id)
        if row is None and include_deleted:
            # 回收站：直接查删除行
            rows = ApitestRepo.list_trash_definitions(limit=9999)
            for r in rows:
                if str(r.get("id")) == str(definition_id):
                    return ApiDefinition.from_dict(dict(r))
        return ApiDefinition.from_dict(dict(row)) if row else None

    def list_trash(self, project_id: str = "",
                   limit: int = 100) -> Tuple[List[ApiDefinition], int]:
        rows = ApitestRepo.list_trash_definitions(
            project_id=project_id, limit=limit)
        total = ApitestRepo.count_trash_definitions(project_id=project_id)
        return [ApiDefinition.from_dict(dict(r)) for r in rows], total

    def list(self, *, keyword: str = "", project_id: str = "",
             limit: int = 100, offset: int = 0,
             include_latest_only: bool = True,
             protocols: Optional[list] = None,
             module_ids: Optional[list] = None) -> Tuple[List[ApiDefinition], int]:
        rows = ApitestRepo.list_definitions(
            keyword=keyword, limit=limit, offset=offset,
            project_id=project_id, include_latest_only=include_latest_only,
            protocols=protocols, module_ids=module_ids)
        total = ApitestRepo.count_definitions(
            project_id=project_id, keyword=keyword,
            protocols=protocols, module_ids=module_ids)
        return [ApiDefinition.from_dict(dict(r)) for r in rows], total

    def count(self, project_id: str = "", **kwargs) -> int:
        return ApitestRepo.count_definitions(project_id=project_id, **kwargs)

    def record_version(self, definition_id: str, version: str = "",
                       operator: str = "") -> Optional[dict]:
        item = ApitestRepo.get_definition(definition_id)
        if not item:
            return None
        return ApitestRepo.create_definition_version(
            definition_id, version)

    def list_versions(self, ref_id: str) -> list:
        return ApitestRepo.list_definition_versions(ref_id)

    # ── 写：以聚合为粒度落库 ────────────────────────
    def save(self, definition: ApiDefinition, version: str = "v1") -> ApiDefinition:
        d = definition.to_dict()
        kwargs = {
            "version": version,
            "name": d["name"],
            "protocol": d["protocol"],
            "method": d["method"],
            "path": d["path"],
            "headers": d["headers"],
            "body": d["body"],
            "query": d["query"],
            "params": d["params"],
            "description": d["description"],
            "tags": d["tags"],
            "module_id": d.get("module_id", ""),
            "project_id": d.get("project_id", ""),
        }
        result = ApitestRepo.create_definition(**kwargs)
        if result and result.get("id"):
            return ApiDefinition.from_dict(dict(result))
        return definition

    def update(self, definition: ApiDefinition) -> bool:
        d = definition.to_dict()
        kwargs = {
            "name": d["name"],
            "protocol": d["protocol"],
            "method": d["method"],
            "path": d["path"],
            "headers": d["headers"],
            "body": d["body"],
            "query": d["query"],
            "params": d["params"],
            "description": d["description"],
            "tags": d["tags"],
        }
        if d.get("module_id"):
            kwargs["module_id"] = d["module_id"]
        result = ApitestRepo.update_definition(definition.id.value, **kwargs)
        return result is not None

    def soft_delete(self, definition_id: str) -> bool:
        return ApitestRepo.delete_definition(definition_id)

    def restore(self, definition_id: str) -> bool:
        return ApitestRepo.restore_definition(definition_id)


# ── ApiCase 仓储 ────────────────────────────────────────
class ApiCaseRepoAdapter:
    """将既有 ApitestRepo 封装为面向聚合的 ApiCase 仓储。"""

    def next_id(self) -> str:
        return uuid.uuid4().hex[:12]

    # ── 读：聚合重建 ────────────────────────────────
    def find_by_id(self, case_id: str,
                   include_deleted: bool = False) -> Optional[ApiCase]:
        row = ApitestRepo.get_api_case(case_id)
        if row is None and include_deleted:
            rows = ApitestRepo.list_trash_cases(limit=9999)
            for r in rows:
                if str(r.get("id")) == str(case_id):
                    return ApiCase.from_dict(dict(r))
        return ApiCase.from_dict(dict(row)) if row else None

    def list_trash(self, project_id: str = "",
                   limit: int = 100) -> Tuple[List[ApiCase], int]:
        rows = ApitestRepo.list_trash_cases(project_id, limit)
        total = ApitestRepo.count_trash_cases(project_id)
        return [ApiCase.from_dict(dict(r)) for r in rows], total

    def list(self, *, keyword: str = "", project_id: str = "",
             api_definition_id: str = "",
             limit: int = 100, offset: int = 0) -> Tuple[List[ApiCase], int]:
        rows = ApitestRepo.list_api_cases(
            keyword=keyword, limit=limit, offset=offset,
            project_id=project_id, api_definition_id=api_definition_id)
        total = ApitestRepo.count_api_cases(
            project_id=project_id, keyword=keyword,
            api_definition_id=api_definition_id)
        return [ApiCase.from_dict(dict(r)) for r in rows], total

    def count(self, project_id: str = "", **kwargs) -> int:
        return ApitestRepo.count_api_cases(project_id=project_id, **kwargs)

    # ── 写：以聚合为粒度落库 ────────────────────────
    def save(self, case: ApiCase) -> ApiCase:
        d = case.to_dict()
        kwargs = {
            "name": d["name"],
            "api_definition_id": d["api_definition_id"],
            "request": d["request"],
            "asserts": d["asserts"],
            "pre_scripts": d["pre_scripts"],
            "post_scripts": d["post_scripts"],
            "pre_sql": d["pre_sql"],
            "post_sql": d["post_sql"],
            "variables": d["variables"],
            "logic_controllers": d["logic_controllers"],
            "environment_id": d["environment_id"],
            "status": d["status"],
            "priority": d["priority"],
            "description": d["description"],
            "project_id": d["project_id"],
        }
        result = ApitestRepo.create_api_case(**kwargs)
        if result and result.get("id"):
            return ApiCase.from_dict(dict(result))
        return case

    def update(self, case: ApiCase) -> bool:
        d = case.to_dict()
        kwargs = {
            "name": d["name"],
            "api_definition_id": d["api_definition_id"],
            "request": d["request"],
            "asserts": d["asserts"],
            "pre_scripts": d["pre_scripts"],
            "post_scripts": d["post_scripts"],
            "pre_sql": d["pre_sql"],
            "post_sql": d["post_sql"],
            "variables": d["variables"],
            "logic_controllers": d["logic_controllers"],
            "environment_id": d["environment_id"],
            "status": d["status"],
            "priority": d["priority"],
            "description": d["description"],
            "project_id": d["project_id"],
        }
        result = ApitestRepo.update_api_case(case.id.value, **kwargs)
        return result is not None

    def soft_delete(self, case_id: str) -> bool:
        return ApitestRepo.delete_api_case(case_id)

    def restore(self, case_id: str) -> bool:
        return ApitestRepo.restore_case(case_id)


# ── Scenario 仓储 ───────────────────────────────────────
class ScenarioRepoAdapter:
    """将既有 ApitestRepo 封装为面向聚合的 Scenario 仓储。"""

    def next_id(self) -> str:
        return uuid.uuid4().hex[:12]

    # ── 读：聚合重建 ────────────────────────────────
    def find_by_id(self, scenario_id: str,
                   include_deleted: bool = False) -> Optional[Scenario]:
        row = ApitestRepo.get_scenario(scenario_id)
        if row is None and include_deleted:
            rows = ApitestRepo.list_trash_scenarios(limit=9999)
            for r in rows:
                if str(r.get("id")) == str(scenario_id):
                    return Scenario.from_dict(dict(r))
        return Scenario.from_dict(dict(row)) if row else None

    def list_trash(self, project_id: str = "",
                   limit: int = 100) -> Tuple[List[Scenario], int]:
        rows = ApitestRepo.list_trash_scenarios(project_id, limit)
        total = ApitestRepo.count_trash_scenarios(project_id)
        return [Scenario.from_dict(dict(r)) for r in rows], total

    def list(self, *, keyword: str = "", project_id: str = "",
             limit: int = 100, offset: int = 0) -> Tuple[List[Scenario], int]:
        rows = ApitestRepo.list_scenarios(
            keyword=keyword, limit=limit, offset=offset, project_id=project_id)
        total = ApitestRepo.count_scenarios(
            project_id=project_id, keyword=keyword)
        return [Scenario.from_dict(dict(r)) for r in rows], total

    def count(self, project_id: str = "", **kwargs) -> int:
        return ApitestRepo.count_scenarios(project_id=project_id, **kwargs)

    # ── 写：以聚合为粒度落库 ────────────────────────
    def save(self, scenario: Scenario) -> Scenario:
        d = scenario.to_dict()
        kwargs = {
            "name": d["name"],
            "steps": d["steps"],
            "description": d["description"],
            "status": d["status"],
            "environment_id": d["environment_id"],
            "project_id": d["project_id"],
        }
        result = ApitestRepo.create_scenario(**kwargs)
        if result and result.get("id"):
            return Scenario.from_dict(dict(result))
        return scenario

    def update(self, scenario: Scenario) -> bool:
        d = scenario.to_dict()
        kwargs = {
            "name": d["name"],
            "steps": d["steps"],
            "description": d["description"],
            "status": d["status"],
            "environment_id": d["environment_id"],
            "project_id": d["project_id"],
        }
        result = ApitestRepo.update_scenario(scenario.id.value, **kwargs)
        return result is not None

    def soft_delete(self, scenario_id: str) -> bool:
        return ApitestRepo.delete_scenario(scenario_id)

    def restore(self, scenario_id: str) -> bool:
        return ApitestRepo.restore_scenario(scenario_id)


# ── 单例 ─────────────────────────────────────────────────
definition_repository = ApiDefinitionRepoAdapter()
api_case_repository = ApiCaseRepoAdapter()
scenario_repository = ScenarioRepoAdapter()


# ── Mock 仓储 ───────────────────────────────────────────
class MockRepoAdapter:
    """将既有 ApitestRepo 封装为面向聚合的 Mock 仓储。

    Mock 服务（api_mocks 表）的 CRUD/回收站/批量操作全部经 ApitestRepo
    落库；本适配器提供聚合级读写语义，供应用层编排。批量操作（delete/
    restore/purge）在 app_service 侧组合调用单条语义。
    """

    def next_id(self) -> str:
        return uuid.uuid4().hex[:12]

    # ── 读：聚合重建 ────────────────────────────────
    def find_by_id(self, mock_id: str,
                   include_deleted: bool = False) -> Optional[ApiMock]:
        row = ApitestRepo.get_mock(mock_id)
        if row is None and include_deleted:
            rows = ApitestRepo.list_trash_mocks(limit=9999)
            for r in rows:
                if str(r.get("id")) == str(mock_id):
                    return ApiMock.from_dict(dict(r))
        return ApiMock.from_dict(dict(row)) if row else None

    def list_trash(self, project_id: str = "",
                   limit: int = 100) -> Tuple[List[ApiMock], int]:
        rows = ApitestRepo.list_trash_mocks(project_id=project_id, limit=limit)
        total = ApitestRepo.count_trash_mocks(project_id=project_id)
        return [ApiMock.from_dict(dict(r)) for r in rows], total

    def list(self, *, keyword: str = "", project_id: str = "",
             limit: int = 100, offset: int = 0) -> Tuple[List[ApiMock], int]:
        rows = ApitestRepo.list_mocks(
            keyword=keyword, limit=limit, offset=offset, project_id=project_id)
        total = ApitestRepo.count_mocks(project_id=project_id)
        return [ApiMock.from_dict(dict(r)) for r in rows], total

    def count(self, project_id: str = "", **kwargs) -> int:
        return ApitestRepo.count_mocks(project_id=project_id, **kwargs)

    def count_trash(self, project_id: str = "") -> int:
        return ApitestRepo.count_trash_mocks(project_id=project_id)

    # ── 写：以聚合为粒度落库 ────────────────────────
    def save(self, mock: ApiMock) -> ApiMock:
        d = mock.to_dict()
        kwargs = {
            "name": d["name"],
            "api_definition_id": d["api_definition_id"],
            "method": d["method"],
            "path": d["path"],
            "status_code": d["status_code"],
            "response_body": d["response_body"],
            "response_headers": d["response_headers"],
            "delay_ms": d["delay_ms"],
            "active": d["active"],
            "description": d["description"],
            "project_id": d["project_id"],
            "match_type": d["match_type"],
            "match_script": d["match_script"],
        }
        result = ApitestRepo.create_mock(**kwargs)
        if result and result.get("id"):
            return ApiMock.from_dict(dict(result))
        return mock

    def update(self, mock: ApiMock) -> bool:
        d = mock.to_dict()
        kwargs = {
            "name": d["name"],
            "api_definition_id": d["api_definition_id"],
            "method": d["method"],
            "path": d["path"],
            "status_code": d["status_code"],
            "response_body": d["response_body"],
            "response_headers": d["response_headers"],
            "delay_ms": d["delay_ms"],
            "active": d["active"],
            "description": d["description"],
            "project_id": d["project_id"],
            "match_type": d["match_type"],
            "match_script": d["match_script"],
        }
        result = ApitestRepo.update_mock(mock.id.value, **kwargs)
        return result is not None

    def soft_delete(self, mock_id: str) -> bool:
        return ApitestRepo.delete_mock(mock_id)

    def restore(self, mock_id: str) -> bool:
        return ApitestRepo.restore_mock(mock_id)

    def purge(self, mock_id: str) -> bool:
        return ApitestRepo.purge_mock(mock_id)


# ── Mock 单例 ─────────────────────────────────────────
mock_repository = MockRepoAdapter()
