"""接口测试应用服务（Application Service / Use Case 门面）。

职责：
  1. 作为路由器与领域层之间的用例编排入口；
  2. 承载接口测试域的事务边界：加载聚合 → 执行领域命令 → 保存聚合 →
     发布领域事件；
  3. 将领域异常透传给上层（由 Web 层统一翻译为 HTTP 响应）。

保持瘦：只做编排，不写业务规则（业务规则在领域层聚合内）。
"""
from __future__ import annotations

import logging
from typing import Optional

from app.domain.apitest.application.dto import (
    BatchDeleteMocksCommand,
    BatchPurgeMocksCommand,
    BatchRestoreMocksCommand,
    CaseListQuery,
    ChangeApiCaseStatusCommand,
    CreateApiCaseCommand,
    CreateDefinitionCommand,
    CreateMockCommand,
    CreateScenarioCommand,
    CreateVersionCommand,
    DefinitionListQuery,
    DeleteCaseCommand,
    DeleteDefinitionCommand,
    DeleteMockCommand,
    DeleteScenarioCommand,
    MockListQuery,
    PurgeMockCommand,
    RestoreCaseCommand,
    RestoreDefinitionCommand,
    RestoreMockCommand,
    RestoreScenarioCommand,
    RunMockRequestCommand,
    ScenarioListQuery,
    UpdateApiCaseCommand,
    UpdateDefinitionCommand,
    UpdateMockCommand,
    UpdateScenarioCommand,
)
from app.domain.apitest.domain.entities.api_case import ApiCase
from app.domain.apitest.domain.entities.mock import ApiMock
from app.domain.apitest.domain.entities.api_definition import ApiDefinition
from app.domain.apitest.domain.entities.scenario import Scenario
from app.domain.apitest.infrastructure.apitest_repository_impl import (
    api_case_repository,
    definition_repository,
    mock_repository,
    scenario_repository,
)
from app.domain.common.domain_events import event_bus
from app.domain.common.exceptions import AggregateNotFound

logger = logging.getLogger(__name__)


class ApitestAppService:
    """接口测试用例编排服务。"""

    def __init__(
        self,
        *,
        definition_repo=None,
        case_repo=None,
        scenario_repo=None,
        mock_repo=None,
    ):
        self._def_repo = definition_repo or definition_repository
        self._case_repo = case_repo or api_case_repository
        self._scn_repo = scenario_repo or scenario_repository
        self._mock_repo = mock_repo or mock_repository

    # ═══════════════════════════════════════════════════
    # ApiDefinition
    # ═══════════════════════════════════════════════════
    def create_definition(self, cmd: CreateDefinitionCommand) -> dict:
        definition = ApiDefinition(
            definition_id=self._def_repo.next_id(),
            name=cmd.name,
            protocol=cmd.protocol,
            method=cmd.method,
            path=cmd.path,
            headers=cmd.headers,
            body=cmd.body,
            query=cmd.query,
            params=cmd.params,
            description=cmd.description,
            tags=cmd.tags,
            module_id=cmd.module_id,
            project_id=cmd.project_id,
        )
        saved = self._def_repo.save(definition, version=cmd.version)
        self._publish(saved)
        return saved.to_dict()

    def get_definition(self, definition_id: str) -> Optional[dict]:
        definition = self._def_repo.find_by_id(definition_id)
        return definition.to_dict() if definition else None

    def update_definition(self, cmd: UpdateDefinitionCommand) -> Optional[dict]:
        definition = self._find_definition_or_raise(cmd.definition_id)
        definition.set_content(
            name=cmd.name,
            protocol=cmd.protocol,
            method=cmd.method,
            path=cmd.path,
            headers=cmd.headers,
            body=cmd.body,
            query=cmd.query,
            params=cmd.params,
            description=cmd.description,
            tags=cmd.tags,
            module_id=cmd.module_id,
            operator=cmd.operator,
        )
        self._def_repo.update(definition)
        self._publish(definition)
        return definition.to_dict()

    def delete_definition(self, cmd: DeleteDefinitionCommand) -> bool:
        definition = self._find_definition_or_raise(cmd.definition_id)
        definition.delete(cmd.operator, cmd.reason)
        self._def_repo.soft_delete(definition.id.value)
        self._publish(definition)
        return True

    def restore_definition(self, cmd: RestoreDefinitionCommand) -> bool:
        definition = self._def_repo.find_by_id(
            cmd.definition_id, include_deleted=True)
        if definition is None or not definition.deleted:
            raise AggregateNotFound(f"回收站中不存在该接口定义: {cmd.definition_id}")
        definition.restore(cmd.operator)
        self._def_repo.restore(cmd.definition_id)
        self._publish(definition)
        return True

    def list_definitions(self, query: DefinitionListQuery) -> dict:
        items, total = self._def_repo.list(
            keyword=query.keyword, project_id=query.project_id,
            limit=query.limit, offset=query.offset,
            include_latest_only=query.include_latest_only,
            protocols=query.protocols, module_ids=query.module_ids,
        )
        return {"list": [d.to_dict() for d in items], "total": total}

    def list_trash_definitions(self, project_id: str = "", limit: int = 100) -> dict:
        items, total = self._def_repo.list_trash(
            project_id=project_id, limit=limit)
        return {"list": [d.to_dict() for d in items], "total": total}

    def create_definition_version(self, cmd: CreateVersionCommand) -> Optional[dict]:
        definition = self._find_definition_or_raise(cmd.definition_id)
        definition.create_version(cmd.version, cmd.operator)
        result = self._def_repo.record_version(
            cmd.definition_id, cmd.version, cmd.operator)
        self._publish(definition)
        return result

    def list_definition_versions(self, ref_id: str) -> list:
        return self._def_repo.list_versions(ref_id)

    # ═══════════════════════════════════════════════════
    # ApiCase
    # ═══════════════════════════════════════════════════
    def create_api_case(self, cmd: CreateApiCaseCommand) -> dict:
        case = ApiCase(
            case_id=self._case_repo.next_id(),
            name=cmd.name,
            api_definition_id=cmd.api_definition_id,
            request=cmd.request,
            asserts=cmd.asserts,
            pre_scripts=cmd.pre_scripts,
            post_scripts=cmd.post_scripts,
            pre_sql=cmd.pre_sql,
            post_sql=cmd.post_sql,
            variables=cmd.variables,
            logic_controllers=cmd.logic_controllers,
            environment_id=cmd.environment_id,
            priority=cmd.priority,
            description=cmd.description,
            project_id=cmd.project_id,
        )
        saved = self._case_repo.save(case)
        self._publish(saved)
        return saved.to_dict()

    def get_api_case(self, case_id: str) -> Optional[dict]:
        case = self._case_repo.find_by_id(case_id)
        return case.to_dict() if case else None

    def update_api_case(self, cmd: UpdateApiCaseCommand) -> Optional[dict]:
        case = self._find_case_or_raise(cmd.case_id)
        case.set_content(
            name=cmd.name,
            api_definition_id=cmd.api_definition_id,
            request=cmd.request,
            asserts=cmd.asserts,
            pre_scripts=cmd.pre_scripts,
            post_scripts=cmd.post_scripts,
            pre_sql=cmd.pre_sql,
            post_sql=cmd.post_sql,
            variables=cmd.variables,
            logic_controllers=cmd.logic_controllers,
            environment_id=cmd.environment_id,
            description=cmd.description,
            project_id=cmd.project_id,
            operator=cmd.operator,
        )
        if cmd.priority is not None:
            case.change_priority(cmd.priority, cmd.operator)
        if cmd.status is not None and cmd.status != case.status.value.value:
            case.change_status(cmd.status, cmd.operator)
        self._case_repo.update(case)
        self._publish(case)
        return case.to_dict()

    def change_api_case_status(self, cmd: ChangeApiCaseStatusCommand) -> Optional[dict]:
        case = self._find_case_or_raise(cmd.case_id)
        case.change_status(cmd.target_status, cmd.operator)
        self._case_repo.update(case)
        self._publish(case)
        return case.to_dict()

    def delete_api_case(self, cmd: DeleteCaseCommand) -> bool:
        case = self._find_case_or_raise(cmd.case_id)
        case.delete(cmd.operator, cmd.reason)
        self._case_repo.soft_delete(case.id.value)
        self._publish(case)
        return True

    def restore_api_case(self, cmd: RestoreCaseCommand) -> bool:
        case = self._case_repo.find_by_id(cmd.case_id, include_deleted=True)
        if case is None or not case.deleted:
            raise AggregateNotFound(f"回收站中不存在该接口用例: {cmd.case_id}")
        case.restore(cmd.operator)
        self._case_repo.restore(cmd.case_id)
        self._publish(case)
        return True

    def list_api_cases(self, query: CaseListQuery) -> dict:
        items, total = self._case_repo.list(
            keyword=query.keyword, project_id=query.project_id,
            api_definition_id=query.api_definition_id,
            limit=query.limit, offset=query.offset,
        )
        return {"list": [c.to_dict() for c in items], "total": total}

    def list_trash_cases(self, project_id: str = "", limit: int = 100) -> dict:
        items, total = self._case_repo.list_trash(
            project_id=project_id, limit=limit)
        return {"list": [c.to_dict() for c in items], "total": total}

    # ═══════════════════════════════════════════════════
    # Scenario
    # ═══════════════════════════════════════════════════
    def create_scenario(self, cmd: CreateScenarioCommand) -> dict:
        scenario = Scenario(
            scenario_id=self._scn_repo.next_id(),
            name=cmd.name,
            steps=cmd.steps,
            description=cmd.description,
            environment_id=cmd.environment_id,
            project_id=cmd.project_id,
        )
        saved = self._scn_repo.save(scenario)
        self._publish(saved)
        return saved.to_dict()

    def get_scenario(self, scenario_id: str) -> Optional[dict]:
        scenario = self._scn_repo.find_by_id(scenario_id)
        return scenario.to_dict() if scenario else None

    def update_scenario(self, cmd: UpdateScenarioCommand) -> Optional[dict]:
        scenario = self._find_scenario_or_raise(cmd.scenario_id)
        scenario.set_content(
            name=cmd.name,
            steps=cmd.steps,
            description=cmd.description,
            environment_id=cmd.environment_id,
            project_id=cmd.project_id,
            operator=cmd.operator,
        )
        if cmd.status is not None and cmd.status != scenario.status.value.value:
            scenario.change_status(cmd.status, cmd.operator)
        self._scn_repo.update(scenario)
        self._publish(scenario)
        return scenario.to_dict()

    def delete_scenario(self, cmd: DeleteScenarioCommand) -> bool:
        scenario = self._find_scenario_or_raise(cmd.scenario_id)
        scenario.delete(cmd.operator, cmd.reason)
        self._scn_repo.soft_delete(scenario.id.value)
        self._publish(scenario)
        return True

    def restore_scenario(self, cmd: RestoreScenarioCommand) -> bool:
        scenario = self._scn_repo.find_by_id(
            cmd.scenario_id, include_deleted=True)
        if scenario is None or not scenario.deleted:
            raise AggregateNotFound(f"回收站中不存在该接口场景: {cmd.scenario_id}")
        scenario.restore(cmd.operator)
        self._scn_repo.restore(cmd.scenario_id)
        self._publish(scenario)
        return True

    def list_scenarios(self, query: ScenarioListQuery) -> dict:
        items, total = self._scn_repo.list(
            keyword=query.keyword, project_id=query.project_id,
            limit=query.limit, offset=query.offset,
        )
        return {"list": [s.to_dict() for s in items], "total": total}

    def list_trash_scenarios(self, project_id: str = "", limit: int = 100) -> dict:
        items, total = self._scn_repo.list_trash(
            project_id=project_id, limit=limit)
        return {"list": [s.to_dict() for s in items], "total": total}

    # ── 内部助手 ────────────────────────────────────
    def _find_definition_or_raise(self, definition_id: str) -> ApiDefinition:
        definition = self._def_repo.find_by_id(definition_id)
        if definition is None:
            raise AggregateNotFound(f"接口定义不存在或已删除: {definition_id}")
        return definition

    def _find_case_or_raise(self, case_id: str) -> ApiCase:
        case = self._case_repo.find_by_id(case_id)
        if case is None:
            raise AggregateNotFound(f"接口用例不存在或已删除: {case_id}")
        return case

    def _find_scenario_or_raise(self, scenario_id: str) -> Scenario:
        scenario = self._scn_repo.find_by_id(scenario_id)
        if scenario is None:
            raise AggregateNotFound(f"接口场景不存在或已删除: {scenario_id}")
        return scenario

    @staticmethod
    def _publish(aggregate) -> None:
        """发布聚合记录的领域事件。"""
        events = aggregate.pull_domain_events()
        for ev in events:
            event_bus.dispatch(ev)




# ═══════════════════════════════════════════════════
# ApiMock
# ═══════════════════════════════════════════════════
    def create_mock(self, cmd: CreateMockCommand) -> dict:
        mock = ApiMock(
            mock_id=self._mock_repo.next_id(),
            name=cmd.name,
            api_definition_id=cmd.api_definition_id,
            method=cmd.method,
            path=cmd.path,
            status_code=cmd.status_code,
            response_body=cmd.response_body,
            response_headers=cmd.response_headers,
            delay_ms=cmd.delay_ms,
            active=cmd.active,
            description=cmd.description,
            project_id=cmd.project_id,
            match_type=cmd.match_type,
            match_script=cmd.match_script,
            _created=True,
        )
        saved = self._mock_repo.save(mock)
        self._publish(mock)
        return saved.to_dict()

    def get_mock(self, mock_id: str) -> Optional[dict]:
        mock = self._mock_repo.find_by_id(mock_id)
        return mock.to_dict() if mock else None

    def update_mock(self, cmd: UpdateMockCommand) -> Optional[dict]:
        mock = self._find_mock_or_raise(cmd.mock_id)
        mock.set_content(
            name=cmd.name,
            api_definition_id=cmd.api_definition_id,
            method=cmd.method,
            path=cmd.path,
            status_code=cmd.status_code,
            response_body=cmd.response_body,
            response_headers=cmd.response_headers,
            delay_ms=cmd.delay_ms,
            active=cmd.active,
            description=cmd.description,
            project_id=cmd.project_id,
            match_type=cmd.match_type,
            match_script=cmd.match_script,
        )
        self._mock_repo.update(mock)
        self._publish(mock)
        return mock.to_dict()

    def delete_mock(self, cmd: DeleteMockCommand) -> bool:
        mock = self._find_mock_or_raise(cmd.mock_id)
        mock.delete()
        self._mock_repo.soft_delete(mock.id.value)
        self._publish(mock)
        return True

    def restore_mock(self, cmd: RestoreMockCommand) -> bool:
        mock = self._mock_repo.find_by_id(cmd.mock_id, include_deleted=True)
        if mock is None or not mock.deleted:
            raise AggregateNotFound(f"回收站中不存在该 Mock 服务: {cmd.mock_id}")
        mock.restore()
        self._mock_repo.restore(mock.id.value)
        self._publish(mock)
        return True

    def purge_mock(self, cmd: PurgeMockCommand) -> bool:
        mock = self._mock_repo.find_by_id(cmd.mock_id, include_deleted=True)
        if mock is None:
            raise AggregateNotFound(f"Mock 服务不存在: {cmd.mock_id}")
        self._mock_repo.purge(cmd.mock_id)
        return True

    def list_mocks(self, query: MockListQuery) -> dict:
        items, total = self._mock_repo.list(
            keyword=query.keyword, project_id=query.project_id,
            limit=query.limit, offset=query.offset,
        )
        return {"list": [m.to_dict() for m in items], "total": total}

    def count_mocks(self, project_id: str = "", **kwargs) -> int:
        return self._mock_repo.count(project_id=project_id, **kwargs)

    def list_trash_mocks(self, project_id: str = "", limit: int = 100) -> dict:
        items, total = self._mock_repo.list_trash(
            project_id=project_id, limit=limit)
        return {"list": [m.to_dict() for m in items], "total": total}

    def count_trash_mocks(self, project_id: str = "") -> int:
        return self._mock_repo.count_trash(project_id=project_id)

    def batch_delete_mocks(self, cmd: BatchDeleteMocksCommand) -> int:
        n = 0
        for mid in cmd.ids:
            try:
                self.delete_mock(DeleteMockCommand(mock_id=mid, operator=cmd.operator))
                n += 1
            except AggregateNotFound:
                pass
        return n

    def batch_restore_mocks(self, cmd: BatchRestoreMocksCommand) -> int:
        n = 0
        for mid in cmd.ids:
            try:
                self.restore_mock(RestoreMockCommand(mock_id=mid, operator=cmd.operator))
                n += 1
            except AggregateNotFound:
                pass
        return n

    def batch_purge_mocks(self, cmd: BatchPurgeMocksCommand) -> int:
        n = 0
        for mid in cmd.ids:
            try:
                self.purge_mock(PurgeMockCommand(mock_id=mid, operator=cmd.operator))
                n += 1
            except AggregateNotFound:
                pass
        return n

    def run_mock_request(self, cmd: RunMockRequestCommand) -> Optional[dict]:
        """Mock 请求匹配与运行。

        委托既有 ApitestRepo.run_mock_request 实现路径匹配与响应生成；
        此方法在应用层暴露供门面桥接，语义与旧契约一致。
        """
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.run_mock_request(
            method=cmd.method, path=cmd.path, base_path=cmd.base_path,
            query_params=cmd.query_params, request_body=cmd.request_body,
        )

    # ── Mock 内部助手 ────────────────────────────────
    def _find_mock_or_raise(self, mock_id: str) -> ApiMock:
        mock = self._mock_repo.find_by_id(mock_id)
        if mock is None:
            raise AggregateNotFound(f"Mock 服务不存在或已删除: {mock_id}")
        return mock

    # ═══════════════════════════════════════════════════
    # Environment (apitest 侧 api_environments)
    # ═══════════════════════════════════════════════════
    def list_environments(self, project_id: str = "", **kwargs) -> list:
        """环境列表（apitest 测试环境配置，非 Docker 环境域）。"""
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.list_environments(project_id=project_id, **kwargs)

    def count_environments(self, project_id: str = "", **kwargs) -> int:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.count_environments(project_id=project_id, **kwargs)

    def get_environment(self, env_id: str) -> Optional[dict]:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.get_environment(env_id)

    def create_environment(self, **kwargs) -> dict:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.create_environment(**kwargs)

    def update_environment(self, env_id: str, **kwargs) -> Optional[dict]:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.update_environment(env_id, **kwargs)

    def delete_environment(self, env_id: str) -> bool:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.delete_environment(env_id)

    def export_environment(self, env_id: str) -> Optional[dict]:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.export_environment(env_id)

    def import_environment(self, data: dict, project_id: str = "") -> dict:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.import_environment(data, project_id=project_id)

    def env_detail_to_frontend(self, env: dict) -> Optional[dict]:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.env_detail_to_frontend(env)

    # ═══════════════════════════════════════════════════
    # Environment Group (env_groups)
    # ═══════════════════════════════════════════════════
    def list_env_groups(self, project_id: str = "", keyword: str = "") -> list:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.list_env_groups(project_id=project_id, keyword=keyword)

    def get_env_group(self, group_id: str) -> Optional[dict]:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.get_env_group(group_id)

    def create_env_group(self, name: str = "", project_id: str = "",
                         description: str = "", env_group_project: list = None,
                         **kwargs) -> dict:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.create_env_group(
            name=name, project_id=project_id, description=description,
            env_group_project=env_group_project, **kwargs,
        )

    def update_env_group(self, group_id: str, **kwargs) -> Optional[dict]:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.update_env_group(group_id, **kwargs)

    def delete_env_group(self, group_id: str) -> bool:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.delete_env_group(group_id)

    # ═══════════════════════════════════════════════════
    # Global Params
    # ═══════════════════════════════════════════════════
    def get_global_params(self, project_id: str) -> Optional[dict]:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.get_global_params(project_id)

    def save_global_params(self, project_id: str, headers: list = None,
                           common_variables: list = None) -> dict:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.save_global_params(
            project_id, headers=headers, common_variables=common_variables,
        )

    def delete_global_params(self, project_id: str) -> bool:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.delete_global_params(project_id)

    def delete_global_param_by_id(self, param_id: str) -> bool:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.delete_global_param_by_id(param_id)

    # ═══════════════════════════════════════════════════
    # Module Tree / Module Store
    # ═══════════════════════════════════════════════════
    def build_module_tree(self, module_type: str = "api", include_api: bool = True,
                          project_id: str = "", **kwargs) -> list:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.build_module_tree(
            module_type, include_api=include_api, project_id=project_id,
        )

    def add_module(self, scope: str = "definition", name: str = "",
                   parent_id: str = "root", project_id: str = "",
                   module_type: str = "", **kwargs) -> dict:
        from app.repositories.apitest_repo import ApitestRepo
        mt = scope if scope else module_type
        return ApitestRepo.add_module(
            mt, name=name, parent_id=parent_id, project_id=project_id,
        )

    def update_module(self, module_id: str, name: str = "", **kwargs) -> bool:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.update_module(
            module_id, name=name or kwargs.get("name", ""),
        )

    def delete_module(self, module_id: str) -> bool:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.delete_module(module_id)

    def get_module(self, module_id: str) -> Optional[dict]:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.get_module(module_id)

    def list_modules(self, scope: str = "definition", project_id: str = "") -> list:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.list_modules(scope, project_id=project_id)

    def move_module(self, drag_node_id: str, drop_node_id: str,
                    drop_position: int = 0) -> bool:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.move_module(
            drag_node_id, drop_node_id, drop_position=drop_position,
        )

    def count_modules(self, module_type: str = "api") -> int:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.count_modules(module_type)

    # ═══════════════════════════════════════════════════
    # 执行（Execution）
    # ═══════════════════════════════════════════════════
    def run_case(self, case_id: str, environment_id: str = "") -> dict:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.run_case(case_id, environment_id=environment_id)

    def debug_api_call(self, **kwargs) -> dict:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.debug_api_call(**kwargs)

    def run_scenario(self, scenario: dict, environment_id: str = "") -> dict:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.run_scenario(scenario, environment_id)

    def import_content(self, content: str, fmt: str = "auto",
                       project_id: str = "") -> dict:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.import_content(content, fmt, project_id)

    def get_assert_types(self) -> dict:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.assert_types()

    # ═══════════════════════════════════════════════════
    # Followers（关注）
    # ═══════════════════════════════════════════════════
    def list_followers(self, resource_id: str, resource_type: str = "") -> list:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.list_followers(resource_id, resource_type)

    def follow_resource(self, resource_id: str, resource_type: str = "",
                        user_id: str = "") -> bool:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.follow_resource(resource_id, resource_type, user_id)

    def unfollow_resource(self, resource_id: str, resource_type: str = "",
                          user_id: str = "") -> bool:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.unfollow_resource(resource_id, resource_type, user_id)

    def toggle_follow(self, resource_id: str, resource_type: str = "",
                      user_id: str = "") -> bool:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.toggle_follow(resource_id, resource_type, user_id)

    def is_followed(self, resource_id: str, resource_type: str = "",
                    user_id: str = "") -> bool:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.is_followed(resource_id, resource_type, user_id)

    # ═══════════════════════════════════════════════════
    # Operation Logs
    # ═══════════════════════════════════════════════════
    def list_operation_logs(self, resource_type: str = "", resource_id: str = "",
                            project_id: str = "", limit: int = 100,
                            offset: int = 0, **kwargs) -> list:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.list_operation_logs(
            resource_type=resource_type, resource_id=resource_id,
            project_id=project_id, limit=limit, offset=offset, **kwargs,
        )

    def count_operation_logs(self, resource_type: str = "",
                             resource_id: str = "", project_id: str = "") -> int:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.count_operation_logs(
            resource_type=resource_type, resource_id=resource_id,
            project_id=project_id,
        )

    def clear_operation_logs(self, days: int = 30) -> int:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.clear_operation_logs(days=days)

    # ═══════════════════════════════════════════════════
    # Execution Logs（测试执行记录）
    # ═══════════════════════════════════════════════════
    def list_execution_logs(self, exec_type: str = "", target_id: str = "",
                            limit: int = 100, offset: int = 0,
                            keyword: str = "") -> list:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.list_execution_logs(
            exec_type, target_id, limit, offset=offset, keyword=keyword)

    def count_execution_logs(self, exec_type: str = "",
                             target_id: str = "", keyword: str = "") -> int:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.count_execution_logs(exec_type, target_id, keyword=keyword)

    def clear_execution_logs(self, exec_type: str = "") -> int:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.clear_execution_logs(exec_type)

    # ═══════════════════════════════════════════════════
    # 统计 / 定义版本辅助
    # ═══════════════════════════════════════════════════
    def dashboard_stats(self) -> dict:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.dashboard_stats()

    def count_definitions_by_module(self, protocols=None) -> dict:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.count_definitions_by_module(protocols=protocols)

    def count_definitions_total(self, protocols=None) -> int:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.count_definitions_total(protocols=protocols)

    def count_cases_for_definition(self, definition_id: str) -> int:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.count_cases_for_definition(definition_id)

    def list_schedules(self, keyword: str = "") -> list:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.list_schedules(keyword=keyword)

    def list_definition_versions(self, ref_id: str) -> list:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.list_definition_versions(ref_id)

    def create_definition_version(self, definition_id: str,
                                  version: str = "") -> Optional[dict]:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.create_definition_version(definition_id, version)

    def rollback_definition(self, definition_id: str,
                            version_id: str) -> Optional[dict]:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.rollback_definition(definition_id, version_id)

    # ═══════════════════════════════════════════════════
    # 批量/回收站 薄门面（definition/case/scenario 聚合旁路）
    # ═══════════════════════════════════════════════════
    def list_definitions_via_repo(self, keyword: str = "", limit: int = 100,
                                  offset: int = 0, project_id: str = "",
                                  include_latest_only: bool = True,
                                  protocols: Optional[list] = None,
                                  module_ids: Optional[list] = None) -> list:
        """definition 列表直接透传（薄门面）。"""
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.list_definitions(
            keyword, limit, offset, project_id=project_id,
            include_latest_only=include_latest_only,
            protocols=protocols, module_ids=module_ids,
        )

    def count_definitions(self, project_id: str = "", **kwargs) -> int:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.count_definitions(project_id=project_id, **kwargs)

    def list_cases_via_repo(self, keyword: str = "", limit: int = 100,
                            offset: int = 0, project_id: str = "",
                            **kwargs) -> list:
        """case 列表直接透传（薄门面）。"""
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.list_api_cases(
            keyword=keyword, limit=limit, offset=offset,
            project_id=project_id, **kwargs,
        )

    def count_cases(self, project_id: str = "", **kwargs) -> int:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.count_api_cases(project_id=project_id, **kwargs)

    def list_scenarios_via_repo(self, keyword: str = "", limit: int = 100,
                                offset: int = 0, project_id: str = "",
                                **kwargs) -> list:
        """scenario 列表直接透传（薄门面）。"""
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.list_scenarios(
            keyword=keyword, limit=limit, offset=offset,
            project_id=project_id, **kwargs,
        )

    def count_scenarios(self, project_id: str = "", **kwargs) -> int:
        from app.repositories.apitest_repo import ApitestRepo
        return ApitestRepo.count_scenarios(project_id=project_id, **kwargs)

    # 回收站（definition/case/scenario）—— 经已有聚合仓储实现
    def list_trash_by_repo(self, project_id: str = "", limit: int = 100,
                           resource: str = "definition") -> list:
        from app.repositories.apitest_repo import ApitestRepo
        if resource == "definition":
            return ApitestRepo.list_trash_definitions(project_id, limit)
        if resource == "case":
            return ApitestRepo.list_trash_cases(project_id, limit)
        return ApitestRepo.list_trash_scenarios(project_id, limit)

    def count_trash_by_repo(self, project_id: str = "",
                            resource: str = "definition") -> int:
        from app.repositories.apitest_repo import ApitestRepo
        if resource == "definition":
            return ApitestRepo.count_trash_definitions(project_id)
        if resource == "case":
            return ApitestRepo.count_trash_cases(project_id)
        return ApitestRepo.count_trash_scenarios(project_id)

    def batch_op_by_repo(self, ids: list, op: str = "delete",
                         resource: str = "definition", **fields) -> int:
        """批量操作薄门面（delete/restore/purge/update）。"""
        from app.repositories.apitest_repo import ApitestRepo
        if resource == "definition":
            if op == "delete":
                return ApitestRepo.batch_delete_definitions(ids)
            if op == "restore":
                return ApitestRepo.batch_restore_definitions(ids)
            if op == "purge":
                return ApitestRepo.batch_purge_definitions(ids)
            return ApitestRepo.batch_update_definitions(ids, **fields)
        if resource == "case":
            if op == "delete":
                return ApitestRepo.batch_delete_cases(ids)
            if op == "restore":
                return ApitestRepo.batch_restore_cases(ids)
            if op == "purge":
                return ApitestRepo.batch_purge_cases(ids)
            return ApitestRepo.batch_update_cases(ids, **fields)
        if resource == "scenario":
            if op == "delete":
                return ApitestRepo.batch_delete_scenarios(ids)
            if op == "restore":
                return ApitestRepo.batch_restore_scenarios(ids)
            if op == "purge":
                return ApitestRepo.batch_purge_scenarios(ids)
            return ApitestRepo.batch_update_scenarios(ids, **fields)
        return 0

    def purge_by_repo(self, resource_id: str,
                      resource: str = "definition") -> bool:
        from app.repositories.apitest_repo import ApitestRepo
        if resource == "definition":
            return ApitestRepo.purge_definition(resource_id)
        if resource == "case":
            return ApitestRepo.purge_case(resource_id)
        return ApitestRepo.purge_scenario(resource_id)


# 单例门面（进程内复用）
apitest_app_service = ApitestAppService()
apitest_service = apitest_app_service
