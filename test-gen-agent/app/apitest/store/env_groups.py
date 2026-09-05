# -*- coding: utf-8 -*-
"""apittest store submodule: env_groups.

Repository 下沉说明：
环境组（env_groups）与全局参数（global_params）的纯数据访问 SQL 已下沉到
app.repositories.apitest_repo.ApitestRepo（L3 Repository 层），本模块退化
为兼容门面，直接委托 ApitestRepo，保证对外行为零回归。
"""
from typing import Any, Dict, List, Optional

from app.repositories.apitest_repo import ApitestRepo

# ── 环境组 CRUD ─────────────────────────────────────────────

def create_env_group(
    name: str,
    description: str = "",
    project_id: str = "",
    env_group_project: list = None,
    pos: int = 0,
) -> Optional[Dict[str, Any]]:
    """创建环境组。"""
    return ApitestRepo.create_env_group(
        name=name, description=description, project_id=project_id,
        env_group_project=env_group_project, pos=pos,
    )


def list_env_groups(project_id: str = "", keyword: str = "") -> List[Dict[str, Any]]:
    """列出环境组。"""
    return ApitestRepo.list_env_groups(project_id=project_id, keyword=keyword)


def _get_env_group_dict(group_id: str) -> Optional[Dict[str, Any]]:
    """获取环境组（内部辅助，委托 ApitestRepo）。"""
    return ApitestRepo.get_env_group(group_id)


def get_env_group(group_id: str) -> Optional[Dict[str, Any]]:
    """获取环境组详情。"""
    return ApitestRepo.get_env_group(group_id)


def update_env_group(group_id: str, **fields) -> Optional[Dict[str, Any]]:
    """更新环境组。"""
    return ApitestRepo.update_env_group(group_id, **fields)


def delete_env_group(group_id: str) -> bool:
    """删除环境组。"""
    return ApitestRepo.delete_env_group(group_id)


def get_env_groups_by_project(project_id: str) -> List[Dict[str, Any]]:
    """获取项目下的环境组列表（用于选择器）。"""
    return ApitestRepo.get_env_groups_by_project(project_id)


# ── 全局参数 CRUD ───────────────────────────────────────────

def get_global_params(project_id: str) -> Optional[Dict[str, Any]]:
    """获取项目全局参数。"""
    return ApitestRepo.get_global_params(project_id)


def save_global_params(
    project_id: str,
    headers: list = None,
    common_variables: list = None,
) -> Dict[str, Any]:
    """保存全局参数（新建或更新）。"""
    return ApitestRepo.save_global_params(
        project_id=project_id, headers=headers,
        common_variables=common_variables,
    )


def delete_global_params(project_id: str) -> bool:
    """删除项目全局参数。"""
    return ApitestRepo.delete_global_params(project_id)
