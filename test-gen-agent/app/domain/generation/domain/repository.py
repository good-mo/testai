"""生成任务聚合仓储接口（Repository Port）。

仅在 domain 层定义、由 infrastructure 实现。应用层依赖此接口而非具体
实现，便于测试替换（内存仓储）与多存储切换。仓储粒度为"聚合"：
GenerationJob 及其内聚的步骤/修复循环作为一个整体被读取/保存。
"""
from __future__ import annotations

from typing import List, Optional, Protocol, Tuple

from app.domain.generation.domain.entities.generation_job import GenerationJob


class GenerationJobRepository(Protocol):
    """生成任务聚合仓储契约。"""

    def next_id(self) -> str: ...

    def save(self, job: GenerationJob) -> Optional[GenerationJob]: ...

    def update(self, job: GenerationJob) -> bool: ...

    def find_by_id(self, job_id: str) -> Optional[GenerationJob]: ...

    def list_jobs(self, *, file_path: str = "", source: str = "",
                  passed: Optional[bool] = None, status: str = "",
                  search: str = "", limit: int = 50,
                  offset: int = 0) -> Tuple[List[GenerationJob], int]: ...

    def delete_by_id(self, job_id: str) -> bool: ...

    def stats(self) -> dict: ...


__all__ = ["GenerationJobRepository"]
