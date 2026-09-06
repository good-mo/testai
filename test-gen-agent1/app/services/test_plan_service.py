# app/services/test_plan_service.py
"""测试计划业务逻辑层（Phase 3 重构 · 4 层对齐 + DDD 接入）。

迁移状态（A→B→C 渐进式）：
  - 阶段 A：`app/domain/test_plan/` DDD 聚合/应用层就绪（本模块不再直接持有规则）。
  - 阶段 B/C：计划聚合生命周期写路径（create/get/delete/archive）与统计
    （get_plan_statistics / get_plans_statistics）已委托 DDD `TestPlanAppService`，
    经 DTO/契约桥对外输出与既有四层一致的行结构；Service 变薄为门面，
    业务不变量（名称非空 / 优先级状态合法 / 归档状态机）由聚合根守护。

  仍属"双轨并存"的旁路（计划头通用编辑 update、只读列表/模块树 / 定时任务 /
  dashboard 布局 / 关联用例存储级编排 / metadata 排序等读模型与应用层专有列）
  保留直接走 TestPlanRepo，不阻塞、可回滚。
"""

from typing import Optional

from app.domain.common.exceptions import AggregateNotFound, DomainValidationError
from app.domain.test_plan.application.dto import (
    CreatePlanCommand,
)
from app.domain.test_plan.application.test_plan_app_service import (
    TestPlanAppService,
)
from app.domain.test_plan.application.test_plan_app_service import (
    test_plan_app_service as _ddd_app,
)
from app.repositories.test_plan_repo import TestPlanRepo


class TestPlanService:
    """测试计划服务（DDD 门面委托 + 既有旁路直连）。

    计划聚合生命周期经 `TestPlanAppService` 编排，返回结果经 `_to_legacy` 契约桥
    补全既有 Web 层读取的元数据列（metadata / execution_rate / pass_rate），
    保证下游调用方无需改动。
    """

    def __init__(self, app_service: TestPlanAppService = None):
        self._ddd: TestPlanAppService = app_service or _ddd_app

    # ── 契约桥：DDD 聚合 dict → 既有 Web 层行结构 ──────────
    @staticmethod
    def _to_legacy(plan: Optional[dict]) -> Optional[dict]:
        """把 DDD 聚合输出补全为既有 `_plan_from_row` 行结构。

        DDD `to_dict` 不含 metadata / execution_rate / pass_rate（应用层专有或
        由统计接口另行填充）；此处以 DB 行补齐，保证 get / create 返回与旧版一致。
        """
        if not plan:
            return None
        pid = plan.get("id")
        merged = dict(plan)
        # 已含则不改，否则从存储行补齐（metadat默认 {}，执行/通过率默认 0）
        if any(k not in merged for k in ("metadata", "execution_rate", "pass_rate")):
            row = TestPlanRepo.get_plan(pid) if pid else None
            if row:
                merged.setdefault("metadata", row.get("metadata", {}))
                merged.setdefault("execution_rate", row.get("execution_rate", 0))
                merged.setdefault("pass_rate", row.get("pass_rate", 0))
        merged.setdefault("metadata", {})
        merged.setdefault("execution_rate", 0)
        merged.setdefault("pass_rate", 0)
        return merged

    # ── 计划 CRUD（委托 DDD）─────────────────────────────
    def list_plans(
        self,
        keyword: str = "",
        status: str = "",
        project_id: str = "",
        module_ids: Optional[list] = None,
        limit: int = 100,
        offset: int = 0,
        **kwargs,
    ) -> list:
        """列出测试计划（委托 DDD `TestPlanAppService.list`）。

        计划聚合只读列表经领域应用门面编排，返回行经 `_to_legacy` 契约桥
        补全既有 Web 层读取的 metadata / execution_rate / pass_rate 列。
        """
        from app.domain.test_plan.application.dto import PlanListQuery

        result = self._ddd.list(PlanListQuery(
            keyword=keyword or "",
            status=status or "",
            project_id=project_id or "",
            module_ids=module_ids or None,
            plan_type=kwargs.get("type") or kwargs.get("plan_type") or "",
            group_id=kwargs.get("groupId") or kwargs.get("group_id") or "",
            limit=int(limit or 100),
            offset=int(offset or 0),
        ))
        return [self._to_legacy(p) for p in result.get("list", [])]

    def count_plans(
        self,
        keyword: str = "",
        status: str = "",
        project_id: str = "",
        module_ids: Optional[list] = None,
        **kwargs,
    ) -> int:
        """统计测试计划数（委托 DDD，仅取 total）。"""
        from app.domain.test_plan.application.dto import PlanListQuery

        result = self._ddd.list(PlanListQuery(
            keyword=keyword or "",
            status=status or "",
            project_id=project_id or "",
            module_ids=module_ids or None,
            plan_type=kwargs.get("type") or kwargs.get("plan_type") or "",
            group_id=kwargs.get("groupId") or kwargs.get("group_id") or "",
            limit=1,
            offset=0,
        ))
        return int(result.get("total", 0))

    def get_plan(self, plan_id: str) -> Optional[dict]:
        try:
            plan = self._ddd.get(plan_id)
        except (AggregateNotFound, DomainValidationError):
            return None
        return self._to_legacy(plan)

    def create_plan(
        self,
        name: str,
        description: str = "",
        priority: str = "P2",
        module_id: str = "root",
        project_id: str = "",
        created_by: str = "admin",
        **kwargs,
    ) -> dict:
        plan = self._ddd.create(
            CreatePlanCommand(
                name=name,
                description=description,
                priority=priority,
                module_id=module_id,
                project_id=project_id,
                created_by=created_by,
                start_time=kwargs.get("start_time", 0),
                end_time=kwargs.get("end_time", 0),
                tags=kwargs.get("tags") or [],
                pass_threshold=kwargs.get("pass_threshold", 100),
                test_planning=kwargs.get("test_planning", False),
                auto_update_status=kwargs.get("auto_update_status", False),
                repeat_case=kwargs.get("repeat_case", False),
                plan_type=kwargs.get("type") or kwargs.get("plan_type") or "TEST_PLAN",
                group_id=kwargs.get("groupId") or kwargs.get("group_id") or "NONE",
                operator=created_by or "admin",
            )
        )
        return self._to_legacy(plan)

    def update_plan(self, plan_id: str, **kwargs) -> Optional[dict]:
        """更新测试计划。

        计划头通用编辑（含 metadata / 执行率 / 通过率等应用层专有列）仍走既有
        TestPlanRepo，保持与旧版对任意字段/状态宽容写入一致的对外行为，避免
        破坏既有调用方。状态机的强约束由 DDD 聚合在专用流程（archive/change_status）
        中守护（阶段 C 下沉，此处不强行收紧以免回归）。
        """
        return TestPlanRepo.update_plan(plan_id, **kwargs)

    def delete_plan(self, plan_id: str) -> bool:
        try:
            return bool(self._ddd.delete(plan_id, "admin"))
        except (AggregateNotFound, DomainValidationError):
            return False

    def archive_plan(self, plan_id: str) -> bool:
        try:
            return bool(self._ddd.archive(plan_id, "admin"))
        except (AggregateNotFound, DomainValidationError):
            return False

    # ── 计划用例（存储级双轨并存，保留既有 TestPlanRepo）──────
    def add_plan_case(
        self, plan_id: str, case_id: str, case_type: str = "functional"
    ) -> Optional[dict]:
        return self._ddd.add_plan_case(
            plan_id=plan_id,
            case_id=case_id,
            case_type=case_type,
        )

    def remove_plan_case(self, rel_id: str, **kwargs) -> bool:
        return self._ddd.remove_plan_case(rel_id, **kwargs)

    def list_plan_cases(self, plan_id: str) -> list:
        return self._ddd.list_plan_cases(plan_id)

    def update_plan_case_status(self, rel_id: str, status: str) -> bool:
        return self._ddd.update_plan_case_status(rel_id, status)

    def _repo_update_rel_pos(self, rel_id: str, pos: int) -> bool:
        """更新计划关联用例的位置（内部占位）。"""
        return self._ddd.update_rel_pos(rel_id, pos)

    # ── 模块 ─────────────────────────────────────────────
    def list_modules(self, **kwargs) -> list:
        return self._ddd.list_modules(**kwargs)

    def create_module(self, name: str, parent_id: str = "root", project_id: str = "") -> dict:
        return self._ddd.create_module(name=name, parent_id=parent_id,
                                       project_id=project_id)

    def update_module(self, module_id: str, name: str = "", **kwargs) -> bool:
        return self._ddd.update_module(module_id, name, **kwargs)

    def delete_module(self, module_id: str) -> bool:
        return self._ddd.delete_module(module_id)

    def move_module(self, drag_node_id: str, drop_node_id: str, drop_position: int = 0) -> bool:
        """移动测试计划模块（改挂父模块）。"""
        return self._ddd.move_module(drag_node_id, drop_node_id, int(drop_position or 0))

    # ── 统计（委托 DDD 或既有仓库）────────────────────────
    def get_plans_statistics(self, plan_ids: list = None) -> dict:
        return self._ddd.statistics_bulk(plan_ids or [])

    def get_plan_statistics(self, plan_id: str) -> dict:
        return self._ddd.statistics(plan_id)

    def count_plans_by_module(self, **kwargs) -> dict:
        return self._ddd.count_plans_by_module(**kwargs)

    # ── Dashboard 布局 ─────────────────────────────────
    def save_dashboard_layout(self, org_id: str, user_id: str, layout: list) -> None:
        return self._ddd.save_dashboard_layout(org_id, user_id, layout)

    def load_dashboard_layout(self, org_id: str, user_id: str):
        return self._ddd.load_dashboard_layout(org_id, user_id)

    # ── 定时任务配置 ─────────────────────────────────
    def save_schedule(
        self,
        plan_id: str,
        cron: str = "",
        enable: bool = True,
        run_mode: str = "SERIAL",
        project_id: str = "",
    ) -> dict:
        return self._ddd.save_schedule(plan_id, cron, enable, run_mode, project_id)

    def get_schedule(self, plan_id: str) -> Optional[dict]:
        return self._ddd.get_schedule(plan_id)

    def get_schedules(self, plan_ids: list) -> dict:
        return self._ddd.get_schedules(plan_ids or [])

    def delete_schedule(self, plan_id: str) -> bool:
        return self._ddd.delete_schedule(plan_id)


test_plan_service = TestPlanService()
