# app/repositories/run_repo.py
"""运行记录数据访问层（Phase 3 重构 · 4 层对齐）。

本层是 runs 域**唯一权威**：同时持有表结构 DDL 与数据访问 SQL。
- 表结构（run_records + 索引）由本模块 _init_db 幂等建表，作为
  schema_registry 单一权威来源，不再依赖旧 app.runs.repository。
- 旧 app.runs.repository 仅作兼容门面，模块顶部委托本仓库，形成
  runs.repository → run_repo 的单向依赖，消除双向循环依赖。

纯数据访问（run_records 的 CRUD / 列表过滤 / 统计 / 清空）均在仓库内
直连 SQL，输出形态与旧 facade 完全一致（JSON 字段反序列化等）。
"""
import json
import logging
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.database import Database

logger = logging.getLogger(__name__)

# 运行来源类型（对外暴露，兼容）
SOURCE_SINGLE = "single"
SOURCE_PROJECT = "project"
SOURCE_WS = "websocket"
SOURCE_TASK = "task"
VALID_SOURCES = {SOURCE_SINGLE, SOURCE_PROJECT, SOURCE_WS, SOURCE_TASK}

DB_NAME = "runs.db"


def _get_conn() -> sqlite3.Connection:
    """获取 runs.db 连接（统一使用 Database 连接池）。"""
    return Database.get_conn(DB_NAME)


def _init_db() -> None:
    """幂等建表 + 索引（权威 DDL，供 schema_registry / 迁移兜底引用）。"""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS run_records (
                id TEXT PRIMARY KEY,
                source TEXT DEFAULT 'single',
                file_path TEXT DEFAULT '',
                source_code TEXT DEFAULT '',
                generated_tests TEXT DEFAULT '',
                test_result TEXT DEFAULT '{}',
                coverage_report TEXT DEFAULT '{}',
                performance_report TEXT DEFAULT '{}',
                retry_count INTEGER DEFAULT 0,
                passed INTEGER DEFAULT 0,
                saved_to TEXT DEFAULT '',
                error TEXT DEFAULT '',
                created_at REAL,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_run_records_created ON run_records(created_at)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_run_records_file ON run_records(file_path)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_run_records_passed ON run_records(passed)
        """)
        conn.commit()
    finally:
        pass


_init_db()


class RunRepo:
    """运行记录数据访问仓库。

    本模块持有 run_records 表结构与数据访问唯一权威。对外暴露与旧
    app.runs.repository 一致的类方法签名，保证上层（service）零改动。
    """

    db_name = DB_NAME

    @classmethod
    def _conn(cls) -> sqlite3.Connection:
        """获取 runs.db 连接（表已由模块导入时 _init_db 建好）。"""
        return _get_conn()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        """将数据库行转为 dict（JSON 字段反序列化）。"""
        data = dict(row)
        for field in ("test_result", "coverage_report", "performance_report", "metadata"):
            if data.get(field):
                try:
                    data[field] = json.loads(data[field])
                except (json.JSONDecodeError, TypeError):
                    pass  # 保留原始字符串
        return data

    # ══════════════════════════════════════════════════════
    # CRUD
    # ══════════════════════════════════════════════════════
    @classmethod
    def save(cls, file_path: str = "", source_code: str = "",
             generated_tests: str = "", test_result: dict = None,
             coverage_report: dict = None, performance_report: dict = None,
             retry_count: int = 0, saved_to: str = "", error: str = "",
             source: str = "", metadata: dict = None) -> Optional[dict]:
        """保存一次运行的所有记录。落盘完整快照。"""
        if source not in VALID_SOURCES:
            source = SOURCE_SINGLE

        test_result = test_result or {}
        coverage_report = coverage_report or {}
        performance_report = performance_report or {}
        metadata = metadata or {}

        record_id = uuid.uuid4().hex[:16]
        now = time.time()
        passed = int(bool(test_result.get("passed", False)))

        conn = cls._conn()
        try:
            conn.execute(
                """INSERT INTO run_records
                   (id, source, file_path, source_code, generated_tests,
                    test_result, coverage_report, performance_report,
                    retry_count, passed, saved_to, error, created_at, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record_id, source, file_path, source_code, generated_tests,
                    json.dumps(test_result, ensure_ascii=False),
                    json.dumps(coverage_report, ensure_ascii=False),
                    json.dumps(performance_report, ensure_ascii=False),
                    retry_count, passed, saved_to, error, now,
                    json.dumps(metadata, ensure_ascii=False),
                ),
            )
            logger.info("运行记录已保存 [id=%s, file=%s, passed=%s]",
                        record_id, file_path, passed)
            return cls.get(record_id)
        except Exception as e:
            logger.error("运行记录保存失败 [err=%s]", e, exc_info=True)
            return None

    @classmethod
    def get(cls, record_id: str) -> Optional[dict]:
        """按 ID 获取一条运行记录。"""
        conn = cls._conn()
        row = conn.execute(
            "SELECT * FROM run_records WHERE id = ?", (record_id,)
        ).fetchone()
        return cls._row_to_dict(row) if row else None

    @classmethod
    def list_records(cls, file_path: Optional[str] = None,
                     source: Optional[str] = None, passed: Optional[bool] = None,
                     search: Optional[str] = None, limit: int = 50,
                     offset: int = 0) -> list:
        """列出运行记录，支持按文件路径/来源/结果过滤与分页。"""
        query = "SELECT * FROM run_records WHERE 1=1"
        params: List = []

        if file_path:
            query += " AND file_path LIKE ?"
            params.append(f"%{file_path}%")
        if source and source in VALID_SOURCES:
            query += " AND source = ?"
            params.append(source)
        if passed is not None:
            query += " AND passed = ?"
            params.append(int(passed))
        if search:
            query += " AND (file_path LIKE ? OR error LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        conn = cls._conn()
        rows = conn.execute(query, params).fetchall()
        return [cls._row_to_dict(r) for r in rows]

    @classmethod
    def count_records(cls, file_path: Optional[str] = None,
                      source: Optional[str] = None, passed: Optional[bool] = None,
                      search: Optional[str] = None) -> int:
        """统计运行记录数量（与 list_records 同过滤条件）。"""
        query = "SELECT COUNT(*) FROM run_records WHERE 1=1"
        params: List = []

        if file_path:
            query += " AND file_path LIKE ?"
            params.append(f"%{file_path}%")
        if source and source in VALID_SOURCES:
            query += " AND source = ?"
            params.append(source)
        if passed is not None:
            query += " AND passed = ?"
            params.append(int(passed))
        if search:
            query += " AND (file_path LIKE ? OR error LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        conn = cls._conn()
        row = conn.execute(query, tuple(params)).fetchone()
        return row[0] if row else 0

    @classmethod
    def stats(cls) -> dict:
        """获取运行记录统计。"""
        conn = cls._conn()
        total = conn.execute("SELECT COUNT(*) FROM run_records").fetchone()[0]
        passed = conn.execute(
            "SELECT COUNT(*) FROM run_records WHERE passed = 1"
        ).fetchone()[0]
        failed = total - passed
        by_source = {s: 0 for s in VALID_SOURCES}
        for row in conn.execute(
            "SELECT source, COUNT(*) AS cnt FROM run_records GROUP BY source"
        ):
            if row["source"] in by_source:
                by_source[row["source"]] = row["cnt"]
        # 平均覆盖率：Python 侧解析 coverage_report 字段
        rows = conn.execute(
            "SELECT coverage_report FROM run_records "
            "WHERE coverage_report IS NOT NULL AND coverage_report != '' "
            "AND coverage_report != '{}'"
        ).fetchall()
        coverage_sum, coverage_cnt = 0.0, 0
        for r in rows:
            try:
                cov = json.loads(r["coverage_report"])
                pct = cov.get("coverage_pct")
                if pct is not None:
                    coverage_sum += float(pct)
                    coverage_cnt += 1
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        avg_coverage = round(coverage_sum / coverage_cnt, 2) if coverage_cnt else 0.0
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "by_source": by_source,
            "avg_coverage": avg_coverage,
        }

    @classmethod
    def clear(cls, source: Optional[str] = None) -> int:
        """清空运行记录（谨慎使用）。返回删除条数。

        显式指定 source 时仅清空该来源记录；缺省时清空全部，
        兼容历史调用方与 DELETE /api/runs 无参清空语义。
        """
        conn = cls._conn()
        if source:
            cur = conn.execute(
                "DELETE FROM run_records WHERE source = ?", (source,)
            )
            logger.info("按来源清空运行记录 [source=%s]", source)
        else:
            cur = conn.execute("DELETE FROM run_records")
            logger.info("运行记录已清空")
        deleted = cur.rowcount
        if deleted:
            logger.info("运行记录删除 [count=%s]", deleted)
        return deleted

    # ── 报告（run 记录别名）操作 ───────────────────────
    @classmethod
    def rename(cls, record_id: str, new_name: str) -> bool:
        """将运行记录重命名（更新 file_path 作为报告名）。"""
        conn = cls._conn()
        cur = conn.execute(
            "UPDATE run_records SET file_path = ? WHERE id = ?",
            (new_name, record_id),
        )
        conn.commit()
        return cur.rowcount > 0

    @classmethod
    def delete_by_id(cls, record_id: str) -> bool:
        """删除单条运行记录。"""
        conn = cls._conn()
        cur = conn.execute(
            "DELETE FROM run_records WHERE id = ?", (record_id,)
        )
        conn.commit()
        return cur.rowcount > 0

    @classmethod
    def delete_batch(cls, record_ids: list) -> int:
        """批量删除运行记录。"""
        if not record_ids:
            return 0
        conn = cls._conn()
        placeholders = ",".join(["?"] * len(record_ids))
        cur = conn.execute(
            f"DELETE FROM run_records WHERE id IN ({placeholders})",
            record_ids,
        )
        conn.commit()
        return cur.rowcount

    @classmethod
    def update_record(cls, record_id: str, *, file_path: str = None,
                      source_code: str = None, source: str = None,
                      generated_tests: str = None, test_result: dict = None,
                      coverage_report: dict = None,
                      performance_report: dict = None,
                      retry_count: int = None, saved_to: str = None,
                      error: str = None, metadata: dict = None) -> Optional[dict]:
        """按主键 id 原位更新一条运行记录（保留 id，不回炉新建）。

        供 DDD 生成编排域做"聚合级状态推进"落库使用：聚合 id 必须保持
        稳定，因此不能走 delete + save（那会生成新主键）。
        """
        conn = cls._conn()
        current = cls.get(record_id)
        if current is None:
            return None
        old = current
        new_meta = dict(old.get("metadata") or {})
        if metadata is not None:
            new_meta.update(metadata)

        test_result = (test_result if test_result is not None
                       else old.get("test_result") or {})
        coverage_report = (coverage_report if coverage_report is not None
                           else old.get("coverage_report") or {})
        performance_report = (performance_report if performance_report is not None
                              else old.get("performance_report") or {})

        passed = int(bool((test_result or {}).get("passed")))
        conn.execute(
            """UPDATE run_records SET
                 source = ?, file_path = ?, source_code = ?, generated_tests = ?,
                 test_result = ?, coverage_report = ?, performance_report = ?,
                 retry_count = ?, passed = ?, saved_to = ?, error = ?, metadata = ?
               WHERE id = ?""",
            (
                source if source is not None else old.get("source", "single"),
                file_path if file_path is not None else old.get("file_path", ""),
                source_code if source_code is not None else old.get("source_code", ""),
                generated_tests if generated_tests is not None else old.get("generated_tests", ""),
                json.dumps(test_result, ensure_ascii=False),
                json.dumps(coverage_report, ensure_ascii=False),
                json.dumps(performance_report, ensure_ascii=False),
                int(retry_count) if retry_count is not None else int(old.get("retry_count") or 0),
                passed,
                saved_to if saved_to is not None else old.get("saved_to", ""),
                error if error is not None else old.get("error", ""),
                json.dumps(new_meta, ensure_ascii=False),
                record_id,
            ),
        )
        conn.commit()
        return cls.get(record_id)


# 兼容类方法调用（部分上层代码按实例使用）
run_repo = RunRepo
