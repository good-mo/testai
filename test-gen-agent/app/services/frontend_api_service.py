# app/services/frontend_api_service.py
"""前端兼容 API 测试数据业务层（frontend_api 域 DDD 接入 · 阶段 C 薄门面）。

前端兼容（TestPilot 风格接口定义/用例/场景/Mock/导入）已收敛到 frontend_api
域 DDD 应用服务 `frontend_api_app_service`（见 `app/domain/frontend_api/`，
聚合根 `ApiImport` 承载导入来源/统计语义）。本 Service 收敛为对 DDD 应用门面
的**薄委托门面**，仅保留既有方法签名以兼容 `app/routers/frontend.py` /
`app/api_testing/management/` 等调用方，返回结构与重构前一致，对外 API
零回归、可回滚。

> 推荐调用方直接使用 `frontend_api_app_service`；本类仅作过渡兼容层保留。
"""
from __future__ import annotations

from typing import Optional

from app.domain.frontend_api.application.dto import (
    ImportFromPostmanCommand,
    ImportFromSwaggerCommand,
)
from app.domain.frontend_api.application.frontend_api_app_service import (
    frontend_api_app_service as _ddd,
)


class FrontendApiService:
    """前端兼容接口测试数据服务（DDD 薄门面）。"""

    # ── 导入 ─────────────────────────────────────────────
    def import_from_postman(self, data: dict) -> dict:
        return _ddd.import_postman(ImportFromPostmanCommand(data=data))

    def import_from_swagger(self, data: dict) -> dict:
        return _ddd.import_swagger(ImportFromSwaggerCommand(data=data))

    # ── 接口定义 ─────────────────────────────────────────
    def list_api_definitions(self, search: str = "", method: str = "",
                             protocol: str = "", limit: int = 100,
                             project_id: str = "") -> list:
        return _ddd.list_api_definitions(
            search=search, method=method, protocol=protocol,
            limit=limit, project_id=project_id,
        )

    def create_api_definition(self, **kwargs) -> dict:
        return _ddd.create_api_definition(**kwargs)

    def get_api_definition(self, def_id: str) -> Optional[dict]:
        return _ddd.get_api_definition(def_id)

    def update_api_definition(self, def_id: str, **kwargs) -> Optional[dict]:
        return _ddd.update_api_definition(def_id, **kwargs)

    def delete_api_definition(self, def_id: str, permanent: bool = False) -> bool:
        return _ddd.delete_api_definition(def_id, permanent=permanent)

    def list_trash_definitions(self, limit: int = 100) -> list:
        return _ddd.list_trash_definitions(limit=limit)

    def restore_definition(self, def_id: str) -> bool:
        return _ddd.restore_definition(def_id)

    # ── 接口用例 ─────────────────────────────────────────
    def list_api_test_cases(self, search: str = "", definition_id: str = "",
                            environment_id: str = "", enabled=None,
                            limit: int = 100, project_id: str = "") -> list:
        return _ddd.list_api_test_cases(
            search=search, definition_id=definition_id,
            environment_id=environment_id, enabled=enabled,
            limit=limit, project_id=project_id,
        )

    def create_api_test_case(self, **kwargs) -> dict:
        return _ddd.create_api_test_case(**kwargs)

    def get_api_test_case(self, case_id: str) -> Optional[dict]:
        return _ddd.get_api_test_case(case_id)

    def update_api_test_case(self, case_id: str, **kwargs) -> Optional[dict]:
        return _ddd.update_api_test_case(case_id, **kwargs)

    def delete_api_test_case(self, case_id: str, permanent: bool = False) -> bool:
        return _ddd.delete_api_test_case(case_id, permanent=permanent)

    def restore_case(self, case_id: str) -> bool:
        return _ddd.restore_case(case_id)

    # ── 场景 ─────────────────────────────────────────────
    def list_scenarios(self, limit: int = 100) -> list:
        return _ddd.list_scenarios(limit=limit)

    def create_scenario(self, **kwargs) -> dict:
        return _ddd.create_scenario(**kwargs)

    def execute_scenario(self, scenario_id: str) -> dict:
        return _ddd.execute_scenario(scenario_id)

    def get_scenario(self, scenario_id: str) -> Optional[dict]:
        return _ddd.get_scenario(scenario_id)

    def update_scenario(self, scenario_id: str, **kwargs) -> Optional[dict]:
        return _ddd.update_scenario(scenario_id, **kwargs)

    def delete_scenario(self, scenario_id: str, permanent: bool = False) -> bool:
        return _ddd.delete_scenario(scenario_id, permanent=permanent)

    def list_trash_scenarios(self, limit: int = 100) -> list:
        return _ddd.list_trash_scenarios(limit=limit)

    def restore_scenario(self, scenario_id: str) -> bool:
        return _ddd.restore_scenario(scenario_id)

    # ── Mock ─────────────────────────────────────────────
    def list_mock_services(self, limit: int = 100) -> list:
        return _ddd.list_mock_services(limit=limit)

    def create_mock_service(self, **kwargs) -> dict:
        return _ddd.create_mock_service(**kwargs)

    def get_mock_service(self, mock_id: str) -> Optional[dict]:
        return _ddd.get_mock_service(mock_id)

    def update_mock_service(self, mock_id: str, **kwargs) -> Optional[dict]:
        return _ddd.update_mock_service(mock_id, **kwargs)

    def delete_mock_service(self, mock_id: str, permanent: bool = False) -> bool:
        return _ddd.delete_mock_service(mock_id, permanent=permanent)


frontend_api_service = FrontendApiService()
