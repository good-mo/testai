"""性能测试任务聚合根 PerformanceTest。

聚合边界内的组成：
  - PerformanceTest（聚合根）
  - 值对象：PerformanceMetrics（结果画像）、SLOThreshold（阈值集合）、
    SLOValidationResult（校验结果）、PerformanceStatus（状态机）

职责：
  - 守护性能测试任务的完整性与业务不变量（状态迁移合法、终态不可重入、
    不达标需带原因、目标标识非空等）。
  - 记录一次基准测试产生的性能指标并依据 SLO 阈值判定达标与否。

所有变更必须经由聚合根方法触发；业务命令（开始/记录结果/标记失败/跳过/
配置阈值）在校验通过后记录领域事件，供应用层落库 + 发布。
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Mapping, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.performance.domain.events import (
    PerformanceTestCompleted,
    PerformanceTestFailed,
    PerformanceTestPassed,
    PerformanceTestSkipped,
    PerformanceTestStarted,
    SLOThresholdUpdated,
)
from app.domain.performance.domain.exceptions import (
    InvalidPerformanceStatusTransition,
)
from app.domain.performance.domain.value_objects.performance_metrics import (
    PerformanceMetrics,
)
from app.domain.performance.domain.value_objects.slo import (
    SLOThreshold,
    SLOValidationResult,
)
from app.domain.performance.domain.value_objects.status import (
    PerformanceStatus,
    PerformanceStatusEnum,
)


class PerformanceTest(AggregateRoot):
    """性能测试任务聚合根。"""

    def __init__(
        self,
        *,
        test_id: str,
        target_name: str,
        source_ref: str = "",
        status: str = PerformanceStatusEnum.PENDING.value,
        thresholds: Optional[List[Mapping[str, Any]]] = None,
        metrics: Optional[Mapping[str, Any]] = None,
        slo_result: Optional[Mapping[str, Any]] = None,
        reason: str = "",
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
    ):
        target_name = (target_name or "").strip()
        if not target_name:
            raise DomainValidationError("性能测试目标名称不能为空")
        self.id = Identifier.of(test_id)
        self._target_name = target_name
        self._source_ref = (source_ref or "").strip()
        self._status = PerformanceStatus(status)
        self._thresholds = [
            t if isinstance(t, SLOThreshold) else SLOThreshold(**t)
            for t in (thresholds or [])
        ]
        self._metrics: Optional[PerformanceMetrics] = (
            metrics
            if isinstance(metrics, PerformanceMetrics)
            else PerformanceMetrics.from_dict(metrics) if metrics else None
        )
        self._slo_result: Optional[SLOValidationResult] = (
            slo_result
            if isinstance(slo_result, SLOValidationResult)
            else SLOValidationResult(
                name=slo_result.get("name", ""),
                passed=bool(slo_result.get("passed")),
                checks=list(slo_result.get("checks") or []),
                details=slo_result.get("details", ""),
            )
            if slo_result
            else None
        )
        self._reason = reason or ""
        self._created_at = created_at if created_at is not None else time.time()
        self._updated_at = updated_at if updated_at is not None else self._created_at
        self._domain_events = []
        self.version = 0

    # ── 只读属性 ─────────────────────────────────────
    @property
    def target_name(self) -> str:
        return self._target_name

    @property
    def source_ref(self) -> str:
        return self._source_ref

    @property
    def status(self) -> PerformanceStatus:
        return self._status

    @property
    def thresholds(self) -> List[SLOThreshold]:
        return list(self._thresholds)

    @property
    def metrics(self) -> Optional[PerformanceMetrics]:
        return self._metrics

    @property
    def slo_result(self) -> Optional[SLOValidationResult]:
        return self._slo_result

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    @property
    def passed(self) -> bool:
        """是否处于「达标」终态。"""
        return self._status.value is PerformanceStatusEnum.PASSED

    @property
    def is_terminal(self) -> bool:
        return self._status.is_terminal

    def _touch(self) -> None:
        self._updated_at = time.time()

    def _transition_to(self, target: PerformanceStatus, operator: str) -> None:
        if not self._status.can_transition_to(target):
            raise InvalidPerformanceStatusTransition(str(self._status), str(target))
        self._status = target
        self._touch()

    # ── 业务命令（守护不变量）────────────────────────
    def set_target(self, target_name: str, operator: str = "system") -> None:
        """修改被测目标名称（仅允许在执行前）。"""
        nt = (target_name or "").strip()
        if not nt:
            raise DomainValidationError("性能测试目标名称不能为空")
        if self._status.value is not PerformanceStatusEnum.PENDING:
            raise InvalidPerformanceStatusTransition(str(self._status), "pending")
        if nt == self._target_name:
            return
        self._target_name = nt
        self._touch()

    def set_thresholds(
        self, thresholds: List[Mapping[str, Any]], operator: str = "system"
    ) -> None:
        """配置 / 覆盖 SLO 阈值（仅允许在执行前）。"""
        if self._status.value is not PerformanceStatusEnum.PENDING:
            raise InvalidPerformanceStatusTransition(str(self._status), "pending")
        self._thresholds = [SLOThreshold(**t) for t in (thresholds or [])]
        self._touch()
        self.record_event(SLOThresholdUpdated(self.id.value, operator))

    def start(self, operator: str = "system") -> None:
        """开始执行：pending → running。"""
        self._transition_to(PerformanceStatus(PerformanceStatusEnum.RUNNING), operator)
        self.record_event(PerformanceTestStarted(self.id.value, self._target_name, operator))

    def record_result(
        self,
        metrics: PerformanceMetrics,
        slo_result: Optional[SLOValidationResult] = None,
        operator: str = "system",
    ) -> None:
        """写入性能结果并判定达标：running → passed / failed。

        若未显式提供 slo_result，则由领域策略依据当前阈值自动校验。
        """
        if self._status.value is PerformanceStatusEnum.PENDING:
            # 允许未 start 直接落结果：视为自动 start
            self._transition_to(
                PerformanceStatus(PerformanceStatusEnum.RUNNING), operator
            )
        if self._status.value is not PerformanceStatusEnum.RUNNING:
            raise InvalidPerformanceStatusTransition(str(self._status), "passed/failed")

        if not metrics or not (metrics.name or "").strip():
            raise DomainValidationError("性能结果必须携带指标名称")
        if metrics.name != self._target_name:
            raise DomainValidationError(
                f"指标名称 '{metrics.name}' 与目标 '{self._target_name}' 不一致"
            )

        if slo_result is None:
            from app.domain.performance.domain.services.performance_policy import (
                PerformancePolicy,
            )
            slo_result = PerformancePolicy().validate_slo(
                name=self._target_name, metrics=metrics, thresholds=self._thresholds
            )

        self._metrics = metrics
        self._slo_result = slo_result

        if slo_result.passed:
            self._transition_to(PerformanceStatus(PerformanceStatusEnum.PASSED), operator)
            self.record_event(
                PerformanceTestCompleted(
                    self.id.value, self._target_name, "passed", True, operator
                )
            )
            self.record_event(PerformanceTestPassed(self.id.value, self._target_name, operator))
        else:
            self._transition_to(PerformanceStatus(PerformanceStatusEnum.FAILED), operator)
            self._reason = slo_result.details
            self.record_event(
                PerformanceTestCompleted(
                    self.id.value, self._target_name, "failed", False, operator
                )
            )
            self.record_event(
                PerformanceTestFailed(
                    self.id.value, self._target_name, self._reason, operator
                )
            )

    def fail(self, reason: str = "", operator: str = "system") -> None:
        """显式标记失败（如执行异常）：running → failed。"""
        if self._status.value is not PerformanceStatusEnum.RUNNING:
            raise InvalidPerformanceStatusTransition(str(self._status), "failed")
        self._reason = reason or "性能测试执行失败"
        self._transition_to(PerformanceStatus(PerformanceStatusEnum.FAILED), operator)
        self.record_event(
            PerformanceTestFailed(self.id.value, self._target_name, self._reason, operator)
        )

    def skip(self, reason: str = "", operator: str = "system") -> None:
        """跳过测试：pending/running → skipped。"""
        self._reason = reason or "已跳过"
        self._transition_to(PerformanceStatus(PerformanceStatusEnum.SKIPPED), operator)
        self.record_event(
            PerformanceTestSkipped(self.id.value, self._target_name, self._reason, operator)
        )

    # ── 快照 / 持久化 ───────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        """导出可落库 / 返回给上层视图层的字典。"""
        return {
            "id": self.id.value,
            "target_name": self._target_name,
            "source_ref": self._source_ref,
            "status": self._status.value.value,
            "thresholds": [t.to_dict() for t in self._thresholds],
            "metrics": self._metrics.to_dict() if self._metrics else None,
            "slo_result": self._slo_result.to_dict() if self._slo_result else None,
            "reason": self._reason,
            "passed": self.passed,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "PerformanceTest":
        """从持久化字典重建聚合。"""
        data = dict(data or {})
        return PerformanceTest(
            test_id=str(data.get("id") or data.get("test_id") or ""),
            target_name=data.get("target_name", ""),
            source_ref=data.get("source_ref", ""),
            status=data.get("status") or PerformanceStatusEnum.PENDING.value,
            thresholds=list(data.get("thresholds") or []),
            metrics=data.get("metrics"),
            slo_result=data.get("slo_result"),
            reason=data.get("reason", ""),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
