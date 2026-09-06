"""测试计划聚合仓储实现（Adapter 防腐层）。

把"面向聚合的仓储接口"翻译为既有 TestPlanRepo（四层 Repository）与
test_plan_cases 表的命令，实现防腐层（Anti-Corruption Layer）。
计划主体行复用 TestPlanRepo；聚合内关联用例（需保留聚合侧 rel_id 与排序）
以直接 SQL 落 test_plan_cases 表，保证 rel_id 稳定、可被后续 remove/更新引用。

复用已验证的存储逻辑，同时让领域层获得聚合级读写语义；后续如需换存储
仅替换本文件。
"""
from __future__ import annotations

import time
import uuid
from typing import List, Optional, Tuple

from app.core.database import Database
from app.domain.test_plan.domain.entities.test_plan import TestPlan
from app.domain.test_plan.infrastructure.test_plan_store import DB_NAME, TestPlanRepo


class TestPlanRepoAdapter:
    """将既有 TestPlanRepo 封装为面向聚合的仓储。"""

    def next_id(self) -> str:
        return uuid.uuid4().hex[:12]

    # ── 关联用例表直连（保留 rel_id / 排序）──────────
    @staticmethod
    def _conn():
        return Database.get_conn(DB_NAME)

    @classmethod
    def _load_cases(cls, plan_id: str) -> List[dict]:
        conn = cls._conn()
        rows = conn.execute(
            "SELECT id, plan_id, case_id, case_type, status, execute_time "
            "FROM test_plan_cases WHERE plan_id = ? ORDER BY execute_time ASC",
            (plan_id,),
        ).fetchall()
        return [
            {
                "rel_id": str(r["id"]),
                "plan_id": str(r["plan_id"]),
                "case_id": str(r["case_id"]),
                "case_type": str(r["case_type"] or "functional"),
                "status": str(r["status"] or "pending"),
                "position": float(r["execute_time"] or 0),
            }
            for r in rows
        ]

    @classmethod
    def _sync_cases(cls, plan_id: str, cases: list) -> None:
        """把聚合内的关联用例集合与 test_plan_cases 表对齐。"""
        conn = cls._conn()
        # 收集 DB 现存 rel_id
        existing = {
            str(r["id"])
            for r in conn.execute(
                "SELECT id FROM test_plan_cases WHERE plan_id = ?", (plan_id,)
            ).fetchall()
        }
        new_cases = [c for c in cases if c.rel_id not in existing]
        removed = existing - {c.rel_id for c in cases}
        for rid in removed:
            conn.execute("DELETE FROM test_plan_cases WHERE id = ?", (rid,))
        for c in new_cases:
            conn.execute(
                "INSERT INTO test_plan_cases "
                "(id, plan_id, case_id, case_type, status, execute_time, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (c.rel_id, plan_id, c.case_id, c.case_type.value, c.status.value,
                 float(c.position), time.time()),
            )
        # 更新现有关联的执行状态与排序
        for c in cases:
            if c.rel_id in existing:
                conn.execute(
                    "UPDATE test_plan_cases SET status = ?, case_type = ?, "
                    "execute_time = ? WHERE id = ? AND plan_id = ?",
                    (c.status.value, c.case_type.value, float(c.position),
                     c.rel_id, plan_id),
                )
        conn.commit()

    # ── 读：聚合重建 ────────────────────────────────
    def find_by_id(self, plan_id: str) -> Optional[TestPlan]:
        row = TestPlanRepo.get_plan(plan_id)
        if not row:
            return None
        row = dict(row)
        row["cases"] = self._load_cases(plan_id)
        return TestPlan.from_dict(row)

    def list(self, *, keyword: str = "", status: str = "", project_id: str = "",
             module_ids: Optional[List[str]] = None, plan_type: str = "",
             group_id: str = "",
             limit: int = 100, offset: int = 0) -> Tuple[List[TestPlan], int]:
        rows = TestPlanRepo.list_plans(
            keyword=keyword, status=status, project_id=project_id,
            module_ids=module_ids, limit=limit, offset=offset,
            type=plan_type, group_id=group_id,
        )
        total = TestPlanRepo.count_plans(
            keyword=keyword, status=status, project_id=project_id,
            module_ids=module_ids,
            type=plan_type, group_id=group_id,
        )
        plans = []
        for r in rows:
            d = dict(r)
            d["cases"] = self._load_cases(str(d.get("id")))
            plans.append(TestPlan.from_dict(d))
        return plans, total

    def statistics(self, plan_id: str) -> dict:
        return TestPlanRepo.get_plan_statistics(plan_id)

    def statistics_bulk(self, plan_ids: List[str]) -> dict:
        return TestPlanRepo.get_plans_statistics(plan_ids)

    # ── 写：以聚合为粒度落库 ────────────────────────
    def save(self, plan: TestPlan) -> TestPlan:
        # 计划主体行以聚合的显式 id 直插，保证 find_by_id 可重建同一聚合
        d = plan.to_dict()
        now = time.time()
        import json as _json
        conn = self._conn()
        conn.execute(
            "INSERT INTO test_plans (id, name, description, priority, module_id, "
            "project_id, created_by, created_at, updated_at, start_time, end_time, "
            "tags, pass_threshold, test_planning, auto_update_status, repeat_case, "
            "type, group_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                plan.id.value, d["name"], d["description"], d["priority"],
                d["module_id"], d["project_id"], d["created_by"], now, now,
                d["start_time"], d["end_time"],
                _json.dumps(d["tags"] or [], ensure_ascii=False),
                d["pass_threshold"], 1 if d["test_planning"] else 0,
                1 if d["auto_update_status"] else 0, 1 if d["repeat_case"] else 0,
                d["type"], d["group_id"],
            ),
        )
        conn.commit()
        if d["cases"]:
            self._sync_cases(plan.id.value, plan.cases)
        return plan

    def update(self, plan: TestPlan) -> Optional[TestPlan]:
        d = plan.to_dict()
        persist = {
            "name": d["name"], "description": d["description"],
            "priority": d["priority"], "module_id": d["module_id"],
            "status": d["status"], "tags": d["tags"],
            "pass_threshold": d["pass_threshold"],
            "test_planning": d["test_planning"],
            "auto_update_status": d["auto_update_status"],
            "repeat_case": d["repeat_case"],
        }
        if d["start_time"]:
            persist["start_time"] = d["start_time"]
        if d["end_time"]:
            persist["end_time"] = d["end_time"]
        TestPlanRepo.update_plan(plan.id.value, **persist)
        self._sync_cases(plan.id.value, plan.cases)
        reloaded = self.find_by_id(plan.id.value)
        return reloaded if reloaded else plan

    def delete(self, plan_id: str) -> bool:
        return TestPlanRepo.delete_plan(plan_id)

    def archive(self, plan_id: str) -> bool:
        return TestPlanRepo.archive_plan(plan_id)
