# -*- coding: utf-8 -*-
"""app.api_testing.management.definitions 子模块（接口定义管理，行为不变）。

Repository 下沉说明：
V1 前端兼容层接口定义（api_definitions V1 列）的纯数据访问 SQL 已下沉到
app.repositories.apitest_repo.ApitestRepo，本模块退化为兼容门面。
"""
from typing import List, Optional

from app.repositories.apitest_repo import ApitestRepo


def create_api_definition(
    name: str,
    method: str = "GET",
    path: str = "",
    protocol: str = "HTTP",
    description: str = "",
    request_headers: Optional[dict] = None,
    request_params: Optional[dict] = None,
    request_body: str = "",
    request_body_type: str = "json",
    response_code: str = "200",
    response_headers: Optional[dict] = None,
    response_body: str = "",
    response_body_type: str = "json",
    tags: Optional[list] = None,
    project_id: str = "",
) -> dict:
    return ApitestRepo.mgmt_create_api_definition(
        name=name, method=method, path=path, protocol=protocol,
        description=description, request_headers=request_headers,
        request_params=request_params, request_body=request_body,
        request_body_type=request_body_type, response_code=response_code,
        response_headers=response_headers, response_body=response_body,
        response_body_type=response_body_type, tags=tags,
        project_id=project_id,
    )


def get_api_definition(def_id: str) -> Optional[dict]:
    return ApitestRepo.mgmt_get_api_definition(def_id)


def list_api_definitions(
    search: str = "",
    method: str = "",
    protocol: str = "",
    limit: int = 100,
    project_id: str = "",
) -> List[dict]:
    return ApitestRepo.mgmt_list_api_definitions(
        search=search, method=method, protocol=protocol,
        limit=limit, project_id=project_id,
    )


def update_api_definition(def_id: str, **kwargs) -> Optional[dict]:
    return ApitestRepo.mgmt_update_api_definition(def_id, **kwargs)


def delete_api_definition(def_id: str, permanent: bool = False) -> bool:
    return ApitestRepo.mgmt_delete_api_definition(def_id, permanent=permanent)


def list_trash_definitions(limit: int = 100) -> List[dict]:
    return ApitestRepo.mgmt_list_trash_definitions(limit=limit)


def restore_definition(def_id: str) -> bool:
    return ApitestRepo.mgmt_restore_definition(def_id)
