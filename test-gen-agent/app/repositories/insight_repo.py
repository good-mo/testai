# app/repositories/insight_repo.py
"""测试洞察数据访问层（Phase 3 重构 · 4 层对齐）。

本层已从「委托旧 app.insights.* 各模块」下沉为**仓库内直接 SQLite 实现**，
消除 Repository 空壳化。

数据访问拆分：
- `test_runs` 表（trace 域）CRUD / 统计 / 自证清白 → 仓库内直连 SQL
- 缺陷价值 / 风险分析（查询 defects / test_cases 表）→ 仓库内直连 SQL
  数据读取 + 分析逻辑（与旧 insights 模块输出对齐）
- `attributions`（静态归因字典）、`skill_path`（纯静态技能阶梯）、
  `generate_from_description`（纯自然语言代码生成）为纯业务规则/工具，
  不涉及数据库，保留对旧 insights 模块的委托（避免 repo 层复制重复逻辑）。

schema 权威来源仍归 app.insights.trace（_init_db），仓库只在首次访问
时懒触发建表，避免同表双源 DDL 漂移。
"""
import ast
import json
import logging
import os
import platform
import sqlite3
import time
import uuid
from typing import Dict, Optional

from app.core.database import Database

logger = logging.getLogger(__name__)

# 执行归因（与旧 app.insights.trace 保持一致）
ATTRIBUTION_REQUIREMENT_CHANGE = "requirement_change"
ATTRIBUTION_ENV_ANOMALY = "environment_anomaly"
ATTRIBUTION_DATA_ISSUE = "data_issue"
ATTRIBUTION_CODE_REGRESSION = "code_regression"
ATTRIBUTION_COVERAGE_GAP = "coverage_gap"

ATTRIBUTIONS = {
    ATTRIBUTION_REQUIREMENT_CHANGE: "需求变更",
    ATTRIBUTION_ENV_ANOMALY: "环境异常",
    ATTRIBUTION_DATA_ISSUE: "数据问题",
    ATTRIBUTION_CODE_REGRESSION: "代码回归",
    ATTRIBUTION_COVERAGE_GAP: "覆盖遗漏",
}

# 缺陷严重程度权重（与旧 value.py 保持一致）
SEVERITY_WEIGHT = {
    "blocker": 100.0,
    "critical": 50.0,
    "major": 10.0,
    "minor": 1.0,
}

# 单次覆盖避免回归价值
COVERAGE_POINT_VALUE = 0.5

# 风险等级
RISK_HIGH = "high"
RISK_MEDIUM = "medium"
RISK_LOW = "low"


class InsightRepo:
    """测试洞察数据访问仓库。

    直接以对应 db（统一路由 tga.db）落库，不再委托旧 app.insights.*。
    对外暴露与旧 InsightRepo 一致的类方法签名，保证上层
    （insight_service）零改动。
    """

    db_name = "trace.db"

    _schema_ensured = False

    @classmethod
    def _conn(cls) -> sqlite3.Connection:
        """获取 trace.db 连接；首次访问懒触发幂等建表。

        表 DDL 权威来源为 app.insights.trace（模块导入即建表）。
        """
        if not cls._schema_ensured:
            import app.insights.trace  # noqa: F401  触发表结构初始化
            cls._schema_ensured = True
        return Database.get_conn(cls.db_name)

    @staticmethod
    def _db(db_name: str) -> sqlite3.Connection:
        return Database.get_conn(db_name)

    # ── 执行追溯（test_runs 表 CRUD）─────────────────────
    @staticmethod
    def _capture_env() -> Dict[str, str]:
        """采集当前运行环境快照。"""
        try:
            return {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "machine": platform.machine(),
            }
        except Exception:
            return {}

    @staticmethod
    def _json_dumps(obj) -> str:
        try:
            return json.dumps(obj, ensure_ascii=False)
        except Exception:
            return "{}"

    @classmethod
    def record_trace(cls, file_path: str = "", result: str = "unknown",
                     passed_count: int = 0, failed_count: int = 0,
                     error_count: int = 0, coverage: float = 0,
                     attribution: str = "", note: str = "",
                     created_by: str = "manual") -> dict:
        """记录一次测试执行，形成可追溯的审计证据。"""
        run_id = uuid.uuid4().hex[:12]
        env_info = cls._capture_env()
        conn = cls._conn()
        conn.execute("""
            INSERT INTO test_runs
            (id, file_path, source_hash, result, passed_count, failed_count, error_count,
             coverage, env_info, attribution, note, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, file_path, "", result, passed_count, failed_count, error_count,
            coverage, cls._json_dumps(env_info), attribution, note,
            time.time(), created_by,
        ))
        return {
            "id": run_id,
            "file_path": file_path,
            "result": result,
            "coverage": coverage,
            "attribution": attribution,
            "created_at": time.time(),
        }

    @classmethod
    def list_trace(cls, file_path: Optional[str] = None,
                   result: Optional[str] = None, limit: int = 50,
                   offset: int = 0) -> list:
        """列出执行追溯记录，可按文件/结果过滤。"""
        sql = "SELECT * FROM test_runs WHERE 1=1"
        params: list = []
        if file_path:
            sql += " AND file_path LIKE ?"
            params.append(f"%{file_path}%")
        if result:
            sql += " AND result = ?"
            params.append(result)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        conn = cls._conn()
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def trace_stats(cls) -> dict:
        """获取执行追溯统计。"""
        conn = cls._conn()
        total = conn.execute("SELECT COUNT(*) AS c FROM test_runs").fetchone()["c"]
        passed = conn.execute(
            "SELECT COUNT(*) AS c FROM test_runs WHERE result='passed'"
        ).fetchone()["c"]
        failed = conn.execute(
            "SELECT COUNT(*) AS c FROM test_runs WHERE result='failed'"
        ).fetchone()["c"]
        files = conn.execute(
            "SELECT COUNT(DISTINCT file_path) AS c FROM test_runs"
        ).fetchone()["c"]
        avg_cov = conn.execute(
            "SELECT AVG(coverage) AS c FROM test_runs WHERE coverage > 0"
        ).fetchone()["c"]
        return {
            "total_runs": total,
            "passed": passed,
            "failed": failed,
            "covered_files": files,
            "avg_coverage": round(avg_cov or 0, 1),
        }

    @classmethod
    def attributions(cls) -> dict:
        """静态归因字典。纯常量，无 DB。"""
        return ATTRIBUTIONS

    @classmethod
    def prove_coverage(cls, file_path: str) -> dict:
        """针对某个文件，调出全部历史执行记录，证明已测覆盖。"""
        runs = cls.list_trace(file_path=file_path, limit=100)
        last_run = runs[0] if runs else None
        has_passed_evidence = any(r["result"] == "passed" for r in runs)
        return {
            "file_path": file_path,
            "total_runs": len(runs),
            "last_run": last_run,
            "has_passed_evidence": has_passed_evidence,
            "coverage_snapshot": last_run.get("coverage", 0) if last_run else 0,
            "runs": runs,
        }

    # ── 价值量化（查询 defects / test_cases 表）────────────
    @classmethod
    def value(cls) -> dict:
        """汇总测试价值量化指标。"""
        weight = SEVERITY_WEIGHT

        # 1. 缺陷价值
        defect_value = 0.0
        avoided_incidents = 0
        severity_breakdown = {"blocker": 0, "critical": 0, "major": 0, "minor": 0}
        defect_count = 0
        defects_conn = cls._db("defects.db")
        try:
            rows = defects_conn.execute(
                "SELECT severity, status FROM defects WHERE (deleted IS NULL OR deleted = 0)"
            ).fetchall()
            for r in rows:
                sev = r["severity"]
                defect_count += 1
                severity_breakdown[sev] = severity_breakdown.get(sev, 0) + 1
                defect_value += weight.get(sev, 0)
                if sev in ("blocker", "critical"):
                    avoided_incidents += 1
        except Exception:
            pass

        # 2. 覆盖率汇总
        coverage_summary = {"measured_files": 0, "avg_coverage": 0.0, "covered": 0, "missed": 0}
        cases_conn = cls._db("testcases.db")
        try:
            rows = cases_conn.execute("SELECT last_result FROM test_cases").fetchall()
            cov_values = []
            for r in rows:
                lr = r["last_result"]
                if not lr:
                    continue
                try:
                    data = json.loads(lr)
                except Exception:
                    continue
                cov = (data or {}).get("coverage") or (data or {}).get("coverage_pct")
                if cov is not None:
                    coverage_summary["measured_files"] += 1
                    cov_values.append(float(cov))
            if cov_values:
                coverage_summary["avg_coverage"] = round(sum(cov_values) / len(cov_values), 1)
                coverage_summary["covered"] = len([c for c in cov_values if c >= 80])
                coverage_summary["missed"] = len([c for c in cov_values if c < 80])
        except Exception:
            pass

        # 3. 综合价值分
        defect_score = min(defect_value, 50.0) * 2
        coverage_score = min(coverage_summary["avg_coverage"], 100.0) * 0.5
        value_score = round(min(defect_score + coverage_score, 100.0), 1)

        return {
            "defect_value": round(defect_value, 1),
            "defect_count": defect_count,
            "severity_breakdown": severity_breakdown,
            "avoided_incidents": avoided_incidents,
            "coverage_summary": coverage_summary,
            "value_score": value_score,
            "metric_desc": "价值分 = 缺陷严重度权重分 + 平均覆盖率折算分（各占 50 分上限）",
        }

    @classmethod
    def incident_avoidance(cls) -> dict:
        """估算测试人员避免的线上事故价值。"""
        weight = SEVERITY_WEIGHT
        fixed_defects = []
        conn = cls._db("defects.db")
        try:
            rows = conn.execute(
                "SELECT id, title, severity, status, file_path FROM defects "
                "WHERE (deleted IS NULL OR deleted = 0)"
            ).fetchall()
            for r in rows:
                if r["status"] in ("fixed", "closed"):
                    fixed_defects.append({
                        "id": r["id"],
                        "title": r["title"],
                        "severity": r["severity"],
                        "file_path": r["file_path"],
                        "weight": weight.get(r["severity"], 0),
                    })
        except Exception:
            pass

        total_weight = sum(d["weight"] for d in fixed_defects)
        high_impact = [d for d in fixed_defects if d["severity"] in ("blocker", "critical")]
        return {
            "fixed_defect_count": len(fixed_defects),
            "high_impact_fixed": len(high_impact),
            "avoided_incident_estimate": len(high_impact),
            "total_value_weight": round(total_weight, 1),
            "detail": fixed_defects[:50],
        }

    # ── 风险分析（查询 defects / test_cases 表）────────────
    @staticmethod
    def _complexity_metrics(source_code: str) -> Dict[str, int]:
        """估算代码复杂度。"""
        metrics = {"functions": 0, "branches": 0, "lines": 0}
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            metrics["lines"] = len(source_code.splitlines())
            return metrics
        metrics["lines"] = len(source_code.splitlines())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                metrics["functions"] += 1
            if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.ExceptHandler)):
                metrics["branches"] += 1
        return metrics

    @classmethod
    def assess_risk(cls, source_files: list = None) -> dict:
        """评估各模块风险，输出高风险清单。"""
        if source_files is None:
            source_files = []

        defects_conn = cls._db("defects.db")
        cases_conn = cls._db("testcases.db")

        # 收集每个文件的缺陷数
        defect_by_file: Dict[str, int] = {}
        try:
            rows = defects_conn.execute(
                "SELECT file_path FROM defects WHERE status != 'closed' "
                "AND (deleted IS NULL OR deleted = 0)"
            ).fetchall()
            for r in rows:
                fp = r["file_path"]
                defect_by_file[fp] = defect_by_file.get(fp, 0) + 1
        except Exception:
            pass

        # 收集每个文件的覆盖率
        coverage_by_file: Dict[str, float] = {}
        try:
            rows = cases_conn.execute(
                "SELECT file_path, last_result FROM test_cases"
            ).fetchall()
            for r in rows:
                lr = r["last_result"]
                fp = r["file_path"]
                cov = None
                if lr:
                    try:
                        data = json.loads(lr)
                        cov = (data or {}).get("coverage") or (data or {}).get("coverage_pct")
                    except Exception:
                        cov = None
                coverage_by_file[fp] = float(cov) if cov is not None else 0.0
        except Exception:
            pass

        assessed = []
        for f in source_files:
            path = f.get("relative_path") or f.get("path", "unknown")
            src = f.get("source_code", "")
            if not src and os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        src = fh.read()
                except Exception:
                    src = ""

            metrics = cls._complexity_metrics(src)
            complexity_score = min(40, (metrics["functions"] * 4) + (metrics["branches"] * 2))

            cov = coverage_by_file.get(path, coverage_by_file.get(f.get("path"), 0))
            coverage_gap_score = 0
            if cov > 0:
                coverage_gap_score = min(30, max(0, 30 - int(cov * 0.3)))
            else:
                coverage_gap_score = 20

            defect_count = defect_by_file.get(path, defect_by_file.get(f.get("path"), 0))
            defect_score = min(30, defect_count * 10)

            risk_score = complexity_score + coverage_gap_score + defect_score
            if risk_score >= 60:
                level = RISK_HIGH
            elif risk_score >= 30:
                level = RISK_MEDIUM
            else:
                level = RISK_LOW

            assessed.append({
                "file_path": path,
                "functions": metrics["functions"],
                "branches": metrics["branches"],
                "lines": metrics["lines"],
                "coverage": cov,
                "open_defects": defect_count,
                "risk_score": risk_score,
                "risk_level": level,
                "breakdown": {
                    "complexity": complexity_score,
                    "coverage_gap": coverage_gap_score,
                    "defect_density": defect_score,
                },
            })

        assessed.sort(key=lambda x: x["risk_score"], reverse=True)
        high = [a for a in assessed if a["risk_level"] == RISK_HIGH]
        medium = [a for a in assessed if a["risk_level"] == RISK_MEDIUM]
        return {
            "total_modules": len(assessed),
            "high_risk": high,
            "medium_risk": medium,
            "low_risk": [a for a in assessed if a["risk_level"] == RISK_LOW],
            "recommendation": (
                "发布前请优先回归以上高风险模块，并补齐覆盖率缺口。"
                if high else "暂未发现高风险模块，建议保持常规回归节奏。"
            ),
        }

    # ── 纯业务逻辑（不涉及 DB，委托旧 insights 模块）──────
    @classmethod
    def generate_from_description(cls, description: str) -> dict:
        """自然语言 → 生成 pytest 测试用例（纯代码生成逻辑）。"""
        from app.insights import lowcode
        return lowcode.generate_from_description(description)

    @classmethod
    def skill_path(cls) -> dict:
        """返回技能提升路径（纯静态业务规则）。"""
        from app.insights import lowcode
        return lowcode.skill_path()


# 兼容类方法调用（部分上层代码按类使用）
insight_repo = InsightRepo
