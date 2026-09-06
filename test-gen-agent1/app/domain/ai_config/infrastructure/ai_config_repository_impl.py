"""AI 配置聚合仓储实现（Adapter / Anti-Corruption Layer）。

将既有 AiConfigRepo 模块命令封装为面向 AiConfig 聚合的仓储接口。
"""
from __future__ import annotations

import uuid
from typing import Optional

from app.domain.ai_config.domain.entities.ai_config import AiConfig
from app.domain.common.entities import Identifier
from app.repositories.ai_config_repo import AiConfigRepo


class AiConfigRepoAdapter:
    """将既有 AiConfigRepo 封装为面向 AiConfig 聚合的仓储。"""

    def next_id(self) -> str:
        return uuid.uuid4().hex[:16]

    def save(self, config: AiConfig) -> AiConfig:
        """保存（AiConfigRepo.save 内部做 upsert），并回填真实落库主键。

        AiConfigRepo 以 scope+owner(+project_id) 为唯一 upsert 键并自行生成主键，
        新建时聚合预生成的 id 与落库 id 可能不一致。此处以落库返回的真实 id
        回填聚合 id，保证「返回 id == 落库 id」（避免后续按返回 id 读取落空）。
        """
        row = AiConfigRepo.save(
            scope=config.scope,
            config_value=config.config_value,
            owner=config.owner,
            project_id=config.project_id,
            create_user=config.create_user,
            config_type=config.config_type,
        )
        real_id = row.get("id") if row else None
        if real_id and config.id.value != real_id:
            config.id = Identifier.of(real_id)
        return config

    def get(self, scope: str, owner: str = "", project_id: str = "",
            config_type: str = "default") -> Optional[AiConfig]:
        """按 scope/owner/project_id 读取。"""
        row = AiConfigRepo.get(
            scope=scope, owner=owner, project_id=project_id,
            config_type=config_type,
        )
        return AiConfig.from_dict(dict(row)) if row else None

    def delete(self, scope: str, owner: str = "", project_id: str = "",
               config_type: str = "default") -> bool:
        """按 scope/owner/project_id 删除。"""
        return AiConfigRepo.delete(
            scope=scope, owner=owner, project_id=project_id,
            config_type=config_type,
        )
