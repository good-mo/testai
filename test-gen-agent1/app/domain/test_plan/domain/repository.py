"""测试计划聚合仓储接口（Repository Port）。

仅在 domain 层定义、由 infrastructure 实现。应用层依赖此接口而非具体
实现，便于测试替换（内存仓储）与多存储切换。仓储粒度为"聚合"：TestPlan
及其关联用例作为一个整体被读取/保存，保证事务一致性。
"""
from __future__ import annotations

from typing import List, Optional, Protocol, Tuple

from app.domain.test_plan.domain.entities.test_plan import TestPlan


class TestPlanRepository(Protocol):
    """测试计划聚合仓储契约。"""

    def next_id(self) -> str: ...

    def save(self, plan: TestPlan) -> TestPlan: ...

    def update(self, plan: TestPlan) -> Optional[TestPlan]: ...

    def find_by_id(self, plan_id: str) -> Optional[TestPlan]: ...

    def delete(self, plan_id: str) -> bool: ...

    def archive(self, plan_id: str) -> bool: ...

    def list(self, *, keyword: str = "", status: str = "", project_id: str = "",
             module_ids: Optional[List[str]] = None, plan_type: str = "",
             group_id: str = "",
             limit: int = 100, offset: int = 0) -> Tuple[List[TestPlan], int]: ...

    def statistics(self, plan_id: str) -> dict: ...

    def statistics_bulk(self, plan_ids: List[str]) -> dict: ...
