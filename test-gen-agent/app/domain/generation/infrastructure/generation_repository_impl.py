"""GenerationJob 聚合仓储实现（Adapter 防腐层）。

把"面向聚合的仓储接口"翻译为既有 RunRepo（run_records 四层仓库）的命令，
复用已验证的存储逻辑，让领域层获得聚合级的读写语义。后续如需换存储，
仅替换本文件即可。
"""
from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from app.domain.common.exceptions import AggregateNotFound
from app.domain.generation.domain.entities.generation_job import GenerationJob
from app.domain.generation.infrastructure.generation_store import RunRepo


class GenerationJobRepoAdapter:
    """将既有 RunRepo 封装为面向聚合的 GenerationJob 仓储。"""

    # 重建聚合时需剔除的运行时杂项元数据字段
    _RUNTIME_META_FIELDS = ("request", "via", "client")

    def next_id(self) -> str:
        return uuid.uuid4().hex[:16]

    def save(self, job: GenerationJob) -> Optional[GenerationJob]:
        """保存新聚合（底层 RunRepo.save 生成主键并落盘）。"""
        d = job.to_dict()
        row = RunRepo.save(
            file_path=d["file_path"],
            source_code=d["source_code"],
            source=d["source"],
            generated_tests=d["generated_tests"],
            test_result=d["test_result"],
            coverage_report=d["coverage_report"],
            performance_report=d["performance_report"],
            retry_count=d["retry_count"],
            saved_to=d["saved_to"],
            error=d["error"],
            metadata={**_runtime_free(d["metadata"]), **_job_meta(d)},
        )
        if row is not None:
            # 实际主键以 RunRepo 落库为准，回填到聚合
            job.id = type(job.id).of(row.get("id"))
        return job

    def update(self, job: GenerationJob) -> bool:
        """聚合级原位更新（保留主键，通过 RunRepo.update_record 落库）。"""
        existed = RunRepo.get(job.id.value) is not None
        if not existed:
            raise AggregateNotFound(f"生成任务不存在: {job.id.value}")
        d = job.to_dict()
        row = RunRepo.update_record(
            job.id.value,
            file_path=d["file_path"],
            source_code=d["source_code"],
            source=d["source"],
            generated_tests=d["generated_tests"],
            test_result=d["test_result"],
            coverage_report=d["coverage_report"],
            performance_report=d["performance_report"],
            retry_count=d["retry_count"],
            saved_to=d["saved_to"],
            error=d["error"],
            metadata={**_runtime_free(d["metadata"]), **_job_meta(d)},
        )
        return row is not None

    def find_by_id(self, job_id: str) -> Optional[GenerationJob]:
        row = RunRepo.get(job_id)
        return self._rebuild(row) if row else None

    def list_jobs(self, *, file_path: str = "", source: str = "",
                  passed: Optional[bool] = None, status: str = "",
                  search: str = "", limit: int = 50,
                  offset: int = 0) -> Tuple[List[GenerationJob], int]:
        rows = RunRepo.list_records(
            file_path=file_path or None, source=source or None,
            passed=passed, search=search or None,
            limit=limit, offset=offset,
        )
        total = RunRepo.count_records(
            file_path=file_path or None, source=source or None,
            passed=passed, search=search or None,
        )
        if status:
            rows = [r for r in rows if _row_status(r) == status]
        jobs = [self._rebuild(r) for r in rows]
        return jobs, total

    def delete_by_id(self, job_id: str) -> bool:
        return bool(RunRepo.delete_by_id(job_id))

    def stats(self) -> dict:
        return RunRepo.stats()

    # ── 内部：行 → 聚合 ─────────────────────────────
    @staticmethod
    def _rebuild(row: dict) -> GenerationJob:
        meta = dict(row.get("metadata") or {})
        data = dict(row)
        data["metadata"] = _runtime_free(meta)
        # 将写入 metadata 的 status/步骤/修复循环提升为聚合主表字段重建
        if not data.get("status"):
            data["status"] = meta.get("generation_status") or "pending"
        if not data.get("steps"):
            data["steps"] = meta.get("steps") or []
        if not data.get("fix_loops"):
            data["fix_loops"] = meta.get("fix_loops") or []
        return GenerationJob.from_dict(data)


def _job_meta(d: dict) -> dict:
    """把聚合的 status/步骤/修复循环封装进 metadata 以完整持久化。"""
    meta = {"generation_status": d["status"]}
    if d.get("steps"):
        meta["steps"] = d["steps"]
    if d.get("fix_loops"):
        meta["fix_loops"] = d["fix_loops"]
    return meta


def _runtime_free(meta: dict) -> dict:
    """去除运行时杂项，保留业务元数据字段。"""
    return {k: v for k, v in dict(meta or {}).items()
            if k not in GenerationJobRepoAdapter._RUNTIME_META_FIELDS}


def _row_status(row: dict) -> str:
    meta = row.get("metadata") or {}
    if isinstance(meta, str):
        return "pending"
    return meta.get("generation_status") or "pending"


# 单例（进程内复用）
generation_repository = GenerationJobRepoAdapter()


__all__ = ["GenerationJobRepoAdapter", "generation_repository"]
