# -*- coding: utf-8 -*-
"""app.api_testing.management.debug 子模块（接口调试与调试日志，行为不变）。

Repository 下沉说明：
调试执行请求逻辑与执行记录写入已下沉到
app.repositories.apitest_repo.ApitestRepo（L3 Repository 层），本模块退化为
兼容门面，直接委托 ApitestRepo，保证对外行为零回归。
"""

from typing import List, Optional

from app.repositories.apitest_repo import ApitestRepo


def debug_api_call(
    method: str = "GET",
    url: str = "",
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    body: str = "",
    body_type: str = "json",
    timeout: int = 30,
) -> dict:
    """执行接口调试请求（委托 ApitestRepo）。"""
    return ApitestRepo.debug_api_call(
        method=method, url=url, headers=headers,
        params=params, body=body, body_type=body_type, timeout=timeout,
    )


def list_debug_logs(limit: int = 100) -> List[dict]:
    """列出接口调试执行记录（来自统一结果流水 api_execution_logs）。"""
    logs = ApitestRepo.list_execution_logs(
        exec_type="debug", limit=limit, offset=0,
    )
    for d in logs:
        # 回填原 api_debug_logs 语义字段，保持调用方兼容
        d['case_id'] = d.get('target_id', '')
        d['path'] = d.get('url', '')
        d['success'] = d.get('passed', 0)
    return logs


def clear_debug_logs() -> int:
    """清空调试执行记录。"""
    return ApitestRepo.clear_execution_logs(exec_type="debug")


def _log_debug_call(case_id, method, path, request_data, response_code,
                    response_data, duration_ms, success, error) -> None:
    """记录接口调试执行结果（兼容导出，委托 ApitestRepo）。"""
    try:
        ApitestRepo._log_execution(
            exec_type="debug",
            target_id=case_id or "",
            target_name="",
            method=method,
            url=path,
            request_data=request_data,
            response_data=response_data,
            asserts=[],
            extracted_variables={},
            passed=bool(success),
            response_code=response_code,
            duration_ms=duration_ms,
            error=error or "",
        )
    except Exception:
        pass
