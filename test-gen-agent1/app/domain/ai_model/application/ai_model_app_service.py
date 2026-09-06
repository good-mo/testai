"""AI 模型源应用服务（Application Service / Use Case 门面）。"""
from __future__ import annotations

from typing import Optional

from app.domain.ai_model.application.dto import (
    CreateModelCommand,
    DeleteModelCommand,
    GetModelCommand,
    ListModelsCommand,
    UpdateModelCommand,
)
from app.domain.ai_model.domain.entities.ai_model import (
    OWNER_TYPE_SYSTEM,
    AiModelSource,
)
from app.domain.ai_model.domain.exceptions import AiModelNotFound
from app.domain.ai_model.infrastructure.ai_model_repository_impl import (
    AiModelRepoAdapter,
)


class AiModelAppService:
    """AI 模型源用例编排服务。"""

    def __init__(self, repo=None):
        self._repo = repo or AiModelRepoAdapter()

    def list(self, cmd: ListModelsCommand) -> list:
        """列表查询。"""
        models = self._repo.list(
            owner_type=cmd.owner_type,
            owner=cmd.owner,
            keyword=cmd.keyword,
            provider_name=cmd.provider_name,
        )
        return [m.to_dict() for m in models]

    def get(self, cmd: GetModelCommand) -> Optional[dict]:
        """获取单个模型。"""
        m = self._repo.get(cmd.model_id)
        return m.to_dict() if m else None

    def create(self, cmd: CreateModelCommand) -> dict:
        """新建模型源。"""
        model = AiModelSource(
            model_id=self._repo.next_id(),
            name=cmd.name,
            model_type=cmd.model_type,
            provider_name=cmd.provider_name,
            permission_type=cmd.permission_type,
            status=cmd.status,
            owner=cmd.owner,
            owner_type=cmd.owner_type,
            base_name=cmd.base_name,
            app_key=cmd.app_key,
            api_url=cmd.api_url,
            adv_settings=cmd.adv_settings,
            description=cmd.description,
            create_user=cmd.create_user,
            _created=True,
        )
        saved = self._repo.save(model)
        return saved.to_dict()

    def update(self, cmd: UpdateModelCommand) -> Optional[dict]:
        """更新模型源。"""
        model = self._repo.get(cmd.model_id)
        if not model:
            raise AiModelNotFound(f"模型源 {cmd.model_id} 不存在")
        model.update_settings(
            name=cmd.name, provider_name=cmd.provider_name,
            base_name=cmd.base_name, api_url=cmd.api_url,
            app_key=cmd.app_key, adv_settings=cmd.adv_settings,
            description=cmd.description,
            permission_type=cmd.permission_type, status=cmd.status,
        )
        saved = self._repo.save(model)
        return saved.to_dict()

    def delete(self, cmd: DeleteModelCommand) -> bool:
        """删除模型源。"""
        return self._repo.delete(cmd.model_id)

    def upsert(self, data: dict, create_user: str = "admin") -> dict:
        """按 id 存在则更新、否则新建（兼容 edit-source）。"""
        model_id = str(data.get("id") or "")
        if model_id:
            existing = self._repo.get(model_id)
            if existing:
                return self.update(UpdateModelCommand(
                    model_id=model_id,
                    name=data.get("name"),
                    provider_name=data.get("providerName"),
                    base_name=data.get("baseName"),
                    api_url=data.get("apiUrl"),
                    app_key=data.get("appKey"),
                    adv_settings=data.get("advSettingDTOList"),
                    description=data.get("description"),
                    permission_type=data.get("permissionType"),
                    status=data.get("status"),
                    create_user=create_user,
                ))
        return self.create(CreateModelCommand(
            name=data.get("name", ""),
            model_type=data.get("type", "LLM"),
            provider_name=data.get("providerName", ""),
            permission_type=data.get("permissionType", "PUBLIC"),
            status=bool(data.get("status", True)),
            owner=data.get("owner", ""),
            owner_type=data.get("ownerType", OWNER_TYPE_SYSTEM),
            base_name=data.get("baseName", ""),
            app_key=data.get("appKey", ""),
            api_url=data.get("apiUrl", ""),
            adv_settings=data.get("advSettingDTOList") or [],
            description=data.get("description", ""),
            create_user=create_user,
        ))


# 模块级单例
ai_model_app_service = AiModelAppService()
