# -*- coding: utf-8 -*-
"""app.api_testing.management.environments 子模块（环境管理，行为不变）。

Repository 下沉说明：
V1 前端兼容层环境（api_environments 表）的纯数据访问 SQL 已下沉到
app.repositories.apitest_repo.ApitestRepo，本模块退化为兼容门面。
"""
from typing import List, Optional

from app.repositories.apitest_repo import ApitestRepo


def create_environment(
    name: str,
    description: str = "",
    base_url: str = "",
    headers: Optional[dict] = None,
    variables: Optional[dict] = None,
    project_id: str = "",
) -> dict:
    return ApitestRepo.create_environment(
        name=name, description=description, base_url=base_url,
        headers=headers, variables=variables, project_id=project_id,
    )


def get_environment(env_id: str) -> Optional[dict]:
    """获取环境详情（仓库内直连 SQL 已下沉）。"""
    return ApitestRepo.get_environment(env_id)


def list_environments(limit: int = 100) -> List[dict]:
    """列出所有环境（仓库内直连 SQL 已下沉）。"""
    return ApitestRepo.list_environments()


def update_environment(env_id: str, **kwargs) -> Optional[dict]:
    return ApitestRepo.update_environment(env_id, **kwargs)


def delete_environment(env_id: str) -> bool:
    return ApitestRepo.delete_environment(env_id)
