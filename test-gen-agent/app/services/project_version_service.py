# app/services/project_version_service.py
"""项目版本（project_versions）业务逻辑层（project_version 域 DDD 接入 · 阶段 C 薄门面）。

项目版本 CRUD / 选项 / latest 置顶 / status 切换等落库业务已收敛到
`project_version` 域 DDD 应用服务 `project_version_app_service`（见
`app/domain/project_version/`）。本 Service 收敛为对 DDD 应用门面的**薄委托门面**，
仅保留既有方法签名以兼容 `app/routers/project_compat_extra2.py` 等调用方，返回结构
（camelCase 版本对象）与重构前一致，对外 API 零回归、可回滚。

> 约定：聚合内部与 DB 存**秒**，DDD 聚合 `to_dict()` 对外视图输出 **毫秒**
> （camelCase `createTime`）。而历史 service 的 `createTime` 一直以**秒**裸透传
> （与前端 dayjs 的毫秒期望不一致，属存量遗留），故在门面处做**契约桥**把 DDD 的
> 毫秒 `createTime` 还原为秒，保证对外返回结构与重构前字节一致、调用方零改动。
> 该「秒」字段的历史口径是否统一收敛到毫秒属独立议题，不在本接线范围内。

> 版本「功能开关」落在 project_app_configs 表（module='projectVersion'），属
> project_app_config 域（Round 1 已接线），故本类相关开关方法直接委托
> `project_app_config_app_service`。

> 推荐调用方直接使用 `project_version_app_service`；本类仅作过渡兼容层保留。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.domain.project_app_config.application.project_app_config_service import (
    project_app_config_app_service as _pac,
)
from app.domain.project_version.application.dto import (
    CreateVersionCommand,
    DeleteVersionCommand,
    GetVersionCommand,
    ListVersionsCommand,
    UpdateVersionCommand,
)
from app.domain.project_version.application.project_version_app_service import (
    project_version_app_service as _ddd,
)
from app.domain.project_version.domain.exceptions import ProjectVersionNotFound


def _to_item(ddd_dict: Optional[dict],
             default_project_id: str = "") -> Optional[Dict[str, Any]]:
    """把 DDD to_dict（camelCase、createTime 毫秒）桥接为历史 service 返回的版本对象。

    与历史 `_to_item` 输出 schema 完全一致（createTime 仍为秒裸透传、status/latest
    归一为 bool、publishTime 原样透传），router 与前端零改动。
    """
    if not ddd_dict:
        return None
    return {
        "id": ddd_dict.get("id", ""),
        "name": ddd_dict.get("name", ""),
        "description": ddd_dict.get("description", ""),
        "status": bool(ddd_dict.get("status", False)),
        "latest": bool(ddd_dict.get("latest", False)),
        "publishTime": int(ddd_dict.get("publishTime") or 0),
        # DDD 输出毫秒；历史口径为秒（裸透传），桥接还原为秒
        "createTime": int((ddd_dict.get("createTime") or 0) // 1000),
        "createUser": ddd_dict.get("createUser", "admin"),
        "projectId": ddd_dict.get("projectId", default_project_id),
    }


class ProjectVersionService:
    """项目版本服务：router 层唯一业务入口（project_version 域 DDD 薄门面）。"""

    # ── 列表 / 详情 ──────────────────────────────────────
    @staticmethod
    def list_items(project_id: str, keyword: str = "") -> List[Dict[str, Any]]:
        """项目版本列表（前端 camelCase 结构）。"""
        rows = _ddd.list(ListVersionsCommand(project_id=project_id, keyword=keyword))
        return [_to_item(r, project_id) for r in rows]

    @staticmethod
    def get_item(version_id: str) -> Optional[Dict[str, Any]]:
        """单个项目版本；不存在返回 None。"""
        return _to_item(_ddd.get(GetVersionCommand(version_id=version_id)))

    # ── 新增 / 更新 / 删除 ──────────────────────────────
    @staticmethod
    def add(project_id: str, name: str, description: str = "",
            status: bool = False, latest: bool = False,
            publish_time: float = 0.0) -> Optional[Dict[str, Any]]:
        """新增项目版本并落库。"""
        created = _ddd.create(CreateVersionCommand(
            project_id=project_id, name=name, description=description,
            status=status, latest=latest, publish_time=publish_time,
        ))
        return _to_item(created, project_id)

    @staticmethod
    def update(version_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """按 id 更新项目版本；版本不存在返回 None。"""
        data = data or {}
        try:
            updated = _ddd.update(UpdateVersionCommand(
                version_id=version_id,
                name=data.get("name"),
                description=data.get("description"),
                status=data.get("status"),
                latest=data.get("latest"),
                publish_time=data.get("publishTime"),
            ))
        except ProjectVersionNotFound:
            return None
        return _to_item(updated)

    @staticmethod
    def delete(version_id: str) -> bool:
        """按 id 删除项目版本。"""
        return _ddd.delete(DeleteVersionCommand(version_id=version_id))

    # ── 选项（前端下拉）─────────────────────────────────
    @staticmethod
    def options(project_id: str) -> List[Dict[str, Any]]:
        """项目版本下拉选项 [{id,name,latest,enable}]。"""
        return _ddd.options(project_id)

    # ── 切换 latest / status ─────────────────────────────
    @staticmethod
    def set_latest(version_id: str) -> Optional[Dict[str, Any]]:
        """将指定版本置为最新（同时清除同项目其他版本 latest）。"""
        try:
            return _to_item(_ddd.set_latest(version_id))
        except ProjectVersionNotFound:
            return None

    @staticmethod
    def toggle_status(version_id: str) -> Optional[Dict[str, Any]]:
        """切换版本状态（取反）。"""
        try:
            return _to_item(_ddd.toggle_status(version_id))
        except ProjectVersionNotFound:
            return None

    # ── 版本功能开关（project_app_configs · project_app_config 域）────────────
    @staticmethod
    def is_feature_enabled(project_id: str) -> bool:
        """项目版本功能是否启用。"""
        return _pac.is_project_version_enabled(project_id)

    @staticmethod
    def set_feature_enabled(project_id: str, enabled: bool) -> None:
        """设置项目版本功能启用状态。"""
        _pac.set_project_version_enabled(project_id, enabled)

    @staticmethod
    def toggle_feature_enabled(project_id: str) -> bool:
        """切换项目版本功能启用状态，返回切换后状态。"""
        current = _pac.is_project_version_enabled(project_id)
        new_state = not current
        _pac.set_project_version_enabled(project_id, new_state)
        return new_state


# 模块级单例（与其它 service 风格一致）
project_version_service = ProjectVersionService()
