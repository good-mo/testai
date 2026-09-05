# app/services/datafactory_service.py
"""数据工厂业务逻辑门面（Phase 4 · DDD A→B→C 迁移 — 阶段 C 瘦身）。

原 `DatafactoryService` 直接对接 DatafactoryRepo 做业务编排；**阶段 C**后
收敛为**薄门面**：核心生命周期一律委托 DDD `datafactory_app_service`（业务
规则/不变量已下沉到 `app/domain/datafactory/domain/`），本层仅保留方法签名
与异常语义的向后兼容，供历史调用方与契约测试沿用，不写任何新业务规则。

数据访问权威仍在 `app/domain/datafactory/infrastructure/` 的防腐适配器，
其内部复用既有 DatafactoryRepo 存储实现。
"""
from typing import Optional

from app.core.exceptions import NotFoundError
from app.domain.common.exceptions import AggregateNotFound, DomainValidationError
from app.domain.datafactory.application.datafactory_app_service import (
    datafactory_app_service,
)
from app.domain.datafactory.application.dto import (
    CleanupCommand,
    CreateTemplateCommand,
    GenerateCommand,
    TemplateListQuery,
    UpdateTemplateCommand,
)
from app.domain.datafactory.application.web_mapper import batch_generate_payload

_SVC = datafactory_app_service


class DatafactoryService:
    """数据工厂薄门面（委托 DDD 应用服务）。"""

    def list_templates(self, category: Optional[str] = None,
                       search: Optional[str] = None, limit: int = 100,
                       offset: int = 0) -> list:
        return _SVC.list_templates(TemplateListQuery(
            category=category or "", search=search or "",
            limit=limit, offset=offset,
        )).get("list", [])

    def create_template(self, name: str, description: str = "",
                        category: str = "", schema_def: dict = None,
                        deps: list = None, tags: list = None) -> dict:
        try:
            return _SVC.create_template(CreateTemplateCommand(
                name=name, description=description, category=category,
                schema_def=schema_def, deps=deps, tags=tags,
            ))
        except DomainValidationError as exc:
            raise ValueError(exc.message) from exc

    def get_template(self, template_id: str) -> Optional[dict]:
        return _SVC.get_template(template_id)

    def update_template(self, template_id: str, **kwargs) -> Optional[dict]:
        # 与既有 create 对齐：请求体字段 schema_def 映射到领域 schema
        schema_def = kwargs.pop("schema_def", kwargs.get("schema"))
        schema_def = schema_def if schema_def is not None else kwargs.get("schema")
        try:
            return _SVC.update_template(UpdateTemplateCommand(
                template_id=template_id,
                name=kwargs.get("name"),
                description=kwargs.get("description"),
                category=kwargs.get("category"),
                schema_def=schema_def,
                deps=kwargs.get("deps"),
                tags=kwargs.get("tags"),
                status=kwargs.get("status"),
            ))
        except AggregateNotFound:
            return None

    def delete_template(self, template_id: str) -> bool:
        try:
            return _SVC.delete_template(template_id)
        except AggregateNotFound:
            return False

    def generate_data(self, template_id: str = "", batch_size: int = 1,
                      env_key: str = "") -> dict:
        """按模板造数；模板不存在抛 NotFoundError（404），沿用既有语义。"""
        if not _SVC.get_template(template_id):
            raise NotFoundError(f"数据模板 {template_id} 不存在")
        batch = _SVC.generate(GenerateCommand(
            template_id=template_id, batch_size=batch_size, env_key=env_key,
        ))
        return batch_generate_payload(batch)

    def list_batches(self, limit: int = 50) -> list:
        return _SVC.list_batches(limit=limit).get("batches", [])

    def cleanup_batch(self, batch_id: str) -> bool:
        try:
            return bool(_SVC.cleanup_batch(CleanupCommand(batch_id=batch_id)))
        except AggregateNotFound:
            return False

    def cleanup_by_template(self, template_id: str) -> int:
        return _SVC.cleanup_by_template(template_id)

    def cleanup_by_env(self, env_key: str) -> int:
        return _SVC.cleanup_by_env(env_key)

    def get_stats(self) -> dict:
        return _SVC.stats()


datafactory_service = DatafactoryService()
