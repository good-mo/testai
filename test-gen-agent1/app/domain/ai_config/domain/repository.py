"""AI 配置聚合仓储接口（Repository Port）。"""
from __future__ import annotations

from typing import Optional, Protocol

from app.domain.ai_config.domain.entities.ai_config import AiConfig


class AiConfigRepository(Protocol):
    """AI 配置聚合仓储契约。"""

    def next_id(self) -> str: ...
    def save(self, config: AiConfig) -> AiConfig: ...
    def get(self, scope: str, owner: str = "", project_id: str = "",
            config_type: str = "default") -> Optional[AiConfig]: ...
    def delete(self, scope: str, owner: str = "", project_id: str = "",
               config_type: str = "default") -> bool: ...


__all__ = ["AiConfigRepository"]
