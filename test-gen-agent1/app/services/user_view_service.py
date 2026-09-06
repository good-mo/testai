# app/services/user_view_service.py
"""用户视图（user-view）业务逻辑层（user_view 域 DDD 接入 · 阶段 C 薄门面）。

自定义视图（customViews）落库业务已收敛到 user_view 域 DDD 应用服务
`user_view_app_service`（见 `app/domain/user_view/`）。本 Service 收敛为对
DDD 应用门面的**薄委托门面**，仅保留既有方法签名以兼容
`app/routers/system_compat.py` 等调用方，返回结构（完整前端视图对象）与
重构前一致。

> 推荐调用方直接使用 `user_view_app_service`；本类仅作过渡兼容层保留。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.domain.user_view.application.dto import (
    CreateUserViewCommand,
    DeleteUserViewCommand,
    GetUserViewCommand,
    ListUserViewsCommand,
    UpdateUserViewCommand,
)
from app.domain.user_view.application.user_view_app_service import (
    user_view_app_service as _ddd,
)
from app.domain.user_view.domain.exceptions import UserViewNotFound


class UserViewService:
    """用户视图服务：承接 Router 层的增删改查调用（user_view 域 DDD 薄门面）。"""

    # ── 列表 ────────────────────────────────────────────
    @staticmethod
    def list_custom_views(view_type: str, scope_id: str = "") -> List[Dict[str, Any]]:
        """按 view_type+scope_id 读取全部自定义视图，按 pos 升序。"""
        return _ddd.list_custom_views(ListUserViewsCommand(
            view_type=view_type, scope_id=scope_id,
        ))

    # ── 详情 ────────────────────────────────────────────
    @staticmethod
    def get_custom_view(view_id: str) -> Optional[Dict[str, Any]]:
        """按视图 id 读取单条自定义视图；不存在返回 None。"""
        return _ddd.get(GetUserViewCommand(view_id=view_id))

    # ── 新增 ────────────────────────────────────────────
    @staticmethod
    def add_custom_view(view_type: str, scope_id: str, body: Dict[str, Any],
                        user_id: str = "admin", new_id: str = "") -> Dict[str, Any]:
        """新增自定义视图并落库，返回前端视图对象。"""
        return _ddd.create(CreateUserViewCommand(
            view_type=view_type, scope_id=scope_id, body=body,
            user_id=user_id, new_id=new_id,
        ))

    # ── 更新 ────────────────────────────────────────────
    @staticmethod
    def update_custom_view(view_id: str, body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """按视图 id 更新（合并 body 字段）；不存在返回 None。"""
        try:
            return _ddd.update(UpdateUserViewCommand(
                view_id=view_id, body=body,
            ))
        except UserViewNotFound:
            return None

    # ── 删除 ────────────────────────────────────────────
    @staticmethod
    def delete_custom_view(view_id: str) -> bool:
        """按视图 id 删除；返回是否存在并删除。"""
        return _ddd.delete(DeleteUserViewCommand(view_id=view_id))


# 模块级单例（与其它 service 风格一致，如 auth_service / project_service）
user_view_service = UserViewService()


__all__ = ["user_view_service", "UserViewService"]
