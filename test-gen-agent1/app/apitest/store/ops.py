# -*- coding: utf-8 -*-
"""apittest store submodule: ops (batch/follows/operation logs).

Repository 下沉说明：
api_follows 关注数据访问 SQL 已下沉到 app.repositories.apitest_repo.ApitestRepo
（L3 Repository 层）。批量操作（cases/scenarios/mocks）也在 Repo 已下沉。
本模块退化为兼容门面，直接委托 ApitestRepo，保证对外行为零回归。
"""
from typing import List

from app.repositories.apitest_repo import ApitestRepo


# ── 批量操作 ──────────────────────────────────────────────
def batch_delete_definitions(def_ids: List[str]) -> int:
    return ApitestRepo.batch_delete_definitions(def_ids)


def batch_delete_cases(case_ids: List[str]) -> int:
    return ApitestRepo.batch_delete_cases(case_ids)


def batch_delete_scenarios(scenario_ids: List[str]) -> int:
    return ApitestRepo.batch_delete_scenarios(scenario_ids)


def batch_delete_mocks(mock_ids: List[str]) -> int:
    return ApitestRepo.batch_delete_mocks(mock_ids)


def batch_purge_definitions(def_ids: List[str]) -> int:
    return ApitestRepo.batch_purge_definitions(def_ids)


def batch_purge_cases(case_ids: List[str]) -> int:
    return ApitestRepo.batch_purge_cases(case_ids)


def batch_purge_scenarios(scenario_ids: List[str]) -> int:
    return ApitestRepo.batch_purge_scenarios(scenario_ids)


def batch_purge_mocks(mock_ids: List[str]) -> int:
    return ApitestRepo.batch_purge_mocks(mock_ids)


# ── 关注/取消关注 ─────────────────────────────────────────
def _init_follows_table() -> None:
    """初始化关注表（幂等，已存在时跳过）。"""
    try:
        from app.core.database import Database
        conn = Database.get_conn("apitest.db")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_follows (
                id TEXT PRIMARY KEY,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                user_id TEXT DEFAULT 'admin',
                created_at REAL,
                UNIQUE(resource_type, resource_id, user_id)
            )
        """)
        conn.commit()
    except Exception:
        pass


_init_follows_table()


def follow_resource(resource_type: str, resource_id: str, user_id: str = "admin") -> bool:
    return ApitestRepo.follow_resource(
        resource_id=resource_id, resource_type=resource_type, user_id=user_id)


def unfollow_resource(resource_type: str, resource_id: str, user_id: str = "admin") -> bool:
    return ApitestRepo.unfollow_resource(
        resource_id=resource_id, resource_type=resource_type, user_id=user_id)


def list_followers(resource_type: str, resource_id: str) -> List[str]:
    return ApitestRepo.list_followers(
        resource_id=resource_id, resource_type=resource_type)


def is_followed(resource_type: str, resource_id: str, user_id: str = "admin") -> bool:
    return ApitestRepo.is_followed(
        resource_id=resource_id, resource_type=resource_type, user_id=user_id)


def toggle_follow(resource_type: str, resource_id: str, user_id: str = "admin") -> bool:
    return ApitestRepo.toggle_follow(
        resource_id=resource_id, resource_type=resource_type, user_id=user_id)


# ── 批量更新 ──────────────────────────────────────────────
def batch_update_definitions(def_ids: List[str], **fields) -> int:
    return ApitestRepo.batch_update_definitions(def_ids, **fields)


def batch_update_cases(case_ids: List[str], **fields) -> int:
    return ApitestRepo.batch_update_cases(case_ids, **fields)


def batch_update_scenarios(scenario_ids: List[str], **fields) -> int:
    return ApitestRepo.batch_update_scenarios(scenario_ids, **fields)


def batch_update_mocks(mock_ids: List[str], **fields) -> int:
    return ApitestRepo.batch_update_mocks(mock_ids, **fields)


# ── 回收站批量操作委托 ────────────────────────────────────
def batch_restore_definitions(def_ids: List[str]) -> int:
    return ApitestRepo.batch_restore_definitions(def_ids)


def batch_restore_cases(case_ids: List[str]) -> int:
    return ApitestRepo.batch_restore_cases(case_ids)


def batch_restore_scenarios(scenario_ids: List[str]) -> int:
    return ApitestRepo.batch_restore_scenarios(scenario_ids)


def batch_restore_mocks(mock_ids: List[str]) -> int:
    return ApitestRepo.batch_restore_mocks(mock_ids)
