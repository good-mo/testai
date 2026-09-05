# -*- coding: utf-8 -*-
"""apittest store submodule: cases_scenarios.

Repository 下沉说明：
接口用例（api_cases）与接口场景（api_scenarios）的纯数据访问 CRUD / 回收站 /
批量操作 SQL 已下沉到 app.repositories.apitest_repo.ApitestRepo（L3 Repository
层），本模块退化为兼容门面，直接委托 ApitestRepo，保证对外行为零回归。
"""
from typing import Any, Dict, List, Optional

from app.repositories.apitest_repo import ApitestRepo


# ── 接口用例 ───────────────────────────────────────────────
def create_api_case(name: str, api_definition_id: str = "", request: dict = None,
                    asserts: list = None, pre_scripts: list = None,
                    post_scripts: list = None, pre_sql: list = None,
                    post_sql: list = None, variables: list = None,
                    logic_controllers: list = None, environment_id: str = "",
                    status: str = "draft", priority: str = "P2",
                    description: str = "", project_id: str = "",
                    method: str = "", path: str = "", **kwargs) -> Dict[str, Any]:
    return ApitestRepo.create_api_case(
        name=name, api_definition_id=api_definition_id, request=request,
        asserts=asserts, pre_scripts=pre_scripts, post_scripts=post_scripts,
        pre_sql=pre_sql, post_sql=post_sql, variables=variables,
        logic_controllers=logic_controllers, environment_id=environment_id,
        status=status, priority=priority, description=description,
        project_id=project_id, method=method, path=path, **kwargs,
    )


def list_api_cases(keyword: str = "", limit: int = 100, offset: int = 0,
                   project_id: str = "", api_definition_id: str = "") -> List[Dict[str, Any]]:
    return ApitestRepo.list_api_cases(
        keyword=keyword, limit=limit, offset=offset, project_id=project_id,
        api_definition_id=api_definition_id,
    )


def count_api_cases(project_id: str = "", api_definition_id: str = "") -> int:
    return ApitestRepo.count_api_cases(
        project_id=project_id, api_definition_id=api_definition_id)


def get_api_case(case_id: str) -> Optional[Dict[str, Any]]:
    return ApitestRepo.get_api_case(case_id)


def update_api_case(case_id: str, **fields) -> Optional[Dict[str, Any]]:
    return ApitestRepo.update_api_case(case_id, **fields)


def delete_api_case(case_id: str) -> bool:
    return ApitestRepo.delete_api_case(case_id)


def list_trash_cases(project_id: str = "", limit: int = 100) -> List[Dict[str, Any]]:
    return ApitestRepo.list_trash_cases(project_id=project_id, limit=limit)


def count_trash_cases(project_id: str = "") -> int:
    return ApitestRepo.count_trash_cases(project_id=project_id)


def restore_case(case_id: str) -> bool:
    return ApitestRepo.restore_case(case_id)


def batch_restore_cases(case_ids: List[str]) -> int:
    return ApitestRepo.batch_restore_cases(case_ids)


def purge_case(case_id: str) -> bool:
    return ApitestRepo.purge_case(case_id)


# ── 接口场景 ───────────────────────────────────────────────
def create_scenario(name: str, steps: list = None, description: str = "",
                    status: str = "draft", environment_id: str = "",
                    project_id: str = "") -> Dict[str, Any]:
    return ApitestRepo.create_scenario(
        name=name, steps=steps, description=description, status=status,
        environment_id=environment_id, project_id=project_id,
    )


def list_scenarios(keyword: str = "", limit: int = 100, offset: int = 0,
                   project_id: str = "") -> List[Dict[str, Any]]:
    return ApitestRepo.list_scenarios(
        keyword=keyword, limit=limit, offset=offset, project_id=project_id)


def count_scenarios(project_id: str = "") -> int:
    return ApitestRepo.count_scenarios(project_id=project_id)


def get_scenario(scenario_id: str) -> Optional[Dict[str, Any]]:
    return ApitestRepo.get_scenario(scenario_id)


def update_scenario(scenario_id: str, **fields) -> Optional[Dict[str, Any]]:
    return ApitestRepo.update_scenario(scenario_id, **fields)


def delete_scenario(scenario_id: str) -> bool:
    return ApitestRepo.delete_scenario(scenario_id)


def list_trash_scenarios(project_id: str = "", limit: int = 100) -> List[Dict[str, Any]]:
    return ApitestRepo.list_trash_scenarios(project_id=project_id, limit=limit)


def count_trash_scenarios(project_id: str = "") -> int:
    return ApitestRepo.count_trash_scenarios(project_id=project_id)


def restore_scenario(scenario_id: str) -> bool:
    return ApitestRepo.restore_scenario(scenario_id)


def batch_restore_scenarios(scenario_ids: List[str]) -> int:
    return ApitestRepo.batch_restore_scenarios(scenario_ids)


def purge_scenario(scenario_id: str) -> bool:
    return ApitestRepo.purge_scenario(scenario_id)
