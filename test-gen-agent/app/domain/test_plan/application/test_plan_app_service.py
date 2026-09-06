"""测试计划应用服务（Application Service / Use Case 门面）。

职责：
  1. 作为路由器与领域层之间的用例编排入口；
  2. 承载"测试计划"用例的事务边界：加载聚合 → 执行领域命令 → 保存聚合 →
     发布领域事件；
  3. 将领域异常透传给上层（由 Web 层统一翻译为 HTTP 响应）。

保持瘦：只做编排，不写业务规则（业务规则在领域层聚合内）。
"""
from __future__ import annotations

import logging
from typing import Optional

from app.domain.common.domain_events import event_bus
from app.domain.common.exceptions import AggregateNotFound
from app.domain.test_plan.application.dto import (
    AddCaseCommand,
    ChangeStatusCommand,
    CreatePlanCommand,
    PlanListQuery,
    RemoveCaseCommand,
    ReorderCasesCommand,
    UpdateCaseStatusCommand,
    UpdatePlanCommand,
)
from app.domain.test_plan.domain.entities.test_plan import TestPlan
from app.domain.test_plan.domain.repository import TestPlanRepository
from app.domain.test_plan.infrastructure.test_plan_repository_impl import TestPlanRepoAdapter
from app.domain.test_plan.infrastructure.test_plan_store import TestPlanRepo

logger = logging.getLogger(__name__)


class TestPlanAppService:
    """测试计划用例编排服务。"""

    def __init__(self, repo: TestPlanRepository = None):
        self._repo: TestPlanRepository = repo or TestPlanRepoAdapter()

    # ── 聚合级基础操作 ─────────────────────────────
    def create(self, cmd: CreatePlanCommand) -> dict:
        plan = TestPlan(
            plan_id=self._repo.next_id(),
            name=cmd.name,
            description=cmd.description,
            priority=cmd.priority,
            module_id=cmd.module_id,
            project_id=cmd.project_id,
            created_by=cmd.created_by,
            start_time=cmd.start_time,
            end_time=cmd.end_time,
            tags=cmd.tags,
            pass_threshold=cmd.pass_threshold,
            test_planning=cmd.test_planning,
            auto_update_status=cmd.auto_update_status,
            repeat_case=cmd.repeat_case,
            plan_type=cmd.plan_type,
            group_id=cmd.group_id,
        )
        self._repo.save(plan)
        self._publish(plan)
        return plan.to_dict()

    def get(self, plan_id: str) -> Optional[dict]:
        plan = self._repo.find_by_id(plan_id)
        return plan.to_dict() if plan else None

    def get_or_raise(self, plan_id: str) -> dict:
        plan = self._find_or_raise(plan_id)
        return plan.to_dict()

    def update(self, cmd: UpdatePlanCommand) -> Optional[dict]:
        plan = self._find_or_raise(cmd.plan_id)
        if cmd.name is not None:
            plan.rename(cmd.name, cmd.operator)
        if cmd.description is not None:
            plan.change_description(cmd.description, cmd.operator)
        if cmd.priority is not None:
            plan.change_priority(cmd.priority, cmd.operator)
        if cmd.start_time is not None or cmd.end_time is not None:
            plan.change_schedule(start_time=cmd.start_time, end_time=cmd.end_time,
                                 operator=cmd.operator)
        if cmd.pass_threshold is not None:
            plan.set_threshold(cmd.pass_threshold, cmd.operator)
        if cmd.tags is not None:
            plan.set_tags(cmd.tags, cmd.operator)
        if cmd.test_planning is not None or cmd.auto_update_status is not None \
                or cmd.repeat_case is not None:
            plan.toggle_features(
                test_planning=cmd.test_planning,
                auto_update_status=cmd.auto_update_status,
                repeat_case=cmd.repeat_case,
                operator=cmd.operator,
            )
        # module_id / project_id 无领域不变量，直接设置
        if cmd.module_id is not None and cmd.module_id != plan.module_id:
            plan._module_id = cmd.module_id
            plan._touch()
        if cmd.project_id is not None and cmd.project_id != plan.project_id:
            plan._project_id = cmd.project_id
            plan._touch()
        if cmd.status is not None:
            plan.change_status(cmd.status, cmd.operator)
        self._repo.update(plan)
        self._publish(plan)
        return plan.to_dict()

    def change_status(self, cmd: ChangeStatusCommand) -> Optional[dict]:
        plan = self._find_or_raise(cmd.plan_id)
        plan.change_status(cmd.target_status, cmd.operator)
        self._repo.update(plan)
        self._publish(plan)
        return plan.to_dict()

    def archive(self, plan_id: str, operator: str = "system") -> bool:
        plan = self._find_or_raise(plan_id)
        plan.archive(operator)
        self._repo.archive(plan_id)
        self._publish(plan)
        return True

    def delete(self, plan_id: str, operator: str = "system") -> bool:
        plan = self._find_or_raise(plan_id)
        plan.mark_deleted(operator)
        self._repo.delete(plan_id)
        self._publish(plan)
        return True

    # ── 关联用例编排 ───────────────────────────────
    def add_case(self, cmd: AddCaseCommand) -> dict:
        plan = self._find_or_raise(cmd.plan_id)
        plan.add_case(rel_id="", case_id=cmd.case_id, case_type=cmd.case_type,
                      operator=cmd.operator)
        self._repo.update(plan)
        self._publish(plan)
        return plan.to_dict()

    def remove_case(self, cmd: RemoveCaseCommand) -> dict:
        plan = self._find_or_raise(cmd.plan_id)
        plan.remove_case(cmd.rel_id, cmd.operator)
        self._repo.update(plan)
        self._publish(plan)
        return plan.to_dict()

    def update_case_status(self, cmd: UpdateCaseStatusCommand) -> dict:
        plan = self._find_or_raise(cmd.plan_id)
        plan.update_case_status(cmd.rel_id, cmd.status, cmd.operator)
        self._repo.update(plan)
        self._publish(plan)
        return plan.to_dict()

    def reorder_cases(self, cmd: ReorderCasesCommand) -> dict:
        plan = self._find_or_raise(cmd.plan_id)
        plan.reorder_cases(cmd.ordered_rel_ids, cmd.operator)
        self._repo.update(plan)
        self._publish(plan)
        return plan.to_dict()

    # ── 查询（读模型）──────────────────────────────
    def list(self, query: PlanListQuery) -> dict:
        items, total = self._repo.list(
            keyword=query.keyword, status=query.status, project_id=query.project_id,
            module_ids=query.module_ids,
            plan_type=query.plan_type, group_id=query.group_id,
            limit=query.limit, offset=query.offset,
        )
        return {"list": [p.to_dict() for p in items], "total": total}

    def statistics(self, plan_id: str) -> dict:
        return self._repo.statistics(plan_id)

    def statistics_bulk(self, plan_ids: list) -> dict:
        return self._repo.statistics_bulk(plan_ids or [])

    # ── 内部助手 ───────────────────────────────────

    # ── 模块树 / 统计 / 布局 / 定时 / 关联用例（协调读模型旁路，对齐旧 service 方法面）──
    # 以下为既有 test_plan_service 中仍直连 TestPlanRepo 的旁路方法。为达成"DDD
    # application 方法面与旧 service 逐方法对齐"，将它们补齐到应用门面并薄委托
    # 既有 TestPlanRepo（防腐层），Service 层再统一收敛委托本门面。
    def list_modules(self, **kwargs) -> list:
        return TestPlanRepo.list_modules()

    def create_module(self, name: str, parent_id: str = "root",
                      project_id: str = "") -> dict:
        return TestPlanRepo.create_module(name=name, parent_id=parent_id,
                                          project_id=project_id)

    def update_module(self, module_id: str, name: str = "", **kwargs) -> bool:
        return TestPlanRepo.update_module(module_id, name)

    def delete_module(self, module_id: str) -> bool:
        return TestPlanRepo.delete_module(module_id)

    def move_module(self, drag_node_id: str, drop_node_id: str,
                    drop_position: int = 0) -> bool:
        return TestPlanRepo.move_module(drag_node_id, drop_node_id,
                                        int(drop_position or 0))

    def count_plans_by_module(self, **kwargs) -> dict:
        return TestPlanRepo.count_plans_by_module(
            project_id=kwargs.get("projectId") or kwargs.get("project_id") or ""
        )

    def save_dashboard_layout(self, org_id: str, user_id: str, layout: list) -> None:
        return TestPlanRepo.save_dashboard_layout(org_id, user_id, layout)

    def load_dashboard_layout(self, org_id: str, user_id: str):
        return TestPlanRepo.load_dashboard_layout(org_id, user_id)

    def save_schedule(self, plan_id: str, cron: str = "", enable: bool = True,
                      run_mode: str = "SERIAL", project_id: str = "") -> dict:
        return TestPlanRepo.save_schedule(plan_id, cron, enable, run_mode, project_id)

    def get_schedule(self, plan_id: str) -> Optional[dict]:
        return TestPlanRepo.get_schedule(plan_id)

    def get_schedules(self, plan_ids: list) -> dict:
        return TestPlanRepo.get_schedules(plan_ids or [])

    def delete_schedule(self, plan_id: str) -> bool:
        return TestPlanRepo.delete_schedule(plan_id)

    def add_plan_case(self, plan_id: str, case_id: str,
                      case_type: str = "functional") -> Optional[dict]:
        return TestPlanRepo.add_plan_case(plan_id=plan_id, case_id=case_id,
                                          case_type=case_type)

    def remove_plan_case(self, rel_id: str, **kwargs) -> bool:
        return TestPlanRepo.remove_plan_case(rel_id)

    def list_plan_cases(self, plan_id: str) -> list:
        return TestPlanRepo.list_plan_cases(plan_id)

    def update_plan_case_status(self, rel_id: str, status: str) -> bool:
        return TestPlanRepo.update_plan_case_status(rel_id, status)

    def update_rel_pos(self, rel_id: str, pos: int) -> bool:
        return TestPlanRepo.update_rel_pos(rel_id, pos)

    def _find_or_raise(self, plan_id: str) -> TestPlan:
        plan = self._repo.find_by_id(plan_id)
        if plan is None:
            raise AggregateNotFound(f"测试计划不存在或已删除: {plan_id}")
        return plan

    def _publish(self, plan: TestPlan) -> None:
        events = plan.pull_domain_events()
        for ev in events:
            event_bus.dispatch(ev)


# 单例门面（进程内复用）
test_plan_app_service = TestPlanAppService()
test_plan_service = test_plan_app_service
