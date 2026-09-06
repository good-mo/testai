"""前端兼容应用服务（委托 apitest DDD 仓储）。

frontend_api 域为 TestPilot 前端兼容门面：import 操作以 `ApiImport`
聚合承载来源与导入统计语义，CRUD/查询操作薄委托 infrastructure
`FrontendApiRepoAdapter` 对接 ApitestRepo。
"""
from __future__ import annotations

from typing import Optional

from app.domain.frontend_api.application.dto import (
    ImportFromPostmanCommand,
    ImportFromSwaggerCommand,
)
from app.domain.frontend_api.domain.entities.api_import import (
    ApiImport,
    SOURCE_POSTMAN,
    SOURCE_SWAGGER,
)
from app.domain.frontend_api.infrastructure.frontend_api_repository_impl import (
    FrontendApiRepoAdapter,
)


class FrontendApiAppService:
    """前端兼容用例编排服务。"""

    def __init__(self, repo=None):
        self._repo = repo or FrontendApiRepoAdapter()

    # ── 导入（以 ApiImport 聚合承载来源/统计语义）──────────
    def import_postman(self, cmd: ImportFromPostmanCommand) -> dict:
        job = ApiImport(source=SOURCE_POSTMAN, _created=True)
        result = self._repo.import_from_postman(cmd.data)
        if result:
            job.mark_completed(
                imported=result.get("imported", 0),
                failed=result.get("failed", 0),
            )
        return result

    def import_swagger(self, cmd: ImportFromSwaggerCommand) -> dict:
        job = ApiImport(source=SOURCE_SWAGGER, _created=True)
        result = self._repo.import_from_swagger(cmd.data)
        if result:
            job.mark_completed(
                imported=result.get("imported", 0),
                failed=result.get("failed", 0),
            )
        return result

    # ── 接口定义 ─────────────────────────────────────────
    def list_api_definitions(self, **kwargs) -> list:
        return self._repo.list_api_definitions(**kwargs)

    def create_api_definition(self, **kwargs) -> dict:
        return self._repo.create_api_definition(**kwargs)

    def get_api_definition(self, def_id: str) -> Optional[dict]:
        return self._repo.get_api_definition(def_id)

    def update_api_definition(self, def_id: str, **kwargs) -> Optional[dict]:
        return self._repo.update_api_definition(def_id, **kwargs)

    def delete_api_definition(self, def_id: str, permanent: bool = False) -> bool:
        return self._repo.delete_api_definition(def_id, permanent=permanent)

    def list_trash_definitions(self, limit: int = 100) -> list:
        return self._repo.list_trash_definitions(limit=limit)

    def restore_definition(self, def_id: str) -> bool:
        return self._repo.restore_definition(def_id)

    # ── 接口用例 ─────────────────────────────────────────
    def list_api_test_cases(self, **kwargs) -> list:
        return self._repo.list_api_test_cases(**kwargs)

    def create_api_test_case(self, **kwargs) -> dict:
        return self._repo.create_api_test_case(**kwargs)

    def get_api_test_case(self, case_id: str) -> Optional[dict]:
        return self._repo.get_api_test_case(case_id)

    def update_api_test_case(self, case_id: str, **kwargs) -> Optional[dict]:
        return self._repo.update_api_test_case(case_id, **kwargs)

    def delete_api_test_case(self, case_id: str, permanent: bool = False) -> bool:
        return self._repo.delete_api_test_case(case_id, permanent=permanent)

    def restore_case(self, case_id: str) -> bool:
        return self._repo.restore_case(case_id)

    # ── 场景 ─────────────────────────────────────────────
    def list_scenarios(self, **kwargs) -> list:
        return self._repo.list_scenarios(**kwargs)

    def create_scenario(self, **kwargs) -> dict:
        return self._repo.create_scenario(**kwargs)

    def execute_scenario(self, scenario_id: str) -> dict:
        return self._repo.execute_scenario(scenario_id)

    def get_scenario(self, scenario_id: str) -> Optional[dict]:
        return self._repo.get_scenario(scenario_id)

    def update_scenario(self, scenario_id: str, **kwargs) -> Optional[dict]:
        return self._repo.update_scenario(scenario_id, **kwargs)

    def delete_scenario(self, scenario_id: str, permanent: bool = False) -> bool:
        return self._repo.delete_scenario(scenario_id, permanent=permanent)

    def list_trash_scenarios(self, limit: int = 100) -> list:
        return self._repo.list_trash_scenarios(limit=limit)

    def restore_scenario(self, scenario_id: str) -> bool:
        return self._repo.restore_scenario(scenario_id)

    # ── Mock ─────────────────────────────────────────────
    def list_mock_services(self, **kwargs) -> list:
        return self._repo.list_mock_services(**kwargs)

    def create_mock_service(self, **kwargs) -> dict:
        return self._repo.create_mock_service(**kwargs)

    def get_mock_service(self, mock_id: str) -> Optional[dict]:
        return self._repo.get_mock_service(mock_id)

    def update_mock_service(self, mock_id: str, **kwargs) -> Optional[dict]:
        return self._repo.update_mock_service(mock_id, **kwargs)

    def delete_mock_service(self, mock_id: str, permanent: bool = False) -> bool:
        return self._repo.delete_mock_service(mock_id, permanent=permanent)


frontend_api_app_service = FrontendApiAppService()
frontend_api_service = frontend_api_app_service
