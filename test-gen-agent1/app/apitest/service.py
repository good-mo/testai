# app/apitest/service.py
"""接口测试 API 服务层（兼容门面）。

Repository 下沉说明：
执行与统计逻辑（dashboard_stats / run_mock_request / run_case）已下沉到
app.repositories.apitest_repo.ApitestRepo（L3 Repository 层），本模块退化为
兼容门面，直接委托 ApitestRepo，保证对外行为零回归。
"""
from typing import Any, Dict, Optional

from app.repositories.apitest_repo import ApitestRepo


def dashboard_stats() -> Dict[str, Any]:
    """接口测试模块仪表盘统计（委托 ApitestRepo）。"""
    return ApitestRepo.dashboard_stats()


def _match_path_with_wildcard(mock_path: str, req_path: str) -> bool:
    """通配路径匹配（兼容导出，委托 ApitestRepo）。"""
    return ApitestRepo._mock_path_match(mock_path, req_path)


def run_mock_request(method: str, path: str, base_path: str = "",
                     query_params: dict = None, request_body: str = "") -> Optional[Dict[str, Any]]:
    """根据请求方法+路径匹配启用的 Mock，返回响应（委托 ApitestRepo）。"""
    return ApitestRepo.run_mock_request(
        method=method, path=path, base_path=base_path,
        query_params=query_params, request_body=request_body,
    )


def run_case(case_id: str, environment_id: str = "") -> Dict[str, Any]:
    """单独执行一个接口用例（委托 ApitestRepo）。"""
    return ApitestRepo.run_case(case_id, environment_id=environment_id)
