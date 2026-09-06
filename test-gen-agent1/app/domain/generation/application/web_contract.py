"""Generation 域 ↔ Web / 运行记录（run_records）行模型的契约翻译层。

目的（B 阶段前置的 DTO 契约桥）
--------------------------------
generation 域聚合 `GenerationJob` 与其底层存储 run_records（被 `/api/runs`、
报告兼容层共用）的**表达形态不同**：

  - 运行记录行（`RunRepo`/`run_service`/`/api/runs` 所见）是 14 列扁平快照，
    `status`/`steps`/`fix_loops` 等 DDD 派生态埋在 `metadata` JSON 里；
  - `GenerationJob.to_dict()` 则是 21 键聚合视图，额外含
    `status`/`steps`/`fix_loops`/`version`/`updated_at`/`test_type`/`generate_script`。

本模块提供**纯翻译函数**（无 DB 副作用），保证：
  1. 既有运行记录（含历史遗留、非 DDD 写入的）可无损还原为 `GenerationJob` 聚合；
  2. `GenerationJob` 输出可稳定投影为与 run_records 契约一致的扁平行；
  3. DDD 写入记录与既有 `run_service.save` 写入记录在契约上**逐字段等价**，
     从而让「同步生成链路落库切换为 DDD 生产者」这一 B/C 步骤可独立验证、可回滚。

保持零框架依赖，仅依赖 domain 聚合与纯 dataclass 行模型。
"""
from __future__ import annotations

from typing import Optional

from app.domain.generation.domain.entities.generation_job import GenerationJob

# run_records 权威扁平列（与 RunRepo DDL / run_service 返回的行模型一致）
RUN_ROW_KEYS = (
    "id",
    "source",
    "file_path",
    "source_code",
    "generated_tests",
    "test_result",
    "coverage_report",
    "performance_report",
    "retry_count",
    "passed",
    "saved_to",
    "error",
    "created_at",
    "metadata",
)

# GenerationJob 独有、在扁平行中会落到 metadata 的派生态字段
_AGGREGATE_META_FIELDS = ("status", "steps", "fix_loops")


def to_run_row(job: GenerationJob) -> dict:
    """把聚合投影为与 run_records 契约一致的扁平行（供落库/读模型对齐）。

    - `passed` 以 0/1 int 表达（与 run_records 列一致）；
    - `status`/`steps`/`fix_loops` 收敛进 metadata（`generation_status`/`steps`/
      `fix_loops`），与既有 generation 仓储防腐层落库语义一致；
    - 其余 `test_type`/`generate_script`/`version`/`updated_at` 等 DDD 视图字段
      不进入扁平行，避免污染既有前端契约。
    """
    d = job.to_dict()
    meta = dict(d.get("metadata") or {})
    meta["generation_status"] = d["status"]
    if d.get("steps"):
        meta["steps"] = d["steps"]
    if d.get("fix_loops"):
        meta["fix_loops"] = d["fix_loops"]
    return {
        "id": d["id"],
        "source": d["source"],
        "file_path": d["file_path"],
        "source_code": d["source_code"],
        "generated_tests": d["generated_tests"],
        "test_result": d["test_result"],
        "coverage_report": d["coverage_report"],
        "performance_report": d["performance_report"],
        "retry_count": d["retry_count"],
        "passed": 1 if d.get("passed") else 0,
        "saved_to": d["saved_to"],
        "error": d["error"],
        "created_at": d["created_at"],
        "metadata": meta,
    }


def run_row_to_job(row: dict) -> Optional[GenerationJob]:
    """把运行记录行无损还原为 `GenerationJob` 聚合。

    兼容两类输入：
      - 旧数据（status/steps/fix_loops 未落在 metadata，或元数据缺失）：按缺省
        pending 重建，`GenerationJob.from_dict` 兜底；
      - DDD 写入数据（status/steps/fix_loops 位于 metadata JSON）：自动提升回聚合主字段。
    """
    if not row:
        return None
    data = dict(row)
    meta = data.get("metadata") or {}
    if isinstance(meta, str):
        import json

        try:
            meta = json.loads(meta or "{}")
        except Exception:
            meta = {}
    if not data.get("status"):
        data["status"] = meta.get("generation_status") or "pending"
    if not data.get("steps"):
        data["steps"] = meta.get("steps") or []
    if not data.get("fix_loops"):
        data["fix_loops"] = meta.get("fix_loops") or []
    data["metadata"] = {k: v for k, v in dict(meta).items()
                        if k not in _AGGREGATE_META_FIELDS}
    try:
        return GenerationJob.from_dict(data)
    except Exception:
        # 不可重建（如 file_path 为空等极端脏数据）时返回 None，交由调用方降级
        return None


def run_row_to_web_view(row: dict) -> dict:
    """把扁平运行记录行归一为稳定的「生成记录」Web 视图（幂等、可序列化）。"""
    if not row:
        return {}
    out = {k: row.get(k) for k in RUN_ROW_KEYS if k in row}
    meta = out.get("metadata") or {}
    if isinstance(meta, str):
        import json

        try:
            meta = json.loads(meta or "{}")
        except Exception:
            meta = {}
    # 派生态提升到顶层只读字段，便于前端/调试查看，不写入扁平行
    out["status"] = meta.get("generation_status") or "pending"
    out["steps"] = meta.get("steps") or []
    out["fix_loops"] = meta.get("fix_loops") or []
    return out


__all__ = [
    "RUN_ROW_KEYS",
    "to_run_row",
    "run_row_to_job",
    "run_row_to_web_view",
]
