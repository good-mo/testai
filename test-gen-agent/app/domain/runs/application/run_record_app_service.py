"""运行记录应用服务（Application Service / Use Case 门面）。

承载"运行记录 / 报告（run_records）"用例的事务边界：
  - 登记一次运行快照（save / 落盘 run_records）；
  - 原位更新 / 重命名（file_path 充当报告名）；
  - 列表查询 / 统计 / 清空 / 单条与批量删除。

保持瘦：只做编排 + 领域事件发布，业务规则（来源合法性、报告名非空、
passed 派生）留在领域聚合/值对象内。异常统一抛领域异常供上层翻译。
"""
from __future__ import annotations

import logging
from typing import Optional

from app.domain.common.domain_events import event_bus
from app.domain.common.exceptions import AggregateNotFound
from app.domain.runs.application.dto import (
    ClearRunRecordsCommand,
    RenameRunRecordCommand,
    RunRecordListQuery,
    SaveRunRecordCommand,
    UpdateRunRecordCommand,
)
from app.domain.runs.domain.entities.run_record import RunRecord
from app.domain.runs.domain.repository import RunRecordRepository
from app.domain.runs.infrastructure.run_record_repository_impl import (
    RunRecordRepoAdapter,
)

logger = logging.getLogger(__name__)


class RunRecordAppService:
    """运行记录用例编排服务。"""

    def __init__(self, repo: RunRecordRepository = None):
        self._repo: RunRecordRepository = repo or RunRecordRepoAdapter()

    # ── 保存 / 登记 ─────────────────────────────────
    def save(self, cmd: SaveRunRecordCommand) -> Optional[dict]:
        """登记一次运行/报告快照。返回落库后的记录 dict（含实际主键）。"""
        record = RunRecord(
            record_id=self._repo.next_id(),
            file_path=cmd.file_path,
            source_code=cmd.source_code,
            generated_tests=cmd.generated_tests,
            test_result=cmd.test_result or {},
            coverage_report=cmd.coverage_report or {},
            performance_report=cmd.performance_report or {},
            retry_count=cmd.retry_count,
            saved_to=cmd.saved_to,
            error=cmd.error,
            source=cmd.source,
            metadata=cmd.metadata or {},
        )
        saved = self._repo.save(record)
        if saved is None:
            logger.error("运行记录保存失败 [file=%s]", cmd.file_path)
            return None
        self._emit_saved(saved)
        return saved.to_dict()

    def update(self, cmd: UpdateRunRecordCommand) -> Optional[dict]:
        """原位更新运行记录（保留主键，供聚合级状态推进落库）。"""
        record = self._find_or_raise(cmd.record_id)
        # rename 走报告名语义守卫
        if cmd.file_path is not None:
            record.rename(cmd.file_path, cmd.operator)
        record.set_results(
            source_code=cmd.source_code,
            generated_tests=cmd.generated_tests,
            test_result=cmd.test_result,
            coverage_report=cmd.coverage_report,
            performance_report=cmd.performance_report,
            retry_count=cmd.retry_count,
            saved_to=cmd.saved_to,
            error=cmd.error,
            metadata=cmd.metadata,
        )
        updated = self._repo.update(record)
        return updated.to_dict() if updated else None

    def rename(self, cmd: RenameRunRecordCommand) -> bool:
        """将运行记录重命名（file_path 充当报告名）。"""
        record = self._find_or_raise(cmd.record_id)
        record.rename(cmd.new_name, cmd.operator)
        self._repo.update(record)
        self._publish(record)
        return True

    # ── 查询 ───────────────────────────────────────
    def get(self, record_id: str) -> Optional[dict]:
        record = self._repo.find_by_id(record_id)
        return record.to_dict() if record else None

    def get_or_raise(self, record_id: str) -> dict:
        record = self._repo.find_by_id(record_id)
        if record is None:
            raise AggregateNotFound(f"运行记录不存在: {record_id}")
        return record.to_dict()

    def list(self, query: RunRecordListQuery) -> dict:
        records, total = self._repo.list_records(
            file_path=query.file_path, source=query.source,
            passed=query.passed, search=query.search,
            limit=query.limit, offset=query.offset,
        )
        return {"list": [r.to_dict() for r in records], "total": total}

    def count(self, query: RunRecordListQuery) -> int:
        _, total = self._repo.list_records(
            file_path=query.file_path, source=query.source,
            passed=query.passed, search=query.search,
            limit=1, offset=0,
        )
        return total

    def stats(self) -> dict:
        return self._repo.stats()

    # ── 删除 / 清空 ────────────────────────────────
    def delete(self, record_id: str) -> bool:
        if not self._repo.delete_by_id(record_id):
            return False
        from app.domain.runs.domain.events import RunRecordDeleted

        event_bus.dispatch(RunRecordDeleted(record_id))
        return True

    def delete_batch(self, record_ids: list) -> int:
        ids = list(record_ids or [])
        if not ids:
            return 0
        deleted = self._repo.delete_batch(ids)
        from app.domain.runs.domain.events import RunRecordBatchDeleted

        event_bus.dispatch(RunRecordBatchDeleted(ids, deleted))
        return deleted

    def clear(self, cmd: ClearRunRecordsCommand) -> int:
        cleared = self._repo.clear(source=cmd.source)
        from app.domain.runs.domain.events import RunRecordCleared

        event_bus.dispatch(RunRecordCleared(cmd.source, cleared))
        return cleared

    # ── 内部助手 ───────────────────────────────────
    def _find_or_raise(self, record_id: str) -> RunRecord:
        record = self._repo.find_by_id(record_id)
        if record is None:
            raise AggregateNotFound(f"运行记录不存在: {record_id}")
        return record

    def _emit_saved(self, record: RunRecord) -> None:
        from app.domain.runs.domain.events import RunRecordSaved

        event_bus.dispatch(RunRecordSaved(
            record.id.value, record.file_path,
            record.source.value, record.passed,
        ))

    def _publish(self, record: RunRecord) -> None:
        for ev in record.pull_domain_events():
            event_bus.dispatch(ev)


# 单例门面（进程内复用）
run_record_app_service = RunRecordAppService()

__all__ = ["RunRecordAppService", "run_record_app_service"]
