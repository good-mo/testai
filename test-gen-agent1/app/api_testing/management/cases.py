# -*- coding: utf-8 -*-
"""app.api_testing.management.cases 子模块（接口用例管理，行为不变）。

Repository 下沉说明：
V1 前端兼容层接口用例（api_test_cases 表）的纯数据访问 CRUD SQL 已下沉到
app.repositories.apitest_repo.ApitestRepo，本模块退化为兼容门面。
"""
from typing import List, Optional

from app.repositories.apitest_repo import ApitestRepo


def create_api_test_case(
    name: str,
    definition_id: Optional[str] = None,
    method: str = "GET",
    path: str = "",
    request_headers: Optional[dict] = None,
    request_params: Optional[dict] = None,
    request_body: str = "",
    request_body_type: str = "json",
    assertions: Optional[list] = None,
    pre_scripts: Optional[list] = None,
    post_scripts: Optional[list] = None,
    pre_sql: str = "",
    post_sql: str = "",
    variables: Optional[dict] = None,
    environment_id: Optional[str] = None,
    timeout: int = 30,
    retry_count: int = 0,
    project_id: str = "",
) -> dict:
    return ApitestRepo.mgmt_create_api_test_case(
        name=name, definition_id=definition_id, method=method, path=path,
        request_headers=request_headers, request_params=request_params,
        request_body=request_body, request_body_type=request_body_type,
        assertions=assertions, pre_scripts=pre_scripts,
        post_scripts=post_scripts, pre_sql=pre_sql, post_sql=post_sql,
        variables=variables, environment_id=environment_id,
        timeout=timeout, retry_count=retry_count, project_id=project_id,
    )


def get_api_test_case(case_id: str) -> Optional[dict]:
    return ApitestRepo.mgmt_get_api_test_case(case_id)


def list_api_test_cases(
    search: str = "",
    definition_id: str = "",
    environment_id: str = "",
    enabled: Optional[bool] = None,
    limit: int = 100,
    project_id: str = "",
) -> List[dict]:
    return ApitestRepo.mgmt_list_api_test_cases(
        search=search, definition_id=definition_id,
        environment_id=environment_id, enabled=enabled,
        limit=limit, project_id=project_id,
    )


def update_api_test_case(case_id: str, **kwargs) -> Optional[dict]:
    return ApitestRepo.mgmt_update_api_test_case(case_id, **kwargs)


def delete_api_test_case(case_id: str, permanent: bool = False) -> bool:
    return ApitestRepo.mgmt_delete_api_test_case(case_id, permanent=permanent)


def list_trash_cases(limit: int = 100) -> List[dict]:
    return ApitestRepo.mgmt_list_trash_cases(limit=limit)


def restore_case(case_id: str) -> bool:
    return ApitestRepo.mgmt_restore_case(case_id)
