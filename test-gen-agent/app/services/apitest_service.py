# app/services/apitest_service.py
"""接口测试业务逻辑层（Phase 3 重构 · 4 层对齐 + DDD 接入）。

迁移状态（A→B→C 渐进式）：
  - 阶段 A：`app/domain/apitest/` DDD 聚合/应用层就绪。
  - 阶段 B/C：定义/用例/场景的对象级 CRUD（create/get/update/delete/restore）
    与 列表/回收站/批量删除-恢复/版本 等旁路方法已收敛为对
    `apitest_web` → `apitest_app_service`（DDD 门面）的**薄委托**，
    Service 仅做方法签名兼容与转发。

  已收敛为 DDD 薄门面委托的旁路组（经 `apitest_app_service` 门面）：
  - module_tree / execution（含 execution_logs）/ followers / operation_logs /
    schedules —— 已委托 apitest_app_service 门面。
  - mocks（ApiMock 聚合）/ environments / env_groups / global_params ——
    经 `apitest_web` → `apitest_app_service` 门面。
  - 回收站 purge（物理删除）/ batch_purge / batch_update / rollback_definition
    与 module stats（按模块统计/模块数）—— 经 `apitest_web` → `apitest_app_service` 门面。

  仍属"双轨并存"的旁路（保留直连 ApitestRepo）：
  - dashboard_stats / mgmt_* 前端兼容通道等尚未从 service 转发到 DDD 门面。
"""
from typing import Optional

from app.domain.apitest.application import apitest_app_service, apitest_web
from app.repositories.apitest_repo import ApitestRepo


class ApitestService:
    """接口测试管理服务。"""

    # ── 统计 ─────────────────────────────────────────────
    def dashboard_stats(self) -> dict:
        return ApitestRepo.dashboard_stats()

    # ── 接口定义 CRUD ─────────────────────────────────────
    def list_definitions(self, keyword: str = "", limit: int = 100, offset: int = 0,
                         project_id: str = "", include_all_versions: bool = False,
                         include_latest_only: bool = True,
                         protocols: Optional[list] = None,
                         module_ids: Optional[list] = None) -> list:
        # 阶段 C：薄门面转发 → apitest_web → apitest_app_service → DDD 聚合仓储
        return apitest_web.list_definitions(
            keyword=keyword, limit=limit, offset=offset, project_id=project_id,
            include_latest_only=include_latest_only,
            protocols=protocols, module_ids=module_ids,
        )

    def count_definitions(self, project_id: str = "", **kwargs) -> int:
        # 阶段 C：经 apitest_web 薄门面 → DDD list total
        return apitest_web.count_definitions(project_id=project_id, **kwargs)

    def count_definitions_by_module(self, protocols=None) -> dict:
        """统计每个模块下的接口定义数量，返回 {module_id: count}。"""
        # 阶段 C：薄门面转发 DDD
        return apitest_web.count_definitions_by_module(protocols=protocols)

    def count_definitions_total(self, protocols=None) -> int:
        """统计接口定义总数（可选按协议过滤）。"""
        # 阶段 C：薄门面转发 DDD
        return apitest_web.count_definitions_total(protocols=protocols)

    def count_cases_for_definition(self, definition_id: str) -> int:
        """统计某接口定义下的接口用例数。"""
        # 阶段 C：薄门面转发 DDD
        return apitest_web.count_cases_for_definition(definition_id)

    def list_schedules(self, keyword: str = "") -> list:
        """查询真实调度任务列表。"""
        return apitest_app_service.list_schedules(keyword=keyword)

    def get_definition(self, definition_id: str) -> Optional[dict]:
        return apitest_web.get_definition(definition_id)

    def create_definition(self, **kwargs) -> dict:
        # 阶段 C：业务规则下沉 DDD 聚合，此处仅做门面转发。
        return apitest_web.create_definition(kwargs) or {}

    def update_definition(self, definition_id: str, **kwargs) -> Optional[dict]:
        return apitest_web.update_definition(definition_id, kwargs)

    def delete_definition(self, definition_id: str) -> bool:
        return apitest_web.delete_definition(definition_id)

    # ── 接口定义版本 ─────────────────────────────────────
    def list_definition_versions(self, ref_id: str) -> list:
        # 阶段 C：薄门面转发 DDD
        return apitest_web.list_definition_versions(ref_id)

    def create_definition_version(self, definition_id: str,
                                  version: str = "") -> Optional[dict]:
        # 阶段 C：薄门面转发 DDD（CreateVersionCommand）
        return apitest_web.create_definition_version(definition_id, version)

    def rollback_definition(self, definition_id: str,
                            version_id: str) -> Optional[dict]:
        # 阶段 C：薄门面转发 DDD
        return apitest_web.rollback_definition(definition_id, version_id)

    # ── 接口用例 CRUD ────────────────────────────────────
    def list_api_cases(self, keyword: str = "", limit: int = 100,
                       offset: int = 0, project_id: str = "", **kwargs) -> list:
        # 阶段 C：薄门面转发 → apitest_web → apitest_app_service
        api_def_id = kwargs.get("api_definition_id", "")
        return apitest_web.list_api_cases(
            keyword=keyword, limit=limit, offset=offset,
            project_id=project_id, api_definition_id=api_def_id,
        )

    def count_api_cases(self, project_id: str = "", **kwargs) -> int:
        # 阶段 C：经 apitest_web 薄门面 → DDD list total
        return apitest_web.count_api_cases(project_id=project_id, **kwargs)

    def get_api_case(self, case_id: str) -> Optional[dict]:
        return apitest_web.get_api_case(case_id)

    def create_api_case(self, **kwargs) -> dict:
        return apitest_web.create_api_case(kwargs) or {}

    def update_api_case(self, case_id: str, **kwargs) -> Optional[dict]:
        return apitest_web.update_api_case(case_id, kwargs)

    def delete_api_case(self, case_id: str) -> bool:
        return apitest_web.delete_api_case(case_id)

    # ── 场景编排 ─────────────────────────────────────────
    def list_scenarios(self, keyword: str = "", limit: int = 100,
                       offset: int = 0, project_id: str = "", **kwargs) -> list:
        # 阶段 C：薄门面转发 → apitest_web → apitest_app_service
        return apitest_web.list_scenarios(
            keyword=keyword, limit=limit, offset=offset,
            project_id=project_id,
        )

    def count_scenarios(self, project_id: str = "", **kwargs) -> int:
        # 阶段 C：经 apitest_web 薄门面 → DDD list total
        return apitest_web.count_scenarios(project_id=project_id, **kwargs)

    def get_scenario(self, scenario_id: str) -> Optional[dict]:
        return apitest_web.get_scenario(scenario_id)

    def create_scenario(self, **kwargs) -> dict:
        return apitest_web.create_scenario(kwargs) or {}

    def update_scenario(self, scenario_id: str, **kwargs) -> Optional[dict]:
        return apitest_web.update_scenario(scenario_id, kwargs)

    def delete_scenario(self, scenario_id: str) -> bool:
        return apitest_web.delete_scenario(scenario_id)

    # ── Mock 服务 ────────────────────────────────────────
    def list_mocks(self, keyword: str = "", limit: int = 100,
                   offset: int = 0, project_id: str = "", **kwargs) -> list:
        # 阶段 C：薄门面转发 DDD（ApiMock 聚合）→ apitest_web
        result = apitest_web.list_mocks({
            "keyword": keyword, "limit": limit, "offset": offset,
            "project_id": project_id,
        })
        return result.get("list", [])

    def count_mocks(self, project_id: str = "", **kwargs) -> int:
        return apitest_web.count_mocks(project_id=project_id, **kwargs)

    def get_mock(self, mock_id: str) -> Optional[dict]:
        return apitest_web.get_mock(mock_id)

    def create_mock(self, **kwargs) -> dict:
        return apitest_web.create_mock(dict(kwargs)) or {}

    def update_mock(self, mock_id: str, **kwargs) -> Optional[dict]:
        return apitest_web.update_mock(mock_id, dict(kwargs))

    def delete_mock(self, mock_id: str) -> bool:
        return apitest_web.delete_mock(mock_id)

    def run_mock_request(self, method: str, path: str, base_path: str = "",
                         query_params: dict = None, request_body: str = "") -> Optional[dict]:
        return apitest_web.run_mock_request(
            method=method, path=path, base_path=base_path,
            query_params=query_params, request_body=request_body,
        )

    # ── 环境（apitest 侧 api_environments，非 Docker environment 域）────
    def list_environments(self, keyword: str = "", limit: int = 100,
                          project_id: str = "", **kwargs) -> list:
        # 阶段 C：薄门面转发 DDD（route 不建模，经 app_service 收口）
        return apitest_app_service.list_environments(project_id=project_id, **kwargs)

    def count_environments(self, project_id: str = "", **kwargs) -> int:
        return apitest_app_service.count_environments(project_id=project_id, **kwargs)

    def get_environment(self, env_id: str) -> Optional[dict]:
        return apitest_app_service.get_environment(env_id)

    def create_environment(self, **kwargs) -> dict:
        return apitest_app_service.create_environment(**kwargs)

    def update_environment(self, env_id: str, **kwargs) -> Optional[dict]:
        return apitest_app_service.update_environment(env_id, **kwargs)

    def delete_environment(self, env_id: str) -> bool:
        return apitest_app_service.delete_environment(env_id)

    # ── 环境组 ───────────────────────────────────────────
    def list_env_groups(self, project_id: str = "", keyword: str = "") -> list:
        # 阶段 C：薄门面转发 DDD（route 不建模）
        return apitest_app_service.list_env_groups(project_id=project_id, keyword=keyword)

    def get_env_group(self, group_id: str) -> Optional[dict]:
        return apitest_app_service.get_env_group(group_id)

    def create_env_group(self, name: str = "", project_id: str = "",
                         description: str = "", env_group_project: list = None,
                         **kwargs) -> dict:
        return apitest_app_service.create_env_group(
            name=name, project_id=project_id, description=description,
            env_group_project=env_group_project, **kwargs,
        )

    def update_env_group(self, group_id: str, **kwargs) -> Optional[dict]:
        return apitest_app_service.update_env_group(group_id, **kwargs)

    def delete_env_group(self, group_id: str) -> bool:
        return apitest_app_service.delete_env_group(group_id)

    def export_environment(self, env_id: str) -> Optional[dict]:
        return apitest_app_service.export_environment(env_id)

    def import_environment(self, data: dict, project_id: str = "") -> dict:
        return apitest_app_service.import_environment(data, project_id=project_id)

    # ── 全局参数 ────────────────────────────────────────
    def get_global_params(self, project_id: str) -> Optional[dict]:
        return apitest_app_service.get_global_params(project_id)

    def save_global_params(self, project_id: str, headers: list = None,
                           common_variables: list = None) -> dict:
        return apitest_app_service.save_global_params(
            project_id, headers=headers, common_variables=common_variables,
        )

    def delete_global_params(self, project_id: str) -> bool:
        return apitest_app_service.delete_global_params(project_id)

    def delete_global_param_by_id(self, param_id: str) -> bool:
        """按记录 id 删除全局参数记录（前端兼容）。"""
        return apitest_app_service.delete_global_param_by_id(param_id)

    # ── 环境格式转换辅助 ─────────────────────────────────
    def env_detail_to_frontend(self, env: dict) -> Optional[dict]:
        return apitest_app_service.env_detail_to_frontend(env)

    # ── 回收站 ───────────────────────────────────────────
    def list_trash_definitions(self, project_id: str = "", limit: int = 100) -> list:
        # 阶段 C：薄门面转发 DDD
        return apitest_web.list_trash_definitions(project_id, limit)

    def restore_definition(self, definition_id: str) -> bool:
        return apitest_web.restore_definition(definition_id)

    def purge_definition(self, definition_id: str) -> bool:
        # 阶段 C：薄门面转发 DDD
        return apitest_web.purge_definition(definition_id)

    def list_trash_cases(self, project_id: str = "", limit: int = 100) -> list:
        # 阶段 C：薄门面转发 DDD
        return apitest_web.list_trash_cases(project_id, limit)

    def restore_case(self, case_id: str) -> bool:
        return apitest_web.restore_api_case(case_id)

    def purge_case(self, case_id: str) -> bool:
        # 阶段 C：薄门面转发 DDD
        return apitest_web.purge_case(case_id)

    def list_trash_scenarios(self, project_id: str = "", limit: int = 100) -> list:
        # 阶段 C：薄门面转发 DDD
        return apitest_web.list_trash_scenarios(project_id, limit)

    def restore_scenario(self, scenario_id: str) -> bool:
        return apitest_web.restore_scenario(scenario_id)

    def purge_scenario(self, scenario_id: str) -> bool:
        # 阶段 C：薄门面转发 DDD
        return apitest_web.purge_scenario(scenario_id)

    def list_trash_mocks(self, project_id: str = "", limit: int = 100) -> list:
        # 阶段 C：薄门面转发 DDD（ApiMock 聚合回收站）
        result = apitest_web.list_trash_mocks(project_id=project_id, limit=limit)
        return result.get("list", [])

    def count_trash_definitions(self, project_id: str = "") -> int:
        # 阶段 C：薄门面转发 → DDD list_trash total
        return apitest_web.count_trash_definitions(project_id)

    def count_trash_cases(self, project_id: str = "") -> int:
        # 阶段 C：薄门面转发 → DDD list_trash total
        return apitest_web.count_trash_cases(project_id)

    def count_trash_scenarios(self, project_id: str = "") -> int:
        # 阶段 C：薄门面转发 → DDD list_trash total
        return apitest_web.count_trash_scenarios(project_id)

    def count_trash_mocks(self, project_id: str = "") -> int:
        return apitest_web.count_trash_mocks(project_id=project_id)

    def restore_mock(self, mock_id: str) -> bool:
        return apitest_web.restore_mock(mock_id)

    def purge_mock(self, mock_id: str) -> bool:
        # 阶段 C：薄门面转发 DDD
        return apitest_web.purge_mock(mock_id)

    # ── 批量操作 ─────────────────────────────────────────
    def batch_delete_definitions(self, ids: list) -> int:
        # 阶段 C：逐条经 apitest_web → DDD 门面删除
        return apitest_web.batch_delete_definitions(ids)

    def batch_restore_definitions(self, ids: list) -> int:
        # 阶段 C：逐条经 apitest_web → DDD 门面恢复
        return apitest_web.batch_restore_definitions(ids)

    def batch_purge_definitions(self, ids: list) -> int:
        # 阶段 C：薄门面转发 DDD
        return apitest_web.batch_purge_definitions(ids)

    def batch_update_definitions(self, ids: list, **fields) -> int:
        # 阶段 C：薄门面转发 DDD
        return apitest_web.batch_update_definitions(ids, **fields)

    def batch_delete_cases(self, ids: list) -> int:
        # 阶段 C：逐条经 apitest_web → DDD 门面删除
        return apitest_web.batch_delete_cases(ids)

    def batch_restore_cases(self, ids: list) -> int:
        # 阶段 C：逐条经 apitest_web → DDD 门面恢复
        return apitest_web.batch_restore_cases(ids)

    def batch_purge_cases(self, ids: list) -> int:
        # 阶段 C：薄门面转发 DDD
        return apitest_web.batch_purge_cases(ids)

    def batch_update_cases(self, ids: list, **fields) -> int:
        # 阶段 C：薄门面转发 DDD
        return apitest_web.batch_update_cases(ids, **fields)

    def batch_delete_scenarios(self, ids: list) -> int:
        # 阶段 C：逐条经 apitest_web → DDD 门面删除
        return apitest_web.batch_delete_scenarios(ids)

    def batch_restore_scenarios(self, ids: list) -> int:
        # 阶段 C：逐条经 apitest_web → DDD 门面恢复
        return apitest_web.batch_restore_scenarios(ids)

    def batch_purge_scenarios(self, ids: list) -> int:
        # 阶段 C：薄门面转发 DDD
        return apitest_web.batch_purge_scenarios(ids)

    def batch_update_scenarios(self, ids: list, **fields) -> int:
        # 阶段 C：薄门面转发 DDD
        return apitest_web.batch_update_scenarios(ids, **fields)

    def batch_delete_mocks(self, ids: list) -> int:
        # 阶段 C：逐条经 apitest_web → DDD Mock 聚合删除
        return apitest_web.batch_delete_mocks(ids)

    def batch_restore_mocks(self, ids: list) -> int:
        return apitest_web.batch_restore_mocks(ids)

    def batch_purge_mocks(self, ids: list) -> int:
        # 阶段 C：薄门面转发 DDD
        return apitest_web.batch_purge_mocks(ids)

    # ── 模块树 ───────────────────────────────────────────
    def build_module_tree(self, module_type: str = "api", include_api: bool = True,
                          project_id: str = "", **kwargs) -> list:
        return apitest_app_service.build_module_tree(
            module_type, include_api=include_api, project_id=project_id,
        )

    def add_module(self, scope: str = "definition", name: str = "",
                   parent_id: str = "root", project_id: str = "",
                   module_type: str = "", **kwargs) -> dict:
        # module_store.add_module 的签名是 (scope, name, parent_id, project_id)
        # 前端传的 scope 即 module_store 期望的 scope
        mt = scope if scope else module_type
        return apitest_app_service.add_module(
            mt, name=name, parent_id=parent_id, project_id=project_id,
        )

    def update_module(self, module_id: str, name: str = "", **kwargs) -> bool:
        """更新模块名称。module_store 仅支持更新 name 字段。"""
        return apitest_app_service.update_module(
            module_id, name=name or kwargs.get("name", ""),
        )

    def delete_module(self, module_id: str) -> bool:
        return apitest_app_service.delete_module(module_id)

    def get_module(self, module_id: str) -> Optional[dict]:
        return apitest_app_service.get_module(module_id)

    def list_modules(self, scope: str = "definition", project_id: str = "") -> list:
        """列出指定作用域下全部模块。"""
        return apitest_app_service.list_modules(scope, project_id=project_id)

    def move_module(self, drag_node_id: str, drop_node_id: str,
                    drop_position: int = 0) -> bool:
        """移动模块到指定位置。"""
        return apitest_app_service.move_module(
            drag_node_id, drop_node_id, drop_position=drop_position,
        )

    def count_modules(self, module_type: str = "api") -> int:
        # module stats / module_tree 统一收敛：经 DDD 薄门面转发
        return apitest_app_service.count_modules(module_type)

    # ── 执行与调试 ───────────────────────────────────────
    def run_case(self, case_id: str, environment_id: str = "") -> dict:
        return apitest_app_service.run_case(case_id, environment_id=environment_id)

    def debug_api_call(self, **kwargs) -> dict:
        return apitest_app_service.debug_api_call(**kwargs)

    def run_scenario(self, scenario: dict, environment_id: str = "") -> dict:
        """执行接口场景。"""
        return apitest_app_service.run_scenario(scenario, environment_id)

    def import_content(self, content: str, fmt: str = "auto",
                       project_id: str = "") -> dict:
        """导入接口文档内容。"""
        return apitest_app_service.import_content(content, fmt, project_id)

    def get_assert_types(self) -> dict:
        """运行时断言类型字典（meta 接口）。"""
        return apitest_app_service.get_assert_types()

    # ── 关注/日志 ────────────────────────────────────────
    def list_followers(self, resource_id: str, resource_type: str = "") -> list:
        return apitest_app_service.list_followers(resource_id, resource_type)

    def follow_resource(self, resource_id: str, resource_type: str = "",
                        user_id: str = "") -> bool:
        return apitest_app_service.follow_resource(resource_id, resource_type, user_id)

    def unfollow_resource(self, resource_id: str, resource_type: str = "",
                          user_id: str = "") -> bool:
        return apitest_app_service.unfollow_resource(resource_id, resource_type, user_id)

    def toggle_follow(self, resource_id: str, resource_type: str = "",
                      user_id: str = "") -> bool:
        return apitest_app_service.toggle_follow(resource_id, resource_type, user_id)

    def is_followed(self, resource_id: str, resource_type: str = "",
                    user_id: str = "") -> bool:
        return apitest_app_service.is_followed(resource_id, resource_type, user_id)

    def list_operation_logs(self, resource_type: str = "", resource_id: str = "",
                            project_id: str = "", limit: int = 100,
                            offset: int = 0, **kwargs) -> list:
        return apitest_app_service.list_operation_logs(
            resource_type=resource_type, resource_id=resource_id,
            project_id=project_id, limit=limit, offset=offset, **kwargs,
        )

    def count_operation_logs(self, resource_type: str = "",
                             resource_id: str = "", project_id: str = "") -> int:
        return apitest_app_service.count_operation_logs(
            resource_type=resource_type, resource_id=resource_id,
            project_id=project_id,
        )

    def clear_operation_logs(self, days: int = 30) -> int:
        """清理 days 天之前的操作日志，返回删除条数。

        路由 DELETE /api/apitest/logs?days=N 会传入 days，
        此前这里不接参数，导致调用直接 500（takes 1 positional
        argument but 2 were given）。
        """
        return apitest_app_service.clear_operation_logs(days=days)

    # ── 测试执行记录（执行落库查询）────────────────────────
    def list_execution_logs(self, exec_type: str = "", target_id: str = "",
                            limit: int = 100, offset: int = 0,
                            keyword: str = "") -> list:
        """查询测试执行记录。"""
        return apitest_app_service.list_execution_logs(
            exec_type, target_id, limit, offset=offset, keyword=keyword)

    def count_execution_logs(self, exec_type: str = "",
                             target_id: str = "", keyword: str = "") -> int:
        """统计测试执行记录。"""
        return apitest_app_service.count_execution_logs(exec_type, target_id, keyword=keyword)

    def clear_execution_logs(self, exec_type: str = "") -> int:
        """清空测试执行记录。"""
        return apitest_app_service.clear_execution_logs(exec_type)

    # ── 前端兼容 mgmt 通道（统一经 ApitestRepo 唯一出口）────────────────
    def mgmt_list_trash_cases(self, limit: int = 100) -> list:
        """回收站-接口用例列表（api_test_cases 表，前端兼容）。"""
        return ApitestRepo.mgmt_list_trash_cases(limit=limit)

    def mgmt_restore_case(self, case_id: str) -> bool:
        """回收站-接口用例恢复（api_test_cases 表，前端兼容）。"""
        return ApitestRepo.mgmt_restore_case(case_id)

    def mgmt_delete_api_test_case(self, case_id: str,
                                  permanent: bool = False) -> bool:
        """回收站-接口用例彻底删除（api_test_cases 表，前端兼容）。"""
        return ApitestRepo.mgmt_delete_api_test_case(case_id, permanent=permanent)


apitest_service = ApitestService()
