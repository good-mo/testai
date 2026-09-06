"""AI 模型源聚合仓储实现（Adapter / Anti-Corruption Layer）。"""
from __future__ import annotations

import uuid
from typing import List, Optional

from app.domain.ai_model.domain.entities.ai_model import AiModelSource
from app.repositories.ai_model_repo import ai_model_repo


class AiModelRepoAdapter:
    """将既有 ai_model_repo 封装为面向 AiModelSource 聚合的仓储。"""

    def next_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def save(self, model: AiModelSource) -> AiModelSource:
        data = {
            # 携带聚合根 id：确保新建/更新走的是同一物理行，落库 id 与
            # 聚合 id 一致（避免 repo 侧二次自增导致「返回 id ≠ 落库 id」）。
            "id": model.id.value,
            "name": model.name,
            "type": model.model_type,
            "providerName": model.provider_name,
            "permissionType": model.permission_type,
            "status": model.status,
            "owner": model.owner,
            "ownerType": model.owner_type,
            "baseName": model.base_name,
            "appKey": model.app_key,
            "apiUrl": model.api_url,
            "advSettingDTOList": model.adv_settings,
        }
        creator = getattr(model, "_create_user", None) or "admin"
        # 更新或新建
        existing = ai_model_repo.get(model.id.value)
        if existing:
            ai_model_repo.update(model.id.value, data, update_user=creator)
        else:
            ai_model_repo.create(data, create_user=creator)
        return model

    def get(self, model_id: str) -> Optional[AiModelSource]:
        row = ai_model_repo.get(model_id)
        return AiModelSource.from_dict(dict(row)) if row else None

    def list(self, owner_type: str = "SYSTEM", owner: str = "",
             keyword: str = "", provider_name: str = "") -> List[AiModelSource]:
        rows = ai_model_repo.list(
            owner_type=owner_type, owner=owner,
            keyword=keyword, provider_name=provider_name,
        )
        return [AiModelSource.from_dict(dict(r)) for r in rows]

    def delete(self, model_id: str) -> bool:
        return ai_model_repo.delete(model_id)
