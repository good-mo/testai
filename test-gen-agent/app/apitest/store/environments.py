# -*- coding: utf-8 -*-
"""apittest store submodule: environments.

Repository 下沉说明：
环境（api_environments）的纯数据访问 CRUD SQL 已下沉到
app.repositories.apitest_repo.ApitestRepo（L3 Repository 层），
本模块退化为兼容门面，直接委托 ApitestRepo，保证对外行为零回归。

env_detail_to_frontend / env_frontend_to_db 已下沉到 ApitestRepo，
本模块退化为兼容门面。
"""
from typing import Any, Dict, List, Optional

from app.repositories.apitest_repo import ApitestRepo


# ── 环境管理 ───────────────────────────────────────────────
def create_environment(name: str, base_url: str = "", headers: dict = None,
                       variables: dict = None, description: str = "",
                       project_id: str = "", script: str = "",
                       database_config: dict = None,
                       config: dict = None) -> Dict[str, Any]:
    return ApitestRepo.create_environment(
        name=name, base_url=base_url, headers=headers,
        variables=variables, description=description,
        project_id=project_id, script=script,
        database_config=database_config, config=config,
    )


def list_environments(project_id: str = "") -> List[Dict[str, Any]]:
    return ApitestRepo.list_environments(project_id=project_id)


def count_environments(project_id: str = "") -> int:
    return ApitestRepo.count_environments(project_id=project_id)


def get_environment(env_id: str) -> Optional[Dict[str, Any]]:
    return ApitestRepo.get_environment(env_id)


def update_environment(env_id: str, **fields) -> Optional[Dict[str, Any]]:
    return ApitestRepo.update_environment(env_id, **fields)


def delete_environment(env_id: str) -> bool:
    return ApitestRepo.delete_environment(env_id)


def export_environment(env_id: str) -> Optional[Dict[str, Any]]:
    return ApitestRepo.export_environment(env_id)


def import_environment(data: Dict[str, Any], project_id: str = "") -> Optional[Dict[str, Any]]:
    return ApitestRepo.import_environment(data, project_id=project_id)


# ── 环境格式转换（兼容门面，委托 ApitestRepo）────────
def _env_to_frontend(e: Dict[str, Any]) -> Dict[str, Any]:
    """将后端 api_environments 记录转换为前端 EnvDetailItem 格式（委托 ApitestRepo）。"""
    return ApitestRepo._env_to_frontend(e)


def env_detail_to_frontend(env: Dict[str, Any]) -> Dict[str, Any]:
    """将后端 api_environments 记录转为前端完整 EnvDetailItem（委托 ApitestRepo）。"""
    return ApitestRepo.env_detail_to_frontend(env)


def env_frontend_to_db(data: Dict[str, Any]) -> Dict[str, Any]:
    """将前端 EnvDetailItem 转为后端存储格式（委托 ApitestRepo）。"""
    return ApitestRepo.env_frontend_to_db(data)
