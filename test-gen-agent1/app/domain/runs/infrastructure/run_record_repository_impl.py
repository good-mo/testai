"""运行记录聚合仓储实现（Adapter 防腐层）。

把"面向聚合 RunRecord 的仓储接口"翻译为既有 RunRepo（run_records
四层仓库）命令，复用已验证的存储逻辑，让领域层获得聚合级读写语义。

与 generation 域共享同一 run_records 底层存储，但本适配器保持聚合
视图与 run_service → RunRepo 契约逐字段等价，双轨可回滚。
"""
from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from app.domain.runs.domain.entities.run_record import RunRecord
from app.repositories.run_repo import RunRepo


class RunRecordRepoAdapter:
    """将既有 RunRepo 封装为面向 RunRecord 聚合的仓储。"""

    def next_id(self) -> str:
        return uuid.uuid4().hex[:16]

    # ── 读 ──────────────────────────────────────────
    def find_by_id(self, record_id: str) -> Optional[RunRecord]:
        row = RunRepo.get(record_id)
        return RunRecord.from_dict(row) if row else None

    def list_records(self, *, file_path: str = "", source: str = "",
                     passed: Optional[bool] = None, search: str = "",
                     limit: int = 50, offset: int = 0) -> Tuple[List[RunRecord], int]:
        rows = RunRepo.list_records(
            file_path=file_path or None, source=source or None,
            passed=passed, search=search or None,
            limit=limit, offset=offset,
        )
        total = RunRepo.count_records(
            file_path=file_path or None, source=source or None,
            passed=passed, search=search or None,
        )
        return [RunRecord.from_dict(r) for r in rows], total

    def stats(self) -> dict:
        return RunRepo.stats()

    # ── 写 ──────────────────────────────────────────
    def save(self, record: RunRecord) -> Optional[RunRecord]:
        d = record.to_dict()
        row = RunRepo.save(
            file_path=d["file_path"],
            source_code=d["source_code"],
            generated_tests=d["generated_tests"],
            test_result=d["test_result"],
            coverage_report=d["coverage_report"],
            performance_report=d["performance_report"],
            retry_count=d["retry_count"],
            saved_to=d["saved_to"],
            error=d["error"],
            source=d["source"],
            metadata=d["metadata"],
        )
        if row is None:
            return None
        # 实际主键以 RunRepo 落库为准，回填到聚合
        record.id = type(record.id).of(row.get("id"))
        return record

    def update(self, record: RunRecord) -> Optional[RunRecord]:
        """聚合级原位更新（保留主键）。"""
        d = record.to_dict()
        row = RunRepo.update_record(
            record.id.value,
            file_path=d["file_path"],
            source_code=d["source_code"],
            generated_tests=d["generated_tests"],
            test_result=d["test_result"],
            coverage_report=d["coverage_report"],
            performance_report=d["performance_report"],
            retry_count=d["retry_count"],
            saved_to=d["saved_to"],
            error=d["error"],
            metadata=d["metadata"],
        )
        return RunRecord.from_dict(row) if row else None

    def delete_by_id(self, record_id: str) -> bool:
        return bool(RunRepo.delete_by_id(record_id))

    def delete_batch(self, record_ids: list) -> int:
        return int(RunRepo.delete_batch(list(record_ids)))

    def clear(self, source: str = "") -> int:
        return int(RunRepo.clear(source=source or None))


# 单例（进程内复用）
run_record_repository = RunRecordRepoAdapter()

__all__ = ["RunRecordRepoAdapter", "run_record_repository"]
