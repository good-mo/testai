"""TestInsight 聚合仓储实现（Adapter）。

把"面向聚合的仓储接口"翻译为既有 InsightRepo（数据访问仓库）的命令，
实现防腐层（Anti-Corruption Layer）。复用已验证的存储逻辑，同时让领域层
获得聚合级读写语义；后续如需换存储仅替换本文件。

- 读取 / 统计：直接复用 InsightRepo.list_trace / trace_stats；
- 写入：因既有 record_trace 每次自生成新 id 且不回填 source_hash / env，
  为保持"聚合 id 与落库 id 一致"及完整字段落库，本适配器以同一
  trace.db 连接直接 INSERT（表结构由 app.insights.trace 幂等建表）。
- 跨 defects / cases 的价值量化、风险分析等用例亦委托既有 InsightRepo，
  避免领域层直接触碰其它限界上下文存储。
"""
from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from app.domain.test_insight.domain.entities.trace_run import TraceRun
from app.domain.test_insight.infrastructure.insight_store import InsightRepo


class InsightRepoAdapter:
    """将既有 InsightRepo / trace.db 封装为面向 TraceRun 聚合的仓储。"""

    def next_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def _conn(self):
        # 复用 InsightRepo 建表触发 + 连接管理
        return InsightRepo._conn()

    # ── 读：聚合重建 ────────────────────────────────
    def find_by_id(self, trace_id: str) -> Optional[TraceRun]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM test_runs WHERE id = ?", (str(trace_id),)
        ).fetchone()
        return TraceRun.from_dict(dict(row)) if row else None

    def list(self, *, file_path: str = "", result: str = "",
             limit: int = 50, offset: int = 0) -> Tuple[List[TraceRun], int]:
        sql = "SELECT * FROM test_runs WHERE 1=1"
        params: list = []
        if file_path:
            sql += " AND file_path LIKE ?"
            params.append(f"%{file_path}%")
        if result:
            sql += " AND result = ?"
            params.append(result)
        conn = self._conn()
        rows = conn.execute(sql + " ORDER BY created_at DESC LIMIT ? OFFSET ?",
                            params + [limit, offset]).fetchall()
        all_rows = conn.execute(sql, params).fetchall()
        return [TraceRun.from_dict(dict(r)) for r in rows], len(all_rows)

    def list_by_file(self, file_path: str, limit: int = 100) -> List[TraceRun]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM test_runs WHERE file_path = ? "
            "ORDER BY created_at DESC LIMIT ?", (file_path, limit)
        ).fetchall()
        return [TraceRun.from_dict(dict(r)) for r in rows]

    def stats(self) -> dict:
        return InsightRepo.trace_stats()

    # ── 写：以聚合为粒度落库 ────────────────────────
    def save(self, run: TraceRun) -> TraceRun:
        d = run.to_dict()
        conn = self._conn()
        conn.execute(
            "INSERT INTO test_runs "
            "(id, file_path, source_hash, result, passed_count, failed_count, error_count, "
            " coverage, env_info, attribution, note, created_at, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (d["id"], d["file_path"], d["source_hash"], d["result"],
             d["passed_count"], d["failed_count"], d["error_count"],
             d["coverage"], d["env_info"], d["attribution"], d["note"],
             d["created_at"], d["created_by"]),
        )
        return run

    # ── 跨域分析 / 纯业务规则（代理既有 InsightRepo）──
    def value(self) -> dict:
        return InsightRepo.value()

    def incident_avoidance(self) -> dict:
        return InsightRepo.incident_avoidance()

    def assess_risk(self, source_files: Optional[list] = None) -> dict:
        return InsightRepo.assess_risk(source_files=source_files)

    def generate_from_description(self, description: str) -> dict:
        return InsightRepo.generate_from_description(description)

    def skill_path(self) -> dict:
        return InsightRepo.skill_path()
