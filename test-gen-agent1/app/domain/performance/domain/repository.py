"""性能测试聚合仓储接口（Repository Port）。

仅在 domain 层定义、由 infrastructure 实现。应用层依赖此接口而非具体
实现，便于测试替换（内存仓储）与多存储切换。仓储粒度为「聚合」：
PerformanceTest 及其值对象作为一个整体被读取/保存，保证事务一致性。
"""
from __future__ import annotations

from typing import List, Optional, Protocol, Tuple

from app.domain.performance.domain.entities.performance_test import PerformanceTest


class PerformanceRepository(Protocol):
    """性能测试聚合仓储契约。"""

    def next_id(self) -> str: ...

    def save(self, test: PerformanceTest) -> PerformanceTest: ...

    def find_by_id(self, test_id: str) -> Optional[PerformanceTest]: ...

    def update(self, test: PerformanceTest) -> Optional[PerformanceTest]: ...

    def list(
        self,
        *,
        status: str = "",
        target_name: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[PerformanceTest], int]: ...

    def delete(self, test_id: str) -> bool: ...
