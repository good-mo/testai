"""性能测试基础设施层：内存仓储 + 既有引擎适配。

防腐层 / Adapter，把「面向聚合的仓储接口」与「把被测函数跑成领域指标」
翻译为真实实现：
  1. InMemoryPerformanceRepository —— 进程内内存仓储（适合该上下文当前
     尚无独立持久表；跨请求可迁移到 run 的 performance_report 或独立表）。
  2. EngineBenchmarkRunner —— 复用既有 `app/performance` 基准引擎跑出
     领域 `PerformanceMetrics`，避免重复实现计时/内存采集。
"""
from __future__ import annotations

import uuid
from typing import Callable, List, Optional, Tuple

from app.domain.performance.domain.entities.performance_test import PerformanceTest
from app.domain.performance.domain.value_objects.performance_metrics import (
    PerformanceMetrics,
)


class InMemoryPerformanceRepository:
    """基于内存 dict 的性能测试聚合仓储（线程锁保护写）。"""

    def __init__(self) -> None:
        self._store: dict = {}
        self._lock = __import__("threading").RLock()

    def next_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def save(self, test: PerformanceTest) -> PerformanceTest:
        with self._lock:
            self._store[test.id.value] = test
        return test

    def find_by_id(self, test_id: str) -> Optional[PerformanceTest]:
        with self._lock:
            return self._store.get(str(test_id))

    def update(self, test: PerformanceTest) -> Optional[PerformanceTest]:
        with self._lock:
            if str(test.id.value) not in self._store:
                return None
            self._store[str(test.id.value)] = test
        return test

    def list(
        self,
        *,
        status: str = "",
        target_name: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[PerformanceTest], int]:
        with self._lock:
            items = list(self._store.values())
        if status:
            s = str(status).lower()
            items = [t for t in items if t.status.value.value == s]
        if target_name:
            tn = str(target_name).lower()
            items = [t for t in items if tn in t.target_name.lower()]
        total = len(items)
        return items[offset : offset + limit], total

    def delete(self, test_id: str) -> bool:
        with self._lock:
            return self._store.pop(str(test_id), None) is not None


class EngineBenchmarkRunner:
    """复用既有 app/performance 引擎的真实基准 runner。

    将既有引擎 `benchmark_function` 返回的引擎指标对象转换为领域
    `PerformanceMetrics` 值对象（防腐层：外层对象不入领域层）。
    """

    def __init__(self, *, default_iterations: int = 100, default_warmup: int = 5):
        self._default_iterations = default_iterations
        self._default_warmup = default_warmup

    def run(
        self,
        target: Callable[[], object],
        *,
        name: str,
        iterations: int = 100,
        warmup: int = 5,
    ) -> PerformanceMetrics:
        from app.performance.benchmark import benchmark_function

        engine = benchmark_function(
            target,
            iterations=iterations or self._default_iterations,
            warmup=warmup or self._default_warmup,
            name=name,
        )
        return PerformanceMetrics.from_dict(engine.to_dict())


__all__ = ["InMemoryPerformanceRepository", "EngineBenchmarkRunner"]
