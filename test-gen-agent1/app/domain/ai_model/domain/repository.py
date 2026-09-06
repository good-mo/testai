"""AI 模型源聚合仓储接口（Repository Port）。"""
from __future__ import annotations

from typing import List, Optional, Protocol

from app.domain.ai_model.domain.entities.ai_model import AiModelSource


class AiModelRepository(Protocol):
    """AI 模型源聚合仓储契约。"""

    def next_id(self) -> str: ...
    def save(self, model: AiModelSource) -> AiModelSource: ...
    def get(self, model_id: str) -> Optional[AiModelSource]: ...
    def list(self, owner_type: str = "SYSTEM", owner: str = "",
             keyword: str = "", provider_name: str = "") -> List[AiModelSource]: ...
    def delete(self, model_id: str) -> bool: ...


__all__ = ["AiModelRepository"]
