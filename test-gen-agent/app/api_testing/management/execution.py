# -*- coding: utf-8 -*-
"""app.api_testing.management.execution 子模块（场景执行，行为不变）。

Repository 下沉说明：
场景编排执行逻辑已下沉到
app.repositories.apitest_repo.ApitestRepo.mgmt_execute_scenario，
本模块退化为兼容门面。
"""

from typing import Optional

from app.repositories.apitest_repo import ApitestRepo


def execute_scenario(scenario_id: str, environment_id: Optional[str] = None) -> dict:
    """执行场景中的各接口用例（委托 ApitestRepo.mgmt_execute_scenario）。"""
    return ApitestRepo.mgmt_execute_scenario(
        scenario_id, environment_id=environment_id)
