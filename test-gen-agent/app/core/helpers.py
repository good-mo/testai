# app/core/helpers.py
"""公共路由/请求处理 helper 收敛层。

集中存放跨路由文件重复定义的微型 helper，供 app/routers/*、
app/test_plan/* 等路由文件统一导入，消除逐文件重复实现：

  - as_model:             body dict → Pydantic 模型宽松校验（空/畸形回退默认实例）
  - current_user_name:    从 request.state 解析当前用户名（优先 username，兜底 id）
  - current_user_id:      从 request.state 解析当前用户 id
  - current_user:         从 request.state 取原始 user dict
  - definition_followed:  判断 definition 是否已被关注（api_follows 落库读回）
"""

from typing import Type, TypeVar

from fastapi import Request

_M = TypeVar("_M")

__all__ = [
    "as_model",
    "current_user_name",
    "current_user_id",
    "current_user",
    "definition_followed",
]


def as_model(body, model: Type[_M]) -> _M:
    """把 `read_body` 归一化后的 dict 校验成请求体模型。

    语义与 read_body 保持一致：非 dict 兜底为模型默认值，校验失败回退默认实例，
    保证接入模型后行为零回归。
    """
    raw = body if isinstance(body, dict) else {}
    try:
        return model.model_validate(raw)
    except Exception:
        return model()


def current_user_name(request: Request) -> str:
    """从请求上下文解析当前用户名（用于操作人记录 / 按人隔离）。

    优先取 username，回退到 id，均无则返回 "admin"。
    """
    try:
        user = getattr(request.state, "user", None)
        if user and user.get("username"):
            return str(user["username"])
        if user and user.get("id"):
            return str(user["id"])
    except Exception:
        pass
    return "admin"


def current_user_id(request: Request) -> str:
    """从请求上下文解析当前用户 id（个人数据 owner 语义）。

    无登录态时返回 "admin"。
    """
    try:
        user = getattr(request.state, "user", None)
        if user and user.get("id"):
            return str(user["id"])
    except Exception:
        pass
    return "admin"


def current_user(request: Request) -> dict:
    """当前登录用户（中间件注入），失败时返回空 dict。"""
    return getattr(request.state, "user", None) or {}


def definition_followed(def_id: str) -> bool:
    """读取当前用户是否已关注接口定义（api_follows 落库读回）。

    关注读回闭环：definition 已支持真实落库，列表/回收站/分享详情读回
    真实关注状态，避免 follow 恒为 False。resource_type=definition。
    """
    if not def_id:
        return False
    try:
        from app.services.apitest_service import apitest_service
        return bool(apitest_service.is_followed("definition", def_id))
    except Exception:
        return False
