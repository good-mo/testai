"""身份与访问 DDD ↔ Web 层契约桥（Contract Translator）。

目的（迁移第一步 · DTO 契约桥）：
  身份域没有独立、干净的"用户/组织 CRUD"路由可整段切换，既有
  AuthRepo / OrganizationRepo 返回的 DB 行 schema 与 DDD 聚合
  `to_dict()` 输出存在字段差异。为避免将来把既有 router / service
  切到 DDD 时破坏前端与既有单测契约，这里把 DDD 聚合的输出翻译为
  与既有 Web 层（AuthRepo._row_to_user / OrganizationRepo.get 等）
  逐字段一致的字典。

设计约束：
  - 纯函数、零框架依赖，可在无 DB 环境直接单测；
  - 只翻译字段名/取值形态，不改变语义与业务规则；
  - DDD 仍保留 `to_dict()` 作为领域快照；本桥仅用于"写给 Web 层/存储"
    的对外契约翻译，保证切 DDD 后返回 schema 与既有一致、零回归。
"""
from __future__ import annotations

from typing import Any, Dict, List

# 既有 DB 层组织状态枚举（active/disabled/deleted）
_STORAGE_ORG_STATUS_ACTIVE = "active"
_STORAGE_ORG_STATUS_DISABLED = "disabled"

# DDD 领域层组织状态（enabled/disabled）
_DDD_ORG_STATUS_ACTIVE = "enabled"
_DDD_ORG_STATUS_DISABLED = "disabled"


def org_status_to_storage(status: str) -> str:
    """DDD 组织状态(enabled/disabled) → 既有存储状态(active/disabled)。"""
    if status == _DDD_ORG_STATUS_ACTIVE:
        return _STORAGE_ORG_STATUS_ACTIVE
    if status == _DDD_ORG_STATUS_DISABLED:
        return _STORAGE_ORG_STATUS_DISABLED
    # 兼容既有可能传入的存储态，直接透传
    return status or _STORAGE_ORG_STATUS_DISABLED


def org_status_from_storage(status: str) -> str:
    """既有存储状态(active/disabled/deleted) → DDD 组织状态(enabled/disabled)。"""
    if status == _STORAGE_ORG_STATUS_ACTIVE:
        return _DDD_ORG_STATUS_ACTIVE
    # disabled / deleted / 未知一律视为 disabled
    return _DDD_ORG_STATUS_DISABLED


# ─────────────────────────────────────────────────────────
# 用户契约翻译
# ─────────────────────────────────────────────────────────
def to_web_user(user_dict: Dict[str, Any]) -> Dict[str, Any]:
    """DDD 用户聚合 dict → 既有 AuthRepo Web 用户 schema。

    输入：User.to_dict()（含 created_at/updated_at/status/api_keys）
    输出：既有 AuthRepo._extract_user_from_join / 前端消费字段：
          id/username/name/email/phone/avatar/role/enable(int)/
          create_time/update_time/language/last_organization_id/
          last_project_id（去掉 DDD 专属 status/api_keys）。
    """
    enable = 1 if user_dict.get("enable", 1) else 0
    return {
        "id": user_dict.get("id", ""),
        "username": user_dict.get("username", ""),
        "name": user_dict.get("name", ""),
        "email": user_dict.get("email", ""),
        "phone": user_dict.get("phone", ""),
        "avatar": user_dict.get("avatar", ""),
        "role": user_dict.get("role", "user"),
        "enable": enable,
        "create_time": user_dict.get("created_at"),
        "update_time": user_dict.get("updated_at"),
        "language": user_dict.get("language", "zh-CN"),
        "last_organization_id": user_dict.get("last_organization_id", ""),
        "last_project_id": user_dict.get("last_project_id", ""),
    }


def to_web_user_list(user_dicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量用户契约翻译。"""
    return [to_web_user(u) for u in user_dicts]


# ─────────────────────────────────────────────────────────
# 组织契约翻译
# ─────────────────────────────────────────────────────────
def to_web_organization(org_dict: Dict[str, Any]) -> Dict[str, Any]:
    """DDD 组织聚合 dict → 既有 OrganizationRepo Web 组织 schema。

    输入：Organization.to_dict()（含 enabled/disabled 的 status、members）
    输出：既有前端/OrganizationService 消费形态：
          id/name/description/status(active|disabled)/create_time/
          update_time/members（成员保留既有 member schema）。
    """
    ddd_status = org_dict.get("status", _DDD_ORG_STATUS_ACTIVE)
    storage_status = org_status_to_storage(ddd_status)
    members = org_dict.get("members") or []
    return {
        "id": org_dict.get("id", ""),
        "name": org_dict.get("name", ""),
        "description": org_dict.get("description", ""),
        "status": storage_status,
        "create_time": org_dict.get("created_at"),
        "update_time": org_dict.get("updated_at"),
        "members": _to_web_members(members),
    }


def _to_web_members(members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """DDD 成员 dict → 既有 organization_members 行形态。"""
    out: List[Dict[str, Any]] = []
    for m in members:
        if not isinstance(m, dict):
            continue
        out.append({
            "id": m.get("id", ""),
            "organization_id": m.get("organization_id", ""),
            "user_id": m.get("user_id", ""),
            "username": m.get("username", ""),
            "name": m.get("name", ""),
            "email": m.get("email", ""),
            "role": m.get("role", "member"),
            "create_time": m.get("create_time") or m.get("created_at"),
        })
    return out


def to_web_organization_list(org_dicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量组织契约翻译。"""
    return [to_web_organization(o) for o in org_dicts]
