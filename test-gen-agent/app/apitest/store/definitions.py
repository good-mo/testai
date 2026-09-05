# -*- coding: utf-8 -*-
"""apittest store submodule: definitions.

Repository 下沉说明：
接口定义（api_definitions）的纯数据访问 CRUD / 回收站 / 版本管理 / 批量操作
SQL 已下沉到 app.repositories.apitest_repo.ApitestRepo（L3 Repository 层），
本模块退化为兼容门面，直接委托 ApitestRepo，保证对外行为零回归。
"""
from typing import Any, Dict, List, Optional

from app.repositories.apitest_repo import ApitestRepo


# ── 接口定义 ───────────────────────────────────────────────
def create_definition(name: str, protocol: str = "HTTP", method: str = "GET",
                      path: str = "", headers: dict = None, body: str = "",
                      query: dict = None, params: dict = None,
                      description: str = "", tags: list = None,
                      project_id: str = "", version: str = "v1",
                      module_id: str = "") -> Dict[str, Any]:
    return ApitestRepo.create_definition(
        name=name, protocol=protocol, method=method, path=path,
        headers=headers, body=body, query=query, params=params,
        description=description, tags=tags, project_id=project_id,
        version=version, module_id=module_id,
    )


def list_definitions(keyword: str = "", limit: int = 100, offset: int = 0,
                     project_id: str = "", include_latest_only: bool = True,
                     protocols: Optional[List[str]] = None,
                     module_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    return ApitestRepo.list_definitions(
        keyword=keyword, limit=limit, offset=offset, project_id=project_id,
        include_latest_only=include_latest_only,
        protocols=protocols, module_ids=module_ids,
    )


def count_definitions(project_id: str = "", keyword: str = "",
                      protocols: Optional[List[str]] = None,
                      module_ids: Optional[List[str]] = None) -> int:
    return ApitestRepo.count_definitions(
        project_id=project_id, keyword=keyword,
        protocols=protocols, module_ids=module_ids,
    )


def count_definitions_by_module(protocols: Optional[List[str]] = None) -> Dict[str, int]:
    return ApitestRepo.count_definitions_by_module(protocols=protocols)


def count_definitions_total(protocols: Optional[List[str]] = None) -> int:
    return ApitestRepo.count_definitions_total(protocols=protocols)


def count_cases_for_definition(definition_id: str) -> int:
    return ApitestRepo.count_cases_for_definition(definition_id)


def list_schedules(keyword: str = "") -> List[Dict[str, Any]]:
    return ApitestRepo.list_schedules(keyword=keyword)


def get_definition(definition_id: str) -> Optional[Dict[str, Any]]:
    return ApitestRepo.get_definition(definition_id)


def update_definition(definition_id: str, **fields) -> Optional[Dict[str, Any]]:
    return ApitestRepo.update_definition(definition_id, **fields)


def delete_definition(definition_id: str) -> bool:
    return ApitestRepo.delete_definition(definition_id)


def list_trash_definitions(project_id: str = "", limit: int = 100) -> List[Dict[str, Any]]:
    return ApitestRepo.list_trash_definitions(project_id=project_id, limit=limit)


def count_trash_definitions(project_id: str = "") -> int:
    return ApitestRepo.count_trash_definitions(project_id=project_id)


def restore_definition(definition_id: str) -> bool:
    return ApitestRepo.restore_definition(definition_id)


def batch_restore_definitions(definition_ids: List[str]) -> int:
    return ApitestRepo.batch_restore_definitions(definition_ids)


def purge_definition(definition_id: str) -> bool:
    return ApitestRepo.purge_definition(definition_id)


# ── 版本管理 ──────────────────────────────────────────────
def list_definition_versions(ref_id: str) -> List[Dict[str, Any]]:
    return ApitestRepo.list_definition_versions(ref_id)


def create_definition_version(definition_id: str, version: str = "") -> Optional[Dict[str, Any]]:
    return ApitestRepo.create_definition_version(definition_id, version)


def rollback_definition(definition_id: str, version_id: str) -> Optional[Dict[str, Any]]:
    return ApitestRepo.rollback_definition(definition_id, version_id)
