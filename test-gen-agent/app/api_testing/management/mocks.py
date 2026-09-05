# -*- coding: utf-8 -*-
"""app.api_testing.management.mocks 子模块（Mock 服务管理，行为不变）。

Repository 下沉说明：
V1 前端兼容层 Mock 服务（mock_services 表）的纯数据访问 CRUD SQL 已下沉到
app.repositories.apitest_repo.ApitestRepo，本模块退化为兼容门面。
"""
from typing import List, Optional

from app.repositories.apitest_repo import ApitestRepo


def create_mock_service(
    name: str,
    method: str = "GET",
    path: str = "",
    response_code: int = 200,
    response_headers: Optional[dict] = None,
    response_body: str = "{}",
    delay_ms: int = 0,
    project_id: str = "",
) -> dict:
    return ApitestRepo.mgmt_create_mock_service(
        name=name, method=method, path=path, response_code=response_code,
        response_headers=response_headers, response_body=response_body,
        delay_ms=delay_ms, project_id=project_id,
    )


def get_mock_service(mock_id: str) -> Optional[dict]:
    return ApitestRepo.mgmt_get_mock_service(mock_id)


def list_mock_services(limit: int = 100) -> List[dict]:
    return ApitestRepo.mgmt_list_mock_services(limit=limit)


def update_mock_service(mock_id: str, **kwargs) -> Optional[dict]:
    return ApitestRepo.mgmt_update_mock_service(mock_id, **kwargs)


def delete_mock_service(mock_id: str, permanent: bool = False) -> bool:
    return ApitestRepo.mgmt_delete_mock_service(mock_id, permanent=permanent)
def list_trash_mocks(limit: int = 100) -> List[dict]:
    """列出回收站中的 V1 mock_service（仓库内直连 SQL 已下沉）。"""
    return ApitestRepo.mgmt_list_trash_mocks(limit=limit)


def restore_mock(mock_id: str) -> bool:
    """从回收站恢复 V1 mock_service（仓库内直连 SQL 已下沉）。"""
    return ApitestRepo.mgmt_restore_mock(mock_id)
