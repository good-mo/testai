"""用例聚合仓储接口（Repository Port）。

面向聚合的仓储接口，仅在 domain 层定义、由 infrastructure 实现。
应用层依赖此接口而非具体实现，从而保持领域/应用层对存储的零依赖，
便于测试替换（内存仓储）与多存储切换。

仓储的粒度是"聚合"：TestCase 及其内聚的子实体/值对象作为一个整体
被读取/保存，保证事务一致性（无论底层是单表还是多表）。
"""
from __future__ import annotations

from typing import List, Optional, Protocol, Tuple

from app.domain.cases.domain.entities.case import TestCase


class CaseRepository(Protocol):
    """测试用例聚合仓储契约。"""

    def next_id(self) -> str: ...

    def save(self, case: TestCase) -> TestCase: ...

    def update(self, case: TestCase) -> bool: ...

    def find_by_id(self, case_id: str) -> Optional[TestCase]: ...

    def soft_delete(self, case_id: str, deleted_by: str = "", reason: str = "") -> bool: ...

    def restore(self, case_id: str, operator: str = "") -> bool: ...

    def find_deleted(self, case_id: str) -> Optional[TestCase]: ...

    def list_deleted(self, limit: int = 100, offset: int = 0) -> Tuple[List[TestCase], int]: ...

    def list_cases(self, *, status: str = "", priority: str = "", tag: str = "",
                   search: str = "", test_type: str = "", module_id: str = "",
                   limit: int = 100, offset: int = 0) -> Tuple[List[TestCase], int]: ...

    def create_version(self, case_id: str, snapshot: dict, version: int,
                       operator: str = "", change_desc: str = "") -> int: ...

    def record_change(self, case_id: str, action: str, field: str = "",
                      old_value: str = "", new_value: str = "", operator: str = "") -> None: ...

    def invalidate_mindmap_cache(self) -> None: ...

    # ── 导入 / 导出（格式工具能力，经仓储透传既有 CaseRepo）──
    def export_excel(self, cases: list) -> bytes: ...

    def export_mindmap(self, cases: list = None) -> str: ...

    def import_excel(self, content: str, operator: str = "") -> dict: ...

    def import_mindmap(self, content: str, operator: str = "") -> dict: ...
