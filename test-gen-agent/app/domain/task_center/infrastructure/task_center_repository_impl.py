"""任务中心仓储实现（直接对接任务管理器 / 定时计划存储）。

不再反向依赖 `app.services.task_center_service`（避免 domain → services → domain
循环依赖风险）：
  - exec-task 操作 → app.tasks.manager（任务队列存储）
  - schedule 操作 → app.repositories.test_plan_repo.TestPlanRepo
"""
from __future__ import annotations

from app.core.task_enums import normalize_status
from app.repositories.test_plan_repo import TestPlanRepo
from app.tasks.manager import manager


class TaskCenterRepoAdapter:
    """将 TaskCenterRepository 委托给任务管理器与定时计划仓储。"""

    # ── exec-task（执行任务）── ────────────────────────────
    def stop_tasks(self, ids: list) -> dict:
        stopped, failed = 0, []
        for tid in ids:
            try:
                ok_, msg = manager.stop_task(tid)
                if ok_:
                    stopped += 1
                else:
                    failed.append(f"{tid}: {msg}")
            except Exception as e:  # noqa: BLE001
                failed.append(f"{tid}: {e}")
        return {"stopped": stopped, "failed": failed}

    def delete_tasks(self, ids: list) -> dict:
        deleted, failed = 0, []
        for tid in ids:
            try:
                ok_, msg = manager.delete_task(tid)
                if ok_:
                    deleted += 1
                else:
                    failed.append(f"{tid}: {msg}")
            except Exception as e:  # noqa: BLE001
                failed.append(f"{tid}: {e}")
        return {"deleted": deleted, "failed": failed}

    def rerun_task(self, task_id: str) -> dict:
        if not task_id:
            return {"ok": False, "message": "缺少任务 ID"}
        ok_, msg = manager.rerun_task(task_id)
        return {"ok": ok_, "message": msg, "taskId": task_id}

    def list_tasks(self) -> list:
        tasks = manager.list_tasks()
        for t in tasks:
            t["status"] = normalize_status(t.get("status"))
            t.setdefault("triggerMode", "MANUAL")
        return tasks

    async def submit_task(self, name: str, payload: dict):
        """[legacy 队列协调] 提交命名执行任务到后台队列。

        收口对 `manager.submit_named` 的直接 import，返回 manager.Task 对象，
        语义与原 service 薄层完全一致（协调 legacy 队列，不做跨域搬移）。
        """
        return await manager.submit_named(name, payload)

    def get_task(self, task_id: str):
        """[legacy 队列协调] 按 id 查询执行任务详情（dict 形态）。"""
        return manager.get_task_dict(task_id)

    def list_raw_tasks(self, limit: int) -> list:
        """[legacy 队列协调] 列出最近执行任务（原始摘要，不做展示态归一）。

        供 method_compat/generation 等需要原始生命周期状态的路由复用。
        """
        return manager.list_tasks(limit=limit)

    # ── schedule（定时任务）── ─────────────────────────────
    def switch_schedules(self, ids: list) -> dict:
        switched, failed = 0, []
        for sid in ids:
            try:
                cur = TestPlanRepo.get_schedule(sid)
                if not cur:
                    failed.append(f"{sid}: 定时任务不存在")
                    continue
                enable = not bool(cur.get("enable"))
                TestPlanRepo.save_schedule(
                    sid, cron=cur.get("cron", ""), enable=enable,
                    run_mode=cur.get("run_mode", "SERIAL"),
                    project_id=cur.get("project_id", ""))
                switched += 1
            except Exception as e:  # noqa: BLE001
                failed.append(f"{sid}: {e}")
        return {"switched": switched, "failed": failed}

    def enable_schedules(self, ids: list, enable: bool) -> dict:
        done, failed = 0, []
        for sid in ids:
            try:
                cur = TestPlanRepo.get_schedule(sid)
                if not cur:
                    failed.append(f"{sid}: 定时任务不存在")
                    continue
                TestPlanRepo.save_schedule(
                    sid, cron=cur.get("cron", ""), enable=enable,
                    run_mode=cur.get("run_mode", "SERIAL"),
                    project_id=cur.get("project_id", ""))
                done += 1
            except Exception as e:  # noqa: BLE001
                failed.append(f"{sid}: {e}")
        return {"done": done, "failed": failed}

    def delete_schedules(self, ids: list) -> dict:
        deleted, failed = 0, []
        for sid in ids:
            try:
                if TestPlanRepo.delete_schedule(sid):
                    deleted += 1
                else:
                    failed.append(f"{sid}: 定时任务不存在")
            except Exception as e:  # noqa: BLE001
                failed.append(f"{sid}: {e}")
        return {"deleted": deleted, "failed": failed}

    def update_schedule_cron(self, ids: list, cron: str) -> dict:
        updated, failed = 0, []
        for sid in ids:
            try:
                cur = TestPlanRepo.get_schedule(sid)
                if not cur:
                    failed.append(f"{sid}: 定时任务不存在")
                    continue
                TestPlanRepo.save_schedule(
                    sid, cron=cron, enable=cur.get("enable", True),
                    run_mode=cur.get("run_mode", "SERIAL"),
                    project_id=cur.get("project_id", ""))
                updated += 1
            except Exception as e:  # noqa: BLE001
                failed.append(f"{sid}: {e}")
        return {"updated": updated, "failed": failed}
