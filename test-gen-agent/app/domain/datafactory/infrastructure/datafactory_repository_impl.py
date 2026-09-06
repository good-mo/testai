"""数据工厂聚合仓储实现（Adapter 防腐层）。

把"面向聚合的仓储接口"翻译为既有 DatafactoryRepo（四层 Repository）的
命令。复用已验证的存储逻辑，同时让领域层获得聚合级读写语义；后续如需
换存储仅替换本文件。

说明：既有 DatafactoryRepo.generate_data 承担"按模板造数 + 落库批次"
的原子操作，其造数算法（字段策略）正是 domain.services.data_gen_policy
所建模的同一套规则。因此本适配器对批次生成直接委托 generate_data，并把
返回结果重建为 DataBatch 聚合，避免在领域层重复实现同一条生成规则。

> 反腐蚀（Anti-Corruption）：历史遗留数据/既有测试可能以仓库直写方式落
> 库，其 `category` 不在领域枚举内（领域在**写入命令**路径严格校验，
> 但对历史行需容忍）。本适配器在聚合水合（hydration）边界做归一化：
> 遇到超出领域类别的历史行，回落为 custom 而非让读取崩溃，保证"读旧
> 数据不回归"；新写入仍由领域层 Category 严格守护。
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from app.domain.datafactory.domain.entities.data_batch import DataBatch
from app.domain.datafactory.domain.entities.data_template import DataTemplate
from app.domain.datafactory.domain.value_objects.category import VALID as CATEGORY_VALID
from app.domain.datafactory.infrastructure.datafactory_store import DatafactoryRepo


def _normalize_category(row: dict) -> dict:
    """把历史行的非法类别归一化为 custom（仅在读取/水合路径）。"""
    data = dict(row)
    cat = str(data.get("category", "")).lower()
    if cat and cat not in CATEGORY_VALID:
        data["category"] = "custom"
    return data


class DataFactoryRepoAdapter:
    """将既有 DatafactoryRepo 封装为面向聚合的仓储。"""

    # ── 标识生成（沿用既有主键策略）─────────────────
    def next_template_id(self) -> str:
        return uuid.uuid4().hex[:12]

    # ── 模板：读 / 写 ───────────────────────────────
    def find_template_by_id(self, template_id: str) -> Optional[DataTemplate]:
        row = DatafactoryRepo.get_template(template_id)
        return DataTemplate.from_dict(_normalize_category(dict(row))) if row else None

    def save_template(self, template: DataTemplate) -> DataTemplate:
        d = template.to_dict()
        # 既有 DatafactoryRepo.create_template 自行分配主键；落库后以返回
        # 行重建聚合，确保聚合 id 与存储一致。
        created = DatafactoryRepo.create_template(
            name=d["name"], description=d["description"], category=d["category"],
            schema=d["schema"], deps=d["deps"], tags=d["tags"],
        )
        return DataTemplate.from_dict(_normalize_category(dict(created))) if created else template

    def update_template(self, template: DataTemplate) -> Optional[DataTemplate]:
        d = template.to_dict()
        updated = DatafactoryRepo.update_template(
            template.id.value,
            name=d["name"], description=d["description"], category=d["category"],
            schema=d["schema"], deps=d["deps"], tags=d["tags"], status=d["status"],
        )
        return DataTemplate.from_dict(_normalize_category(dict(updated))) if updated else None

    def delete_template(self, template_id: str) -> bool:
        return DatafactoryRepo.delete_template(template_id)

    def list_templates(self, *, category: str = "", search: str = "",
                       limit: int = 100, offset: int = 0) -> List[DataTemplate]:
        rows = DatafactoryRepo.list_templates(
            category=category or None, search=search or None,
            limit=limit, offset=offset,
        )
        return [DataTemplate.from_dict(_normalize_category(dict(r))) for r in rows]

    # ── 批次：生成 / 清理 / 统计 ─────────────────────
    def generate_batch(self, template: DataTemplate, batch_size: int,
                       env_key: str = "") -> DataBatch:
        result = DatafactoryRepo.generate_data(
            template_id=template.id.value, batch_size=batch_size, env_key=env_key,
        )
        if not result:
            raise RuntimeError("生成数据批次失败")
        # 以落库结果为权威（含实际分配的 batch_id / template_name）
        batch = DataBatch(
            batch_id=result.get("batch_id"),
            template_id=result.get("template_id", template.id.value),
            template_name=result.get("template_name", template.name),
            batch_size=result.get("batch_size", batch_size),
            env_key=result.get("env_key", env_key),
            data=result.get("data") or [],
        )
        return batch

    def find_batch_by_id(self, batch_id: str) -> Optional[DataBatch]:
        for r in DatafactoryRepo.list_batches(limit=9999):
            if str(r.get("id")) == str(batch_id):
                return DataBatch.from_dict(dict(r))
        return None

    def list_batches(self, limit: int = 50) -> List[DataBatch]:
        rows = DatafactoryRepo.list_batches(limit=limit)
        return [DataBatch.from_dict(dict(r)) for r in rows]

    def clean_batch(self, batch_id: str) -> bool:
        return DatafactoryRepo.cleanup_batch(batch_id)

    def clean_batches_by_template(self, template_id: str, env_key: str = "") -> int:
        return DatafactoryRepo.cleanup_by_template(template_id, env_key=env_key or "default")

    def clean_batches_by_env(self, env_key: str) -> int:
        return DatafactoryRepo.cleanup_by_env(env_key)

    def stats(self) -> dict:
        return DatafactoryRepo.stats()


# 单例（进程内复用）
datafactory_repository = DataFactoryRepoAdapter()

__all__ = ["DataFactoryRepoAdapter", "datafactory_repository"]
