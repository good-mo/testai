"""AI 用例生成配置聚合根 AiConfig。

聚合边界：
  - AiConfig（聚合根）：按 scope+owner+project_id 区分的配置项
  - 配置值（config_value）为聚合内嵌 JSON 结构
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from app.domain.ai_config.domain.events import (
    AiConfigCreated,
    AiConfigUpdated,
)
from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError

# scope 常量
SCOPE_FUNCTIONAL_CASE = "functional_case"
SCOPE_API_CASE = "api_case"


class AiConfig(AggregateRoot):
    """AI 用例生成配置聚合根。"""

    def __init__(
        self,
        *,
        config_id: str,
        scope: str = SCOPE_FUNCTIONAL_CASE,
        config_type: str = "default",
        owner: str = "",
        owner_type: str = "PERSONAL",
        project_id: str = "",
        config_value: Optional[dict] = None,
        create_user: str = "admin",
        create_time: Optional[float] = None,
        update_time: Optional[float] = None,
        _created: bool = False,
    ):
        if not config_id:
            raise DomainValidationError("配置 ID 不能为空")
        if scope not in (SCOPE_FUNCTIONAL_CASE, SCOPE_API_CASE):
            raise DomainValidationError(f"非法 scope: {scope}")
        self.id = Identifier.of(config_id)
        self._scope = scope
        self._config_type = config_type or "default"
        self._owner = owner or ""
        self._owner_type = owner_type or "PERSONAL"
        self._project_id = project_id or ""
        self._config_value = dict(config_value or {})
        self._create_user = create_user or "admin"
        now = time.time()
        self._create_time = create_time if create_time is not None else now
        self._update_time = update_time if update_time is not None else now
        self._domain_events = []
        self.version = 0
        if _created:
            self.record_event(AiConfigCreated(
                self.id.value, self._scope, self._owner, self._project_id))

    # ── 只读属性 ─────────────────────────────────────
    @property
    def scope(self) -> str:
        return self._scope

    @property
    def config_type(self) -> str:
        return self._config_type

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def owner_type(self) -> str:
        return self._owner_type

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def config_value(self) -> Dict[str, Any]:
        return dict(self._config_value)

    @property
    def create_user(self) -> str:
        return self._create_user

    @property
    def create_time(self) -> float:
        return self._create_time

    @property
    def update_time(self) -> float:
        return self._update_time

    # ── 业务命令 ─────────────────────────────────────
    def update_value(self, config_value: Dict[str, Any]) -> None:
        """更新配置值。"""
        if not isinstance(config_value, dict):
            raise DomainValidationError("配置值必须是字典")
        self._config_value = dict(config_value)
        self._update_time = time.time()
        self.record_event(AiConfigUpdated(self.id.value, self._scope))

    # ── 持久化 ───────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "config_id": self.id.value,
            "id": self.id.value,
            "scope": self._scope,
            "config_type": self._config_type,
            "owner": self._owner,
            "owner_type": self._owner_type,
            "project_id": self._project_id,
            "config_value": self._config_value,
            "create_user": self._create_user,
            "create_time": self._create_time,
            "update_time": self._update_time,
        }

    @staticmethod
    def from_dict(data: dict) -> "AiConfig":
        # 兼容两条读取路径：
        #   1) DDD 内部持久化的 snake_case（config_value / config_type / owner_type）
        #   2) 底层 AiConfigRepo 输出的 camelCase 行（config / configType / ownerType）
        #      —— 避免「读聚合→改值→存回」因字段名漂移把配置值读成空。
        cfg = data.get("config_value")
        if cfg is None:
            cfg = data.get("config")
        if not isinstance(cfg, dict):
            cfg = {}
        return AiConfig(
            config_id=str(data.get("config_id") or data.get("id") or ""),
            scope=data.get("scope", SCOPE_FUNCTIONAL_CASE),
            config_type=data.get("config_type") or data.get("configType") or "default",
            owner=data.get("owner", ""),
            owner_type=(data.get("owner_type") or data.get("ownerType")
                        or "PERSONAL").strip(),
            project_id=data.get("project_id") or data.get("projectId") or "",
            config_value=cfg,
            create_user=data.get("create_user") or data.get("createUser") or "admin",
            create_time=data.get("create_time"),
            update_time=data.get("update_time"),
        )
