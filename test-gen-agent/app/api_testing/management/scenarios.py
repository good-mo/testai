# -*- coding: utf-8 -*-
"""app.api_testing.management.scenarios 子模块（场景编排，行为不变）。

Repository 下沉说明：
V1 前端兼容层场景（api_scenarios 表）的纯数据访问 CRUD SQL 已下沉到
app.repositories.apitest_repo.ApitestRepo，本模块退化为兼容门面。
"""
from typing import List, Optional

from app.repositories.apitest_repo import ApitestRepo


def create_scenario(
    name: str,
    description: str = "",
    steps: Optional[list] = None,
    environment_id: Optional[str] = None,
    project_id: str = "",
) -> dict:
    return ApitestRepo.mgmt_create_scenario(
        name=name, description=description, steps=steps,
        environment_id=environment_id, project_id=project_id,
    )


def get_scenario(sc_id: str) -> Optional[dict]:
    return ApitestRepo.mgmt_get_scenario(sc_id)


def list_scenarios(limit: int = 100) -> List[dict]:
    return ApitestRepo.mgmt_list_scenarios(limit=limit)


def update_scenario(sc_id: str, **kwargs) -> Optional[dict]:
    return ApitestRepo.mgmt_update_scenario(sc_id, **kwargs)


def delete_scenario(sc_id: str, permanent: bool = False) -> bool:
    return ApitestRepo.mgmt_delete_scenario(sc_id, permanent=permanent)


def list_trash_scenarios(limit: int = 100) -> List[dict]:
    return ApitestRepo.mgmt_list_trash_scenarios(limit=limit)


def restore_scenario(sc_id: str) -> bool:
    return ApitestRepo.mgmt_restore_scenario(sc_id)
