# -*- coding: utf-8 -*-
"""apittest store submodule: mocks.

Repository 下沉说明：
Mock 服务（api_mocks）的纯数据访问 CRUD / 回收站 / 批量操作 SQL 已下沉到
app.repositories.apitest_repo.ApitestRepo（L3 Repository 层），本模块退化为
兼容门面，直接委托 ApitestRepo，保证对外行为零回归。
"""
from typing import Any, Dict, List, Optional

from app.repositories.apitest_repo import ApitestRepo


def create_mock(name: str, api_definition_id: str = "", method: str = "GET",
                path: str = "", status_code: int = 200, response_body: str = "",
                response_headers: dict = None, delay_ms: int = 0,
                active: int = 1, description: str = "",
                project_id: str = "", match_type: str = "exact",
                match_script: str = "") -> Dict[str, Any]:
    return ApitestRepo.create_mock(
        name=name, api_definition_id=api_definition_id, method=method, path=path,
        status_code=status_code, response_body=response_body,
        response_headers=response_headers, delay_ms=delay_ms, active=active,
        description=description, project_id=project_id, match_type=match_type,
        match_script=match_script,
    )


def list_mocks(keyword: str = "", limit: int = 100, offset: int = 0,
               project_id: str = "") -> List[Dict[str, Any]]:
    return ApitestRepo.list_mocks(
        keyword=keyword, limit=limit, offset=offset, project_id=project_id)


def count_mocks(project_id: str = "") -> int:
    return ApitestRepo.count_mocks(project_id=project_id)


def get_mock(mock_id: str) -> Optional[Dict[str, Any]]:
    return ApitestRepo.get_mock(mock_id)


def update_mock(mock_id: str, **fields) -> Optional[Dict[str, Any]]:
    return ApitestRepo.update_mock(mock_id, **fields)


def delete_mock(mock_id: str) -> bool:
    return ApitestRepo.delete_mock(mock_id)


def list_trash_mocks(project_id: str = "", limit: int = 100) -> List[Dict[str, Any]]:
    return ApitestRepo.list_trash_mocks(project_id=project_id, limit=limit)


def count_trash_mocks(project_id: str = "") -> int:
    return ApitestRepo.count_trash_mocks(project_id=project_id)


def restore_mock(mock_id: str) -> bool:
    return ApitestRepo.restore_mock(mock_id)


def batch_restore_mocks(mock_ids: List[str]) -> int:
    return ApitestRepo.batch_restore_mocks(mock_ids)


def purge_mock(mock_id: str) -> bool:
    return ApitestRepo.purge_mock(mock_id)
