"""报告产物聚合根 Report。

聚合边界内的组成：
  - Report（聚合根，一份测试报告产物的文件制品）
  - ReportFormat / ReportState / 汇总摘要（值对象）

职责：守护报告产物的生命周期不变量（状态机迁移、格式合法、回收站动作
合法性、汇总口径）。所有变更必须经由聚合根方法触发；业务命令在校验
通过后记录领域事件，供应用层落库 + 发布，与文件/审计副作用解耦。

报告产物为文件制品（对应 ReportRepo 的报告文件管理），不依赖业务数据库，
故本聚合以"文件名"为身份，配合 filesystem 仓储实现。
"""
from __future__ import annotations

import time
from typing import Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.report.domain.events import (
    ReportPurged,
    ReportRestored,
    ReportTrashed,
)
from app.domain.report.domain.services.report_policy import ReportLifecyclePolicy
from app.domain.report.domain.value_objects.report_format import ReportFormat
from app.domain.report.domain.value_objects.report_state import (
    ReportState,
    ReportStateEnum,
)


class Report(AggregateRoot):
    """报告产物聚合根。"""

    def __init__(
        self,
        *,
        report_name: str,
        report_format: str = "html",
        title: str = "测试生成报告",
        project_name: str = "Test Generation",
        summary: Optional[dict] = None,
        state: str = ReportStateEnum.ACTIVE.value,
        generated_at: Optional[float] = None,
    ):
        if not (report_name or "").strip():
            raise DomainValidationError("报告文件名不能为空")
        self.id = Identifier.of(report_name.strip())
        self._name = report_name.strip()
        self._format = ReportFormat(report_format)
        self._title = (title or "测试生成报告").strip() or "测试生成报告"
        self._project_name = (project_name or "Test Generation").strip() \
            or "Test Generation"
        self._summary = dict(summary or {
            "total": 0, "passed": 0, "failed": 0, "coverage": 0.0,
        })
        self._state = ReportState(state)
        self._generated_at = generated_at if generated_at is not None else time.time()
        self._domain_events = []
        self.version = 0

    # ── 只读属性 ─────────────────────────────────────
    @property
    def name(self) -> str:
        return self._name

    @property
    def report_format(self) -> ReportFormat:
        return self._format

    @property
    def title(self) -> str:
        return self._title

    @property
    def project_name(self) -> str:
        return self._project_name

    @property
    def summary(self) -> dict:
        return dict(self._summary)

    @property
    def total(self) -> int:
        return self._summary.get("total", 0)

    @property
    def passed(self) -> int:
        return self._summary.get("passed", 0)

    @property
    def failed(self) -> int:
        return self._summary.get("failed", 0)

    @property
    def coverage(self) -> float:
        return self._summary.get("coverage", 0.0)

    @property
    def state(self) -> ReportState:
        return self._state

    @property
    def generated_at(self) -> float:
        return self._generated_at

    @property
    def is_trashed(self) -> bool:
        return self._state.is_trashed

    # ── 业务命令（守护不变量）────────────────────────
    def trash(self, operator: str = "system") -> None:
        """将报告移入回收站。"""
        if self._state.is_trashed:
            raise DomainValidationError("报告已在回收站，不可重复删除")
        policy = ReportLifecyclePolicy()
        policy.ensure_transition_allowed(self._state, ReportState(ReportStateEnum.TRASH))
        self._state = ReportState(ReportStateEnum.TRASH)
        self.record_event(ReportTrashed(self._name, operator))

    def restore(self, operator: str = "system") -> None:
        """从回收站恢复报告。"""
        if not self._state.is_trashed:
            raise DomainValidationError("报告不在回收站，无需恢复")
        policy = ReportLifecyclePolicy()
        policy.ensure_transition_allowed(self._state, ReportState(ReportStateEnum.ACTIVE))
        self._state = ReportState(ReportStateEnum.ACTIVE)
        self.record_event(ReportRestored(self._name, operator))

    def mark_purged(self, operator: str = "system") -> None:
        """标记报告已被彻底删除（终态，供物理删除后调用）。"""
        policy = ReportLifecyclePolicy()
        policy.ensure_purgeable(self._state)
        self._state = ReportState(ReportStateEnum.PURGED)
        self.record_event(ReportPurged(self._name, operator))

    # ── 汇总更新 ─────────────────────────────────────
    def set_summary(self, summary: dict) -> None:
        """写入由生成产物计算出的汇总口径。"""
        total = int(summary.get("total", 0) or 0)
        passed = int(summary.get("passed", 0) or 0)
        failed = int(summary.get("failed", 0) or 0)
        coverage = float(summary.get("coverage", 0.0) or 0.0)
        self._summary = {
            "total": max(total, 0),
            "passed": max(passed, 0),
            "failed": max(failed, 0),
            "coverage": max(coverage, 0.0),
        }

    # ── 序列化 / 持久化 ─────────────────────────────
    def to_dict(self) -> dict:
        """导出可返回给上层视图层的字典。"""
        return {
            "id": self.id.value,
            "name": self._name,
            "report_format": self._format.value,
            "title": self._title,
            "project_name": self._project_name,
            "summary": dict(self._summary),
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "coverage": self.coverage,
            "state": self._state.value.value,
            "generated_at": self._generated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Report":
        """从持久化字典 / 仓储返回行重建聚合。"""
        return Report(
            report_name=str(data.get("name") or data.get("id") or ""),
            report_format=data.get("report_format", "html"),
            title=data.get("title", "测试生成报告"),
            project_name=data.get("project_name", "Test Generation"),
            summary=data.get("summary"),
            state=data.get("state", ReportStateEnum.ACTIVE.value),
            generated_at=data.get("generated_at"),
        )


__all__ = ["Report"]
