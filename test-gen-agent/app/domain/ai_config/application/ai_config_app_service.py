"""AI 配置应用服务（Application Service / Use Case 门面）。"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from app.domain.ai_config.application.dto import (
    DeleteAiConfigCommand,
    GetAiConfigCommand,
    SaveAiConfigCommand,
)
from app.domain.ai_config.domain.entities.ai_config import AiConfig
from app.domain.ai_config.infrastructure.ai_config_repository_impl import (
    AiConfigRepoAdapter,
)

logger = logging.getLogger(__name__)


class AiConfigAppService:
    """AI 配置用例编排服务。"""

    def __init__(self, repo=None):
        self._repo = repo or AiConfigRepoAdapter()

    def get(self, cmd: GetAiConfigCommand) -> Optional[dict]:
        """获取配置，不存在返回 None。"""
        saved = self._repo.get(
            scope=cmd.scope,
            owner=cmd.owner,
            project_id=cmd.project_id,
            config_type=cmd.config_type,
        )
        return saved.to_dict() if saved else None

    def save(self, cmd: SaveAiConfigCommand) -> dict:
        """保存配置（存在则更新、不存在则新建）。"""
        existing = self._repo.get(
            scope=cmd.scope,
            owner=cmd.owner,
            project_id=cmd.project_id,
            config_type=cmd.config_type,
        )
        if existing:
            existing.update_value(cmd.config_value)
            saved = self._repo.save(existing)
        else:
            config = AiConfig(
                config_id=str(uuid.uuid4().hex[:16]),
                scope=cmd.scope,
                config_type=cmd.config_type,
                owner=cmd.owner,
                project_id=cmd.project_id,
                config_value=cmd.config_value,
                create_user=cmd.create_user,
                _created=True,
            )
            saved = self._repo.save(config)
        return saved.to_dict()

    def delete(self, cmd: DeleteAiConfigCommand) -> bool:
        """删除配置。"""
        return self._repo.delete(
            scope=cmd.scope,
            owner=cmd.owner,
            project_id=cmd.project_id,
            config_type=cmd.config_type,
        )


# 模块级单例
ai_config_app_service = AiConfigAppService()
