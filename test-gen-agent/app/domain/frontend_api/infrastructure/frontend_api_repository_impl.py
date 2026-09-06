"""前端兼容仓储实现（委托 ApitestRepo / apitest DDD）。

frontend_api 域为 TestPilot 兼容门面，数据访问统一委托
`app.repositories.apitest_repo.ApitestRepo` 的 mgmt_* 兼容入口。
"""
from __future__ import annotations

from typing import Optional

from app.domain.apitest.infrastructure.apitest_store import ApitestRepo


class FrontendApiRepoAdapter:
    """将 FrontendApiRepository 委托给 ApitestRepo（apitest DDD 的存储层）。"""

    # ── 导入 ─────────────────────────────────────────────
    def import_from_postman(self, data: dict) -> dict:
        return ApitestRepo.mgmt_import_from_postman(data)

    def import_from_swagger(self, data: dict) -> dict:
        return ApitestRepo.mgmt_import_from_swagger(data)

    # ── 接口定义 ─────────────────────────────────────────
    def list_api_definitions(self, **kwargs) -> list:
        return ApitestRepo.mgmt_list_api_definitions(**kwargs)

    def create_api_definition(self, **kwargs) -> dict:
        return ApitestRepo.mgmt_create_api_definition(**kwargs)

    def get_api_definition(self, def_id: str) -> Optional[dict]:
        return ApitestRepo.mgmt_get_api_definition(def_id)

    def update_api_definition(self, def_id: str, **kwargs) -> Optional[dict]:
        return ApitestRepo.mgmt_update_api_definition(def_id, **kwargs)

    def delete_api_definition(self, def_id: str, permanent: bool = False) -> bool:
        return ApitestRepo.mgmt_delete_api_definition(def_id, permanent=permanent)

    def list_trash_definitions(self, limit: int = 100) -> list:
        return ApitestRepo.mgmt_list_trash_definitions(limit=limit)

    def restore_definition(self, def_id: str) -> bool:
        return ApitestRepo.mgmt_restore_definition(def_id)

    # ── 接口用例 ─────────────────────────────────────────
    def list_api_test_cases(self, **kwargs) -> list:
        return ApitestRepo.mgmt_list_api_test_cases(**kwargs)

    def create_api_test_case(self, **kwargs) -> dict:
        return ApitestRepo.mgmt_create_api_test_case(**kwargs)

    def get_api_test_case(self, case_id: str) -> Optional[dict]:
        return ApitestRepo.mgmt_get_api_test_case(case_id)

    def update_api_test_case(self, case_id: str, **kwargs) -> Optional[dict]:
        return ApitestRepo.mgmt_update_api_test_case(case_id, **kwargs)

    def delete_api_test_case(self, case_id: str, permanent: bool = False) -> bool:
        return ApitestRepo.mgmt_delete_api_test_case(case_id, permanent=permanent)

    def restore_case(self, case_id: str) -> bool:
        return ApitestRepo.mgmt_restore_case(case_id)

    # ── 场景 ─────────────────────────────────────────────
    def list_scenarios(self, **kwargs) -> list:
        return ApitestRepo.mgmt_list_scenarios(**kwargs)

    def create_scenario(self, **kwargs) -> dict:
        return ApitestRepo.mgmt_create_scenario(**kwargs)

    def execute_scenario(self, scenario_id: str) -> dict:
        return ApitestRepo.mgmt_execute_scenario(scenario_id)

    def get_scenario(self, scenario_id: str) -> Optional[dict]:
        return ApitestRepo.mgmt_get_scenario(scenario_id)

    def update_scenario(self, scenario_id: str, **kwargs) -> Optional[dict]:
        return ApitestRepo.mgmt_update_scenario(scenario_id, **kwargs)

    def delete_scenario(self, scenario_id: str, permanent: bool = False) -> bool:
        return ApitestRepo.mgmt_delete_scenario(scenario_id, permanent=permanent)

    def list_trash_scenarios(self, limit: int = 100) -> list:
        return ApitestRepo.mgmt_list_trash_scenarios(limit=limit)

    def restore_scenario(self, scenario_id: str) -> bool:
        return ApitestRepo.mgmt_restore_scenario(scenario_id)

    # ── Mock ─────────────────────────────────────────────
    def list_mock_services(self, **kwargs) -> list:
        return ApitestRepo.mgmt_list_mock_services(**kwargs)

    def create_mock_service(self, **kwargs) -> dict:
        return ApitestRepo.mgmt_create_mock_service(**kwargs)

    def get_mock_service(self, mock_id: str) -> Optional[dict]:
        return ApitestRepo.mgmt_get_mock_service(mock_id)

    def update_mock_service(self, mock_id: str, **kwargs) -> Optional[dict]:
        return ApitestRepo.mgmt_update_mock_service(mock_id, **kwargs)

    def delete_mock_service(self, mock_id: str, permanent: bool = False) -> bool:
        return ApitestRepo.mgmt_delete_mock_service(mock_id, permanent=permanent)
