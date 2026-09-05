"""TestInsight 聚合仓储接口（Repository Port）。

仅在 domain 层定义、由 infrastructure 实现。应用层依赖此接口而非具体
实现，便于测试替换（内存仓储）与多存储切换。仓储粒度为"聚合"：
TraceRun 作为整体被读取/保存，保证事务一致性。

此外提供溯源查询与统计（prove / stats），支撑"自证清白"与价值量化。
"""
from __future__ import annotations

from typing import List, Optional, Protocol, Tuple

from app.domain.test_insight.domain.entities.trace_run import TraceRun


class TestInsightRepository(Protocol):
    """执行追溯聚合仓储契约。"""

    def next_id(self) -> str: ...

    def save(self, run: TraceRun) -> TraceRun: ...

    def find_by_id(self, trace_id: str) -> Optional[TraceRun]: ...

    def list(self, *, file_path: str = "", result: str = "",
             limit: int = 50, offset: int = 0) -> Tuple[List[TraceRun], int]: ...

    def list_by_file(self, file_path: str, limit: int = 100) -> List[TraceRun]: ...

    def stats(self) -> dict: ...
