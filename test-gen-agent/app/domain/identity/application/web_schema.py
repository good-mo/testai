"""身份与访问 DTO 契约桥（Web ↔ DDD Aggregate 适配层）。

目标：让 `IdentityAppService` / DDD 聚合的输出与既有四层返回行
（`AuthRepo` / `OrganizationRepo` / `UserGroupRepo` / `InvitationRepo`）
保持**契约兼容**，作为身份域 "A→B→C" 渐进迁移的第 1 步（DTO 桥）。

为什么需要它：
- 既有 `AuthRepo._row_to_user` 返回 DB 行（含 `enable`/`create_time`/
  `update_time`/`create_user`/`deleted` 等）。
- DDD 聚合 `User.to_dict()` 以 `enable`+`status`+`created_at` 表达同一账号，
  且不携带 `create_user`/`deleted` 等存储元字段。
- 若后续把 `auth_service`/`organization_service` 门面切到 `IdentityAppService`
  而不先做契约对齐，直接切换会破坏前端 / 既有单测依赖的字段。

本模块把 DDD 输出翻译回"既有 Web 行 schema"（超集，含只读的 DDD 增强字段），
方向恒定：aggregate/to_dict → web row。反向（web row → aggregate）由各聚合
`from_dict` 负责，无需在本层重复。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _num_to_enable(status: Any) -> int:
    """把 DDD 的 enable/status 归一到既有行的 `enable`(1/0)。"""
    if status is None:
        return 1
    if isinstance(status, int):
        return 1 if status else 0
    return 1 if str(status).lower() in ("1", "true", "enabled", "active") else 0


def user_to_web_row(u: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """把 DDD 应用服务返回的 User 字典翻译为既有 `AuthRepo` 行 schema。

    保留既有调用方（邀请注册 / 成员/组织路由 / seed）依赖的字段：
    id / username / email / phone / avatar / name / role / enable /
    create_time / update_time / language / last_organization_id /
    last_project_id；并补充 deleted / create_user / update_user 缺省值，
    以及只读增强字段 status / api_keys（不破坏既有读取方）。
    """
    if not u:
        return None
    enable = u.get("enable")
    if enable is None:
        enable = _num_to_enable(u.get("status", 1))
    row: Dict[str, Any] = {
        "id": u.get("id"),
        "username": u.get("username", ""),
        "name": u.get("name", ""),
        "email": u.get("email", ""),
        "phone": u.get("phone", ""),
        "avatar": u.get("avatar", ""),
        "role": u.get("role", "user"),
        "enable": 1 if enable else 0,
        "create_time": u.get("create_time", u.get("created_at")),
        "update_time": u.get("update_time", u.get("updated_at")),
        "deleted": u.get("deleted", 0),
        "create_user": u.get("create_user", ""),
        "update_user": u.get("update_user", ""),
        "language": u.get("language", "zh-CN"),
        "last_organization_id": u.get("last_organization_id", ""),
        "last_project_id": u.get("last_project_id", ""),
    }
    # 只读增强字段（DDD 特有，保持透传，不参与既有行主键/写入）
    for extra in ("status", "api_keys", "created_at", "updated_at"):
        if u.get(extra) is not None:
            row[extra] = u.get(extra)
    return row


def users_to_web_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [user_to_web_row(r) for r in rows if r]


def member_to_web_row(m: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """把 DDD Member 字典翻译为既有 `OrganizationRepo.list_members` 行。

    既有 organization_members 行字段：id / organization_id / user_id /
    username / name / email / role / create_time / update_time / deleted。
    """
    if not m:
        return None
    row: Dict[str, Any] = {
        "id": m.get("member_id", m.get("id")),
        "organization_id": m.get("organization_id", ""),
        "user_id": m.get("user_id", ""),
        "username": m.get("username", ""),
        "name": m.get("name", ""),
        "email": m.get("email", ""),
        "role": (m.get("role") or "member").lower(),
        "create_time": m.get("create_time", m.get("created_at")),
        "update_time": m.get("update_time", m.get("updated_at")),
        "deleted": m.get("deleted", 0),
    }
    return row


def org_to_web_row(o: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """把 DDD 应用服务返回的 Organization 字典翻译为既有 OrganizationRepo 行。"""
    if not o:
        return None
    members = o.get("members") or []
    # 既有行用 status=active/disabled（DDD 用 enabled），在此归一并兼容两端
    status = o.get("status")
    if status is None:
        status = "active"
    elif status in ("enabled", "disabled", "active"):
        pass
    else:
        status = "active" if _num_to_enable(status) else "disabled"
    row: Dict[str, Any] = {
        "id": o.get("id"),
        "name": o.get("name", ""),
        "description": o.get("description", ""),
        "status": status,
        "create_time": o.get("create_time", o.get("created_at")),
        "update_time": o.get("update_time", o.get("updated_at")),
    }
    if members:
        row["members"] = [member_to_web_row(x) for x in members]
    return row


__all__ = [
    "user_to_web_row", "users_to_web_rows", "member_to_web_row",
    "org_to_web_row",
]
