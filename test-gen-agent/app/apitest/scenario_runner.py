# app/apitest/scenario_runner.py
"""接口场景编排执行引擎（兼容门面）。

Repository 下沉说明：
场景执行逻辑已下沉到 app.repositories.apitest_repo.ApitestRepo（L3 Repository
层），本模块退化为兼容门面，直接委托 ApitestRepo，保证对外行为零回归。
"""
from typing import Any, Dict

from app.repositories.apitest_repo import ApitestRepo


def _resolve_step_request(step: Dict[str, Any], definition: Dict[str, Any],
                          case: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
    """解析步骤的请求对象（委托 ApitestRepo）。"""
    return ApitestRepo._resolve_step_request(step, definition, case, variables)


def run_scenario(scenario: Dict[str, Any], env_override: str = "") -> Dict[str, Any]:
    """执行场景，返回执行结果（委托 ApitestRepo）。"""
    return ApitestRepo.run_scenario(scenario, env_override or "")
