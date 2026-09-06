"""数据工厂聚合仓储接口（Repository Port）。

仅在 domain 层定义、由 infrastructure 实现。应用层依赖此接口而非具体
实现，便于测试替换（内存仓储）与多存储切换。仓储粒度为"聚合"：模板及
其生成的批次作为一个整体被读取/保存。
"""
from __future__ import annotations

from typing import List, Optional, Protocol

from app.domain.datafactory.domain.entities.data_batch import DataBatch
from app.domain.datafactory.domain.entities.data_template import DataTemplate


class DataFactoryRepository(Protocol):
    """数据工厂聚合仓储契约。"""

    # ── 模板 ─────────────────────────────────────────
    def next_template_id(self) -> str: ...

    def save_template(self, template: DataTemplate) -> DataTemplate: ...

    def update_template(self, template: DataTemplate) -> Optional[DataTemplate]: ...

    def find_template_by_id(self, template_id: str) -> Optional[DataTemplate]: ...

    def delete_template(self, template_id: str) -> bool: ...

    def list_templates(self, *, category: str = "", search: str = "",
                       limit: int = 100, offset: int = 0) -> List[DataTemplate]: ...

    # ── 批次（生成 / 清理 / 统计）────────────────────
    def generate_batch(self, template: DataTemplate, batch_size: int,
                       env_key: str = "") -> DataBatch: ...

    def find_batch_by_id(self, batch_id: str) -> Optional[DataBatch]: ...

    def list_batches(self, limit: int = 50) -> List[DataBatch]: ...

    def clean_batch(self, batch_id: str) -> bool: ...

    def clean_batches_by_template(self, template_id: str, env_key: str = "") -> int: ...

    def clean_batches_by_env(self, env_key: str) -> int: ...

    def stats(self) -> dict: ...


__all__ = ["DataFactoryRepository"]
