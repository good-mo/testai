"""身份域 → 既有四层 Service 的守卫委托（Delegation Guards）。

迁移第二/三步（B/C · Service 委托 + 规则下沉）：
  既有 AuthService / OrganizationService 是薄门面、无领域规则。为让 DDD
  聚合不变量（组织至少保留一名 owner、内置角色保护、账号/组织启停状态机、
  改名/邮箱非空合法等）真正作用于既有调用链，这里向既有 Service 暴露一组
  "守卫委托"助手：Service 在执行原落库前先经 DDD 聚合校验，非法即拒绝。

设计约束（渐进式、可回滚、零破坏）：
  - 只读不改：守卫仅用 DDD 聚合做判定，不改变落库路径；
  - 读不到对象 / 内部异常时**放行**给既有 repo 兜底，绝不抛 500、绝不误伤；
  - 每个守卫返回 (allowed: bool, error: str|None)；allowed=True 表示可继续原逻辑，
    allowed=False 表示违反领域不变量，由调用方决定返回失败语义；
  - 不改变既有 service 的对外返回 schema 与 router 契约。
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from app.domain.identity.application.identity_app_service import (
    IdentityAppService,
    identity_app_service,
)

logger = logging.getLogger(__name__)

# 组织成员角色合法集合（与领域枚举对齐）
_VALID_MEMBER_ROLES = {"owner", "admin", "member"}


# ─────────────────────────────────────────────────────────
# 用户域守卫
# ─────────────────────────────────────────────────────────
def guard_user_update_email(email: Optional[str]) -> Tuple[bool, Optional[str]]:
    """改邮箱前校验：提供且非空时须格式合法（与 User.change_email 一致）。"""
    email = (email or "").strip()
    if email and "@" not in email:
        return False, f"邮箱格式不合法: {email}"
    return True, None


def guard_user_toggle(user_id: str, enabled: bool,
                      svc: IdentityAppService = None) -> Tuple[bool, Optional[str]]:
    """账号启停守卫（经 DDD 账号状态机，幂等）。读不到即放行兜底。"""
    svc = svc or identity_app_service
    try:
        agg = svc.get_user(user_id)  # dict（DDD schema）
    except Exception as exc:  # pragma: no cover - 兜底放行
        logger.warning("identity guard_user_toggle 读取用户失败放行: %s", exc)
        return True, None
    if not agg:
        return True, None  # 用户不存在，交给既有 repo 兜底（多为 False）
    # DDD 校验由聚合方法执行（enable/disable 幂等），此处直接放行
    return True, None


# ─────────────────────────────────────────────────────────
# 组织域守卫
# ─────────────────────────────────────────────────────────
def guard_org_rename(name: str) -> Tuple[bool, Optional[str]]:
    """组织改名校验：非空（与 Organization.rename 一致）。"""
    if not (name or "").strip():
        return False, "组织名称不能为空"
    return True, None


def guard_org_remove_member(org_id: str, user_id: str,
                            svc: IdentityAppService = None) -> Tuple[bool, Optional[str]]:
    """移除成员守卫：组织至少保留一名 owner。

    仅当目标成员确为 owner 且组织仅剩该 owner 时拒绝；否则放行。
    读不到组织/成员即放行兜底（保持既有行为）。
    """
    svc = svc or identity_app_service
    try:
        agg = svc.get_organization(org_id)
    except Exception as exc:  # pragma: no cover - 兜底放行
        logger.warning("identity guard_org_remove_member 读取组织失败放行: %s", exc)
        return True, None
    if not agg:
        return True, None
    members = agg.get("members") or []
    owners = [m for m in members if (m or {}).get("role") == "owner"]
    target = next((m for m in members if (m or {}).get("user_id") == user_id), None)
    if target is None:
        return True, None  # 成员不在组织，交给既有 repo（删除 0 行 → False）
    if target.get("role") == "owner" and len(owners) <= 1:
        return False, "组织至少需要保留一名所有者，不能移除唯一所有者"
    return True, None


def guard_org_change_member_role(org_id: str, user_id: str, new_role: str,
                                 svc: IdentityAppService = None) -> Tuple[bool, Optional[str]]:
    """改成员角色守卫：角色合法 + 唯一 owner 不可被降级。

    DDD 里 owner 仅当 operator != system 且为唯一 owner 才拒降级；这里遵循
    "唯一 owner 不可被降级/移除管理入口"的安全语义：若目标是唯一 owner 且
    要降级为非 owner，则拒绝。
    """
    new_role = (new_role or "").lower()
    if new_role not in _VALID_MEMBER_ROLES:
        return False, f"非法成员角色: {new_role}"
    svc = svc or identity_app_service
    try:
        agg = svc.get_organization(org_id)
    except Exception as exc:  # pragma: no cover - 兜底放行
        logger.warning("identity guard_org_change_member_role 读取组织失败放行: %s", exc)
        return True, None
    if not agg:
        return True, None
    members = agg.get("members") or []
    owners = [m for m in members if (m or {}).get("role") == "owner"]
    target = next((m for m in members if (m or {}).get("user_id") == user_id), None)
    if target is None:
        return True, None
    if target.get("role") == "owner" and len(owners) <= 1 and new_role != "owner":
        return False, "组织至少需要保留一名所有者，不能降级唯一所有者"
    return True, None
