"""任务运行聚合仓储接口（Repository Port）。

仅在 domain 层定义、由 infrastructure 实现。应用层依赖此接口而非具体
实现，便于测试替换（内存仓储）与多存储切换。仓储粒度为"聚合"。

包含两套契约：
  - TaskRepository：任务中心（TaskCenter）生命周期；
  - RunRecordRepository：运行记录 / 报告（run_records）通用能力。
"""
from __future__ import annotations

from typing import List, Optional, Protocol, Tuple

from app.domain.runs.domain.entities.run_record import RunRecord
from app.domain.runs.domain.entities.task import Task


class TaskRepository(Protocol):
    """任务聚合仓储契约（对接 app.repositories.task_repo）。"""

    def next_id(self) -> str: ...

    def save(self, task: Task) -> Task: ...

    def find_by_id(self, task_id: str) -> Optional[Task]: ...

    def list_recent(self, limit: int = 50) -> List[Task]: ...

    def list_pending(self) -> List[Task]: ...

    def delete(self, task_id: str) -> bool: ...

    def claim_next_pending(self, worker_id: str = "") -> Optional[Task]: ...


class RunRecordRepository(Protocol):
    """运行记录聚合仓储契约（对接 app.repositories.run_repo.RunRepo）。"""

    def next_id(self) -> str: ...

    def save(self, record: RunRecord) -> Optional[RunRecord]: ...

    def update(self, record: RunRecord) -> Optional[RunRecord]: ...

    def find_by_id(self, record_id: str) -> Optional[RunRecord]: ...

    def list_records(self, *, file_path: str = "", source: str = "",
                     passed: Optional[bool] = None, search: str = "",
                     limit: int = 50,
                     offset: int = 0) -> Tuple[List[RunRecord], int]: ...

    def stats(self) -> dict: ...

    def clear(self, source: str = "") -> int: ...

    def delete_by_id(self, record_id: str) -> bool: ...

    def delete_batch(self, record_ids: list) -> int: ...


__all__ = ["TaskRepository", "RunRecordRepository"]
