"""测试计划聚合根 TestPlan。

聚合边界内的组成：
  - TestPlan（聚合根）
  - 若干值对象：Priority / PlanStatus / PlanType / CaseType
  - 关联用例集合（PlanCase[]，作为聚合内值对象托管）

职责：守护测试计划的完整性与业务不变量（名称非空、优先级/状态合法、状态机
迁移、归档规则等）。所有变更必须经由聚合根方法触发，业务命令在校验通过后
记录领域事件，供应用层落库 + 发布。

注意：为了与既有四层存储（TestPlanRepo，按"计划 + 计划用例表"落库）适配，
聚合将"关联用例"以 list 形式内聚，由仓储层负责把 PlanCase[] 同步到
test_plan_cases 表。
"""
from __future__ import annotations

import time
from typing import List, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.test_plan.domain.events import (
    TestPlanArchived,
    TestPlanCaseAdded,
    TestPlanCaseRemoved,
    TestPlanCaseReordered,
    TestPlanCaseStatusChanged,
    TestPlanDeleted,
    TestPlanStatusChanged,
    TestPlanUpdated,
)
from app.domain.test_plan.domain.value_objects.case_status import CaseExecutionStatus
from app.domain.test_plan.domain.value_objects.case_type import CaseType
from app.domain.test_plan.domain.value_objects.plan_case import PlanCase
from app.domain.test_plan.domain.value_objects.plan_type import PlanType, PlanTypeEnum
from app.domain.test_plan.domain.value_objects.priority import Priority, PriorityEnum
from app.domain.test_plan.domain.value_objects.status import PlanStatus, PlanStatusEnum


class TestPlan(AggregateRoot):
    """测试计划聚合根。"""

    def __init__(
        self,
        *,
        plan_id: str,
        name: str,
        description: str = "",
        priority: str = PriorityEnum.P2.value,
        status: str = PlanStatusEnum.PREPARED.value,
        module_id: str = "root",
        project_id: str = "",
        created_by: str = "admin",
        start_time: float = 0,
        end_time: float = 0,
        tags: Optional[List[str]] = None,
        pass_threshold: float = 100,
        test_planning: bool = False,
        auto_update_status: bool = False,
        repeat_case: bool = False,
        plan_type: str = PlanTypeEnum.TEST_PLAN.value,
        group_id: str = "NONE",
        cases: Optional[List[dict]] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
    ):
        if not (name or "").strip():
            raise DomainValidationError("测试计划名称不能为空")
        self.id = Identifier.of(plan_id)
        self._name = (name or "").strip()
        self._description = description or ""
        self._priority = Priority(priority)
        self._status = PlanStatus(status)
        self._module_id = module_id or "root"
        self._project_id = project_id or ""
        self._created_by = created_by or "admin"
        self._start_time = float(start_time or 0)
        self._end_time = float(end_time or 0)
        self._tags = list(tags or [])
        self._pass_threshold = self._validate_threshold(pass_threshold)
        self._test_planning = bool(test_planning)
        self._auto_update_status = bool(auto_update_status)
        self._repeat_case = bool(repeat_case)
        self._plan_type = PlanType(plan_type)
        self._group_id = group_id or "NONE"
        self._cases = self._coerce_cases(cases or [], self.id.value)
        self._created_at = created_at if created_at is not None else time.time()
        self._updated_at = updated_at if updated_at is not None else self._created_at
        self._domain_events = []
        self.version = 0

    # ── 只读属性 ─────────────────────────────────────
    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def priority(self) -> Priority:
        return self._priority

    @property
    def status(self) -> PlanStatus:
        return self._status

    @property
    def module_id(self) -> str:
        return self._module_id

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def created_by(self) -> str:
        return self._created_by

    @property
    def start_time(self) -> float:
        return self._start_time

    @property
    def end_time(self) -> float:
        return self._end_time

    @property
    def tags(self) -> List[str]:
        return list(self._tags)

    @property
    def pass_threshold(self) -> float:
        return self._pass_threshold

    @property
    def test_planning(self) -> bool:
        return self._test_planning

    @property
    def auto_update_status(self) -> bool:
        return self._auto_update_status

    @property
    def repeat_case(self) -> bool:
        return self._repeat_case

    @property
    def plan_type(self) -> PlanType:
        return self._plan_type

    @property
    def group_id(self) -> str:
        return self._group_id

    @property
    def cases(self) -> List[PlanCase]:
        return list(self._cases)

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    def _touch(self) -> None:
        self._updated_at = time.time()

    # ── 内部助手 ─────────────────────────────────────
    @staticmethod
    def _validate_threshold(value: float) -> float:
        try:
            v = float(value)
        except (TypeError, ValueError):
            raise DomainValidationError(f"非法通过阈值 '{value}'，应为数值")
        if v < 0 or v > 100:
            raise DomainValidationError("通过阈值必须在 0~100 之间")
        return v

    @classmethod
    def _coerce_cases(cls, cases: list, plan_id: str) -> List[PlanCase]:
        result = []
        for i, c in enumerate(cases):
            if isinstance(c, PlanCase):
                result.append(c)
                continue
            d = dict(c or {})
            result.append(PlanCase(
                rel_id=str(d.get("rel_id") or d.get("id") or d.get("relId") or ""),
                plan_id=str(d.get("plan_id") or plan_id),
                case_id=str(d.get("case_id") or d.get("caseId") or ""),
                case_type=str(d.get("case_type") or d.get("caseType") or "functional"),
                status=str(d.get("status") or "pending"),
                position=int(d.get("position", 0) or (d.get("execute_time") or 0) or i),
            ))
        return result

    # ── 业务命令（守护不变量）────────────────────────
    def rename(self, new_name: str, operator: str = "system") -> None:
        nn = (new_name or "").strip()
        if not nn:
            raise DomainValidationError("测试计划名称不能为空")
        if nn == self._name:
            return
        self._name = nn
        self._touch()
        self.record_event(TestPlanUpdated(self.id.value, ["name"], operator))

    def change_description(self, text: str, operator: str = "system") -> None:
        self._description = text or ""
        self._touch()
        self.record_event(TestPlanUpdated(self.id.value, ["description"], operator))

    def change_priority(self, priority: str, operator: str = "system") -> None:
        new_p = Priority(priority)
        if new_p.value == self._priority.value:
            return
        self._priority = new_p
        self._touch()
        self.record_event(TestPlanUpdated(self.id.value, ["priority"], operator))

    def change_schedule(self, *, start_time: Optional[float] = None,
                        end_time: Optional[float] = None, operator: str = "system") -> None:
        changed = []
        if start_time is not None and float(start_time) != self._start_time:
            self._start_time = float(start_time)
            changed.append("start_time")
        if end_time is not None and float(end_time) != self._end_time:
            self._end_time = float(end_time)
            changed.append("end_time")
        if changed:
            self._touch()
            self.record_event(TestPlanUpdated(self.id.value, changed, operator))

    def set_threshold(self, threshold: float, operator: str = "system") -> None:
        v = self._validate_threshold(threshold)
        if v == self._pass_threshold:
            return
        self._pass_threshold = v
        self._touch()
        self.record_event(TestPlanUpdated(self.id.value, ["pass_threshold"], operator))

    def set_tags(self, tags: List[str], operator: str = "system") -> None:
        self._tags = list(tags or [])
        self._touch()
        self.record_event(TestPlanUpdated(self.id.value, ["tags"], operator))

    def toggle_features(self, *, test_planning: Optional[bool] = None,
                        auto_update_status: Optional[bool] = None,
                        repeat_case: Optional[bool] = None,
                        operator: str = "system") -> None:
        changed = []
        if test_planning is not None and bool(test_planning) != self._test_planning:
            self._test_planning = bool(test_planning)
            changed.append("test_planning")
        if auto_update_status is not None and bool(auto_update_status) != self._auto_update_status:
            self._auto_update_status = bool(auto_update_status)
            changed.append("auto_update_status")
        if repeat_case is not None and bool(repeat_case) != self._repeat_case:
            self._repeat_case = bool(repeat_case)
            changed.append("repeat_case")
        if changed:
            self._touch()
            self.record_event(TestPlanUpdated(self.id.value, changed, operator))

    def change_status(self, target: str, operator: str = "system") -> None:
        """受状态机约束的状态迁移（不含归档，归档走 archive()）。"""
        target_status = PlanStatus(target)
        if target_status.is_archived:
            raise DomainValidationError("归档请使用 archive() 方法")
        from app.domain.test_plan.domain.services.test_plan_policy import TestPlanPolicy
        TestPlanPolicy().ensure_transition_allowed(self._status, target_status)
        if self._status == target_status:
            return
        old = str(self._status)
        self._status = target_status
        self._touch()
        self.record_event(TestPlanStatusChanged(self.id.value, old, str(target_status), operator))

    def archive(self, operator: str = "system") -> None:
        """归档计划（进入终态标记，不可直接回退到运行态）。"""
        if self._status.is_archived:
            raise DomainValidationError("测试计划已在归档状态，不可重复归档")
        old = str(self._status)
        self._status = PlanStatus(PlanStatusEnum.ARCHIVED.value)
        self._touch()
        self.record_event(TestPlanArchived(self.id.value, operator))
        self.record_event(TestPlanStatusChanged(self.id.value, old, "archived", operator))

    def mark_deleted(self, operator: str = "system") -> None:
        """删除计划（记录删除领域事件；物理删除由仓储执行）。"""
        self.record_event(TestPlanDeleted(self.id.value, operator))

    # ── 关联用例（聚合内值对象编排）──────────────────
    def add_case(self, rel_id: str, case_id: str, case_type: str = "functional",
                 operator: str = "system") -> PlanCase:
        ct = CaseType(case_type)
        if not self._repeat_case:
            for c in self._cases:
                if c.case_id == case_id and c.case_type == ct:
                    raise DomainValidationError(
                        f"用例 {case_id} 已存在关联（同类型且不允许多次添加）"
                    )
        rel_id = rel_id or f"{self.id.value}_{case_id}_{len(self._cases)}"
        pc = PlanCase(
            rel_id=rel_id,
            plan_id=self.id.value,
            case_id=case_id,
            case_type=ct,
            status=CaseExecutionStatus("pending"),
            position=len(self._cases),
        )
        self._cases.append(pc)
        self._touch()
        self.record_event(TestPlanCaseAdded(self.id.value, case_id, str(ct), operator))
        return pc

    def remove_case(self, rel_id: str, operator: str = "system") -> None:
        idx = next((i for i, c in enumerate(self._cases) if c.rel_id == rel_id), None)
        if idx is None:
            raise DomainValidationError(f"计划关联用例不存在: {rel_id}")
        self._cases.pop(idx)
        self._touch()
        self.record_event(TestPlanCaseRemoved(self.id.value, rel_id, operator))

    def update_case_status(self, rel_id: str, status: str, operator: str = "system") -> None:
        idx = next((i for i, c in enumerate(self._cases) if c.rel_id == rel_id), None)
        if idx is None:
            raise DomainValidationError(f"计划关联用例不存在: {rel_id}")
        old = str(self._cases[idx].status)
        updated = self._cases[idx].with_status(status)
        if str(updated.status) == old:
            return
        self._cases[idx] = updated
        self._touch()
        self.record_event(TestPlanCaseStatusChanged(
            self.id.value, rel_id, old, str(updated.status), operator))

    def reorder_cases(self, ordered_rel_ids: List[str], operator: str = "system") -> None:
        """按给定的关联 ID 顺序重排计划用例。"""
        by_id = {c.rel_id: c for c in self._cases}
        if set(ordered_rel_ids) != set(by_id.keys()):
            raise DomainValidationError("排序 ID 集合与现有关联用例不一致")
        self._cases = [
            by_id[rid].with_position(i) for i, rid in enumerate(ordered_rel_ids)
        ]
        self._touch()
        self.record_event(TestPlanCaseReordered(self.id.value, list(ordered_rel_ids), operator))

    # ── 快照 / 持久化 ───────────────────────────────
    def to_dict(self) -> dict:
        """导出可落库 / 返回给上层视图层的字典。"""
        return {
            "id": self.id.value,
            "name": self._name,
            "description": self._description,
            "priority": self._priority.value,
            "status": str(self._status),
            "module_id": self._module_id,
            "project_id": self._project_id,
            "created_by": self._created_by,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "start_time": self._start_time,
            "end_time": self._end_time,
            "tags": list(self._tags),
            "pass_threshold": self._pass_threshold,
            "test_planning": self._test_planning,
            "auto_update_status": self._auto_update_status,
            "repeat_case": self._repeat_case,
            "type": self._plan_type.value,
            "group_id": self._group_id,
            "cases": [
                {
                    "rel_id": c.rel_id,
                    "plan_id": c.plan_id,
                    "case_id": c.case_id,
                    "case_type": str(c.case_type),
                    "status": str(c.status),
                    "position": c.position,
                }
                for c in self._cases
            ],
        }

    @staticmethod
    def from_dict(data: dict) -> "TestPlan":
        """从持久化字典重建聚合。"""
        tags = data.get("tags") or []
        cases = data.get("cases") or []
        return TestPlan(
            plan_id=str(data.get("id") or data.get("plan_id") or ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            priority=data.get("priority") or PriorityEnum.P2.value,
            status=data.get("status") or PlanStatusEnum.PREPARED.value,
            module_id=data.get("module_id", "root"),
            project_id=data.get("project_id", ""),
            created_by=data.get("created_by") or data.get("createdBy", "admin"),
            start_time=data.get("start_time", 0),
            end_time=data.get("end_time", 0),
            tags=tags,
            pass_threshold=data.get("pass_threshold", 100),
            test_planning=bool(data.get("test_planning", 0)),
            auto_update_status=bool(data.get("auto_update_status", 0)),
            repeat_case=bool(data.get("repeat_case", 0)),
            plan_type=data.get("type") or PlanTypeEnum.TEST_PLAN.value,
            group_id=data.get("group_id", "NONE"),
            cases=cases,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
