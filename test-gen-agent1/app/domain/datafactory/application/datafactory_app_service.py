"""数据工厂应用服务（Application Service / Use Case 门面）。

职责：
  1. 作为路由器与领域层之间的唯一用例编排入口；
  2. 承载事务边界：加载聚合 → 执行领域命令 → 保存聚合 → 发布领域事件；
  3. 将领域异常透传给上层（由 Web 层统一翻译为 HTTP 响应）。

保持瘦：只做编排，不写业务规则（业务规则在领域层聚合/服务内）。
"""
from __future__ import annotations

import logging
from typing import Optional

from app.domain.common.domain_events import event_bus
from app.domain.common.exceptions import AggregateNotFound
from app.domain.datafactory.application.dto import (
    CleanupCommand,
    CreateTemplateCommand,
    GenerateCommand,
    TemplateListQuery,
    UpdateTemplateCommand,
)
from app.domain.datafactory.domain.entities.data_template import DataTemplate
from app.domain.datafactory.domain.repository import DataFactoryRepository
from app.domain.datafactory.infrastructure.datafactory_repository_impl import (
    DataFactoryRepoAdapter,
)

logger = logging.getLogger(__name__)


class DataFactoryAppService:
    """数据工厂用例编排服务。"""

    def __init__(self, repo: DataFactoryRepository = None):
        # 允许依赖注入（便于测试替身）；默认使用既有存储适配器
        self._repo: DataFactoryRepository = repo or DataFactoryRepoAdapter()

    # ── 模板 CRUD ─────────────────────────────────────
    def create_template(self, cmd: CreateTemplateCommand) -> dict:
        template = DataTemplate(
            template_id=self._repo.next_template_id(),
            name=cmd.name,
            description=cmd.description,
            category=cmd.category,
            schema=cmd.schema_def,
            deps=cmd.deps,
            tags=cmd.tags,
            _created=True,
        )
        saved = self._repo.save_template(template)
        self._publish(template)
        return (saved or template).to_dict()

    def get_template(self, template_id: str) -> Optional[dict]:
        template = self._repo.find_template_by_id(template_id)
        return template.to_dict() if template else None

    def update_template(self, cmd: UpdateTemplateCommand) -> Optional[dict]:
        template = self._find_template_or_raise(cmd.template_id)
        if cmd.name is not None:
            template.rename(cmd.name, cmd.operator)
        if cmd.description is not None:
            template.change_description(cmd.description, cmd.operator)
        if cmd.category is not None:
            template.change_category(cmd.category, cmd.operator)
        if cmd.schema_def is not None:
            template.set_schema(cmd.schema_def, cmd.operator)
        if cmd.deps is not None:
            template.set_deps(cmd.deps, cmd.operator)
        if cmd.tags is not None:
            template.set_tags(cmd.tags, cmd.operator)
        if cmd.status is not None:
            template.set_status(cmd.status, cmd.operator)
        self._repo.update_template(template)
        self._publish(template)
        return template.to_dict()

    def delete_template(self, template_id: str, operator: str = "system") -> bool:
        template = self._find_template_or_raise(template_id)
        template.delete(operator)
        deleted = self._repo.delete_template(template_id)
        self._publish(template)
        return deleted

    # ── 造数 / 批次 ──────────────────────────────────
    def generate(self, cmd: GenerateCommand) -> dict:
        template = self._find_template_or_raise(cmd.template_id)
        if not template.is_active:
            raise AggregateNotFound(f"数据模板 {cmd.template_id} 已停用，无法造数")
        batch = self._repo.generate_batch(template, cmd.batch_size, cmd.env_key)
        self._publish(batch)
        return batch.to_dict()

    def list_batches(self, limit: int = 50) -> dict:
        items = self._repo.list_batches(limit=limit)
        return {"batches": [b.to_dict() for b in items], "total": len(items)}

    # ── 清理 ─────────────────────────────────────────
    def cleanup_batch(self, cmd: CleanupCommand) -> bool:
        batch = self._repo.find_batch_by_id(cmd.batch_id)
        if batch is None:
            raise AggregateNotFound(f"数据批次 {cmd.batch_id} 不存在")
        batch.clean(cmd.operator)
        self._repo.clean_batch(batch.id.value)
        self._publish(batch)
        return True

    def cleanup_by_template(self, template_id: str,
                            env_key: str = "", operator: str = "system") -> int:
        return self._repo.clean_batches_by_template(template_id, env_key)

    def cleanup_by_env(self, env_key: str, operator: str = "system") -> int:
        return self._repo.clean_batches_by_env(env_key)

    # ── 查询 / 统计 ─────────────────────────────────
    def list_templates(self, query: TemplateListQuery) -> dict:
        items = self._repo.list_templates(
            category=query.category, search=query.search,
            limit=query.limit, offset=query.offset,
        )
        return {"list": [t.to_dict() for t in items], "total": len(items)}

    def stats(self) -> dict:
        return self._repo.stats()

    # ── 内部助手 ────────────────────────────────────
    def _find_template_or_raise(self, template_id: str) -> DataTemplate:
        template = self._repo.find_template_by_id(template_id)
        if template is None:
            raise AggregateNotFound(f"数据模板不存在: {template_id}")
        return template

    @staticmethod
    def _publish(agg) -> None:
        events = agg.pull_domain_events()
        for ev in events:
            event_bus.dispatch(ev)


# 单例门面（进程内复用）
datafactory_app_service = DataFactoryAppService()

__all__ = ["DataFactoryAppService", "datafactory_app_service"]
