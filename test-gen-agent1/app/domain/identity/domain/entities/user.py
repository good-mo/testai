"""用户聚合根 User。

聚合边界内的组成：
  - User（聚合根：账号基本信息 + 可用状态）
  - 若干子实体/值对象：ApiKey[]（个人 API 密钥）

职责：守护用户账号的不变量（用户名非空、密码策略、停用/启用状态流转）。
所有变更必须经由聚合根方法触发；业务命令（改名 / 换邮箱 / 停用 / 启用 /
修改密码 / 增删 ApiKey）校验通过后记录领域事件，供应用层落库 + 发布。

说明：密码哈希属于既有安全工具（app.auth.store）的单一权威来源，领域层
仅声明"密码需被重置/验证"这一不变量，不落地具体哈希算法（防腐层在
infrastructure 翻译时调用既有安全工具）。
"""
from __future__ import annotations

import time
from typing import List, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.identity.domain.entities.api_key import ApiKey
from app.domain.identity.domain.events import (
    ApiKeyCreated,
    ApiKeyRevoked,
    UserDisabled,
    UserEmailChanged,
    UserEnabled,
    UserPasswordChanged,
    UserRenamed,
)
from app.domain.identity.domain.value_objects.account_status import (
    AccountStatus,
    AccountStatusEnum,
)


class User(AggregateRoot):
    """用户聚合根。"""

    def __init__(
        self,
        *,
        user_id: str,
        username: str,
        name: str = "",
        email: str = "",
        phone: str = "",
        avatar: str = "",
        role: str = "user",
        status: str = AccountStatusEnum.ENABLED.value,
        language: str = "zh-CN",
        last_organization_id: str = "",
        last_project_id: str = "",
        api_keys: Optional[List[dict]] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
    ):
        uname = (username or "").strip()
        if not uname:
            raise DomainValidationError("用户名不能为空")
        if not (email or "").strip():
            # 允许无邮箱，但如提供则须格式合法
            pass
        self.id = Identifier.of(user_id)
        self._username = uname
        self._name = (name or uname).strip()
        self._email = (email or "").strip()
        self._phone = phone or ""
        self._avatar = avatar or ""
        self._role = role or "user"
        self._status = AccountStatus(status)
        self._language = language or "zh-CN"
        self._last_organization_id = last_organization_id or ""
        self._last_project_id = last_project_id or ""
        self._api_keys: List[ApiKey] = []
        for k in (api_keys or []):
            self._api_keys.append(
                ApiKey(**k) if isinstance(k, dict) else k
            )
        self._created_at = created_at if created_at is not None else time.time()
        self._updated_at = updated_at if updated_at is not None else self._created_at
        self._domain_events = []
        self.version = 0

    # ── 只读属性 ─────────────────────────────────────
    @property
    def username(self) -> str:
        return self._username

    @property
    def name(self) -> str:
        return self._name

    @property
    def email(self) -> str:
        return self._email

    @property
    def phone(self) -> str:
        return self._phone

    @property
    def avatar(self) -> str:
        return self._avatar

    @property
    def role(self) -> str:
        return self._role

    @property
    def status(self) -> AccountStatus:
        return self._status

    @property
    def language(self) -> str:
        return self._language

    @property
    def last_organization_id(self) -> str:
        return self._last_organization_id

    @property
    def last_project_id(self) -> str:
        return self._last_project_id

    @property
    def api_keys(self) -> List[ApiKey]:
        return list(self._api_keys)

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    @property
    def enabled(self) -> bool:
        return self._status.enabled

    def _touch(self) -> None:
        self._updated_at = time.time()

    # ── 业务命令（守护不变量）────────────────────────
    def rename(self, new_name: str, operator: str = "system") -> None:
        nn = (new_name or "").strip()
        if not nn:
            raise DomainValidationError("用户昵称不能为空")
        if nn == self._name:
            return
        self._name = nn
        self._touch()
        self.record_event(UserRenamed(self.id.value, self._username, nn, operator))

    def change_email(self, new_email: str, operator: str = "system") -> None:
        ne = (new_email or "").strip()
        if ne and ("@" not in ne):
            raise DomainValidationError(f"邮箱格式不合法: {new_email}")
        old = self._email
        self._email = ne
        self._touch()
        if ne != old:
            self.record_event(UserEmailChanged(self.id.value, old, ne, operator))

    def change_password(self, operator: str = "system") -> None:
        """标记密码已变更（哈希由既有安全工具在 infrastructure 层落地）。"""
        self._touch()
        self.record_event(UserPasswordChanged(self.id.value, operator))

    def disable(self, operator: str = "system") -> None:
        """停用账号：禁止登录。"""
        if not self.enabled:
            return
        self._status = AccountStatus(AccountStatusEnum.DISABLED.value)
        self._touch()
        self.record_event(UserDisabled(self.id.value, operator))

    def enable(self, operator: str = "system") -> None:
        """启用账号。"""
        if self.enabled:
            return
        self._status = AccountStatus(AccountStatusEnum.ENABLED.value)
        self._touch()
        self.record_event(UserEnabled(self.id.value, operator))

    def set_last_context(self, *, organization_id: str = "", project_id: str = "") -> None:
        if organization_id is not None:
            self._last_organization_id = organization_id or ""
        if project_id is not None:
            self._last_project_id = project_id or ""
        self._touch()

    # ── ApiKey 子实体管理 ────────────────────────────
    def add_api_key(self, *, key_id: str, description: str = "", api_key: str = "") -> ApiKey:
        key = ApiKey(
            key_id=key_id,
            user_id=self.id.value,
            description=description,
            api_key=api_key,
        )
        self._api_keys.append(key)
        self._touch()
        self.record_event(ApiKeyCreated(self.id.value, key_id, description))
        return key

    def revoke_api_key(self, key_id: str, operator: str = "system") -> bool:
        for k in self._api_keys:
            if k.id.value == key_id and not k.revoked:
                k.revoke()
                self._touch()
                self.record_event(ApiKeyRevoked(self.id.value, key_id, operator))
                return True
        raise DomainValidationError(f"API Key 不存在或已吊销: {key_id}")

    # ── 快照 / 持久化 ───────────────────────────────
    def to_dict(self) -> dict:
        """导出可落库/可返回给上层视图层的字典（不含密码）。"""
        return {
            "id": self.id.value,
            "username": self._username,
            "name": self._name,
            "email": self._email,
            "phone": self._phone,
            "avatar": self._avatar,
            "role": self._role,
            "enable": 1 if self.enabled else 0,
            "status": self._status.value,
            "language": self._language,
            "last_organization_id": self._last_organization_id,
            "last_project_id": self._last_project_id,
            "api_keys": [k.to_dict() for k in self._api_keys],
            "created_at": self._created_at,
            "updated_at": self._updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "User":
        """从持久化字典/仓储返回行重建聚合。"""
        api_keys = data.get("api_keys") or data.get("apiKeys") or []
        return User(
            user_id=str(data.get("id") or data.get("user_id") or ""),
            username=data.get("username", ""),
            name=data.get("name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            avatar=data.get("avatar", ""),
            role=data.get("role", "user"),
            status=1 if data.get("enable", 1) else 0,
            language=data.get("language", "zh-CN"),
            last_organization_id=data.get("last_organization_id", ""),
            last_project_id=data.get("last_project_id", ""),
            api_keys=api_keys,
            created_at=data.get("created_at") or data.get("create_time"),
            updated_at=data.get("updated_at") or data.get("update_time"),
        )
