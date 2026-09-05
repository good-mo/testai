# app/repositories/script_repo.py
"""脚本健康度数据访问层。

本层是 scripthealth 域唯一权威：同时持有表结构 DDL、数据访问 SQL
与纯计算业务规则。
- 表结构（scripts / execution_history）由本模块 _init_db 幂等建表，
  作为 schema_registry 单一权威来源。
- 纯计算辅助（evaluate_selector / recommend_stable_strategy —— 不涉及
  数据库，是选择器稳定性评估 / 策略推荐的业务规则）一并收拢至本模块。

纯数据访问（scripts / execution_history 的 CRUD / 执行记录 / 统计）
均在仓库内直连 SQL，输出统一（locators_json / locator_failures_json
等 JSON 字段反序列化等）。
"""
import json
import logging
import re
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.database import Database

logger = logging.getLogger(__name__)

# 定位策略类型（与旧 monitor 保持一致，兼容常量）
LOCATOR_CSS = "css"
LOCATOR_XPATH = "xpath"
LOCATOR_TESTID = "data-testid"
LOCATOR_TEXT = "text"
LOCATOR_NAME = "name"
LOCATOR_ID = "id"

DB_NAME = "scripthealth.db"


def _get_conn() -> sqlite3.Connection:
    """获取 scripthealth.db 连接（统一使用 Database 连接池）。"""
    return Database.get_conn(DB_NAME)


def _init_db() -> None:
    """幂等建表（权威 DDL，供 schema_registry / 迁移兜底引用）。"""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scripts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                file_path TEXT DEFAULT '',
                framework TEXT DEFAULT 'pytest',
                description TEXT DEFAULT '',
                locators_json TEXT DEFAULT '[]',
                total_runs INTEGER DEFAULT 0,
                success_runs INTEGER DEFAULT 0,
                fail_runs INTEGER DEFAULT 0,
                last_run_at REAL,
                last_status TEXT DEFAULT '',
                health_score REAL DEFAULT 100.0,
                status TEXT DEFAULT 'healthy',
                created_at REAL,
                updated_at REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS execution_history (
                id TEXT PRIMARY KEY,
                script_id TEXT DEFAULT '',
                script_name TEXT DEFAULT '',
                success INTEGER DEFAULT 0,
                duration REAL DEFAULT 0,
                error_type TEXT DEFAULT '',
                error_message TEXT DEFAULT '',
                locator_failures_json TEXT DEFAULT '[]',
                created_at REAL
            )
        """)
        conn.commit()
    finally:
        pass


_init_db()


# ── 纯逻辑辅助（不涉及 DB，业务规则收拢于仓库层）──────────

def evaluate_selector(strategy: str, selector: str) -> Dict[str, Any]:
    """评估定位器的稳定性。返回稳定性评分 0-100，以及建议。"""
    score = 100.0
    suggestions = []

    if strategy == LOCATOR_TESTID:
        if len(selector) < 3:
            score -= 10
            suggestions.append("data-testid 名称过短，建议使用有意义的命名")
        elif not re.match(r'^[a-zA-Z0-9_-]+$', selector):
            score -= 15
            suggestions.append("data-testid 应使用字母/数字/下划线/中划线")
        return {"score": score, "strategy": strategy, "suggestions": suggestions,
                "verdict": "stable" if score >= 80 else "needs_attention"}

    elif strategy == LOCATOR_CSS:
        if selector.startswith("div") or selector.startswith("span"):
            score -= 10
            suggestions.append("使用通用标签选择器，建议添加 class 或 id")
        if "> " in selector or " > " in selector:
            score -= 5
            suggestions.append("深层嵌套选择器可能脆弱，建议减少层级")
        if selector.startswith("#"):
            score += 5
        if "nth-child" in selector or "nth-of-type" in selector:
            score -= 30
            suggestions.append("nth-child/nth-of-type 是脆弱定位器，页面元素变化会导致失败")
        if "[" in selector and "data-testid" in selector:
            score += 20
            suggestions.append("使用 data-testid 属性，稳定性高")
        if "class" in selector or "." in selector:
            score += 5
        if score > 100:
            score = 100
        if score < 50:
            suggestions.append("建议改用 data-testid 属性定位")

    elif strategy == LOCATOR_XPATH:
        if "//" in selector and "text()" in selector:
            score -= 15
            suggestions.append("文本匹配 XPath 脆弱，建议改用 data-testid")
        if "position()" in selector or "[1]" in selector:
            score -= 20
            suggestions.append("使用 position() 或 [1] 的 XPath 脆弱，页面变化会导致失败")
        if "contains(" in selector:
            score -= 10
            suggestions.append("contains() 匹配可能不稳定，建议使用精确属性")
        if "@data-testid" in selector:
            score += 20
            suggestions.append("使用 data-testid 属性，稳定性高")

    elif strategy == LOCATOR_TEXT:
        score = 40
        suggestions.append("文本定位最脆弱，页面文案改变即失败")
        suggestions.append("建议改用 data-testid 或稳定的 CSS 选择器")

    elif strategy == LOCATOR_NAME:
        score = 70
        suggestions.append("name 属性定位较稳定，但可能与业务数据冲突")
    elif strategy == LOCATOR_ID:
        score = 85
        if re.match(r'^[0-9]', selector):
            score -= 15
            suggestions.append("ID 以数字开头，可能存在动态生成风险")

    if score > 100:
        score = 100.0

    verdict = "stable" if score >= 80 else ("needs_attention" if score >= 50 else "unstable")
    return {"score": score, "strategy": strategy, "suggestions": suggestions, "verdict": verdict}


def recommend_stable_strategy(selector: str, strategy: str = LOCATOR_CSS) -> Dict[str, Any]:
    """为给定选择器推荐稳定的定位策略。"""
    evaluation = evaluate_selector(strategy, selector)
    if evaluation["score"] >= 80:
        return {
            "current_strategy": strategy,
            "current_selector": selector,
            "recommendation": "当前定位器稳定，无需修改",
            "alternatives": [],
            "score": evaluation["score"],
        }

    alternatives = []
    if strategy == LOCATOR_XPATH:
        testid_match = re.search(r'@data-testid=["\']([^"\']+)["\']', selector)
        if testid_match:
            alternatives.append({
                "strategy": LOCATOR_TESTID,
                "selector": testid_match.group(1),
                "reason": "从 XPath 中提取了 data-testid，稳定性更高",
            })
        alternatives.append({
            "strategy": LOCATOR_CSS,
            "selector": "添加 data-testid 属性后用 CSS 定位",
            "reason": "建议在 HTML 元素上添加 data-testid 属性",
        })
    elif strategy == LOCATOR_CSS:
        alternatives.append({
            "strategy": LOCATOR_TESTID,
            "selector": "使用 data-testid",
            "reason": "data-testid 是业界最佳实践，不受 UI 样式变化影响",
        })
    elif strategy == LOCATOR_TEXT:
        alternatives.append({
            "strategy": LOCATOR_CSS,
            "selector": "为元素添加 class 或 data-testid",
            "reason": "文本定位脆弱，应使用稳定的属性定位",
        })
        alternatives.append({
            "strategy": LOCATOR_TESTID,
            "selector": "使用 data-testid",
            "reason": "data-testid 是最稳定的定位方式",
        })

    return {
        "current_strategy": strategy,
        "current_selector": selector,
        "recommendation": f"当前定位器稳定性评分 {evaluation['score']}，建议优化",
        "alternatives": alternatives,
        "score": evaluation["score"],
    }


class ScriptRepo:
    """脚本健康度数据访问仓库。

    直接以 scripthealth.db（统一路由 tga.db）落库。
    对外暴露类方法签名，供 script_service 调用。
    """

    db_name = DB_NAME

    @classmethod
    def _conn(cls) -> sqlite3.Connection:
        """获取 scripthealth.db 连接（表已由模块导入时 _init_db 建好）。"""
        return _get_conn()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Optional[Dict[str, Any]]:
        """裸行 → 归一化输出（JSON 字段反序列化，与旧 monitor 一致）。"""
        if row is None:
            return None
        data = dict(row)
        for k in ("locators_json", "alternatives_json", "locator_failures_json"):
            if data.get(k):
                try:
                    data[k.replace("_json", "")] = json.loads(data[k])
                    data.pop(k, None)
                except (json.JSONDecodeError, TypeError):
                    pass
        if "locators_json" in data:
            data["locators"] = data.pop("locators_json")
        return data

    @staticmethod
    def _execution_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        """执行记录行 → dict（locator_failures JSON 反序列化）。"""
        d = dict(row)
        if d.get("locator_failures_json"):
            try:
                d["locator_failures"] = json.loads(d["locator_failures_json"])
            except (json.JSONDecodeError, TypeError):
                d["locator_failures"] = []
        d.pop("locator_failures_json", None)
        return d

    @staticmethod
    def _calc_health_score(total: int, success_count: int, fail_count: int,
                           previous_score: float, last_success: bool) -> float:
        """计算健康度评分（0-100）。"""
        success_rate = success_count / total if total > 0 else 1.0
        base_score = success_rate * 100.0
        penalty = 0.0
        if not last_success:
            penalty += 10.0
        if fail_count >= 3:
            penalty += 5.0 * min(fail_count, 10)
        score = max(0, min(100, base_score - penalty))
        smoothed = previous_score * 0.7 + score * 0.3
        return round(max(0, min(100, smoothed)), 1)

    @staticmethod
    def _determine_status(health_score: float) -> str:
        if health_score >= 85:
            return "healthy"
        elif health_score >= 60:
            return "unstable"
        return "degraded"

    # ── 纯逻辑辅助（不涉及 DB，业务规则收拢于仓库层）──
    @classmethod
    def evaluate_selector(cls, strategy: str, selector: str) -> dict:
        """评估定位器的稳定性（纯计算，不涉及 DB）。"""
        return evaluate_selector(strategy, selector)

    @classmethod
    def recommend_strategy(cls, selector: str, strategy: str) -> dict:
        """为给定选择器推荐稳定的定位策略（纯计算，不涉及 DB）。"""
        return recommend_stable_strategy(selector, strategy)

    # ══════════════════════════════════════════════════════
    # 脚本管理（DB CRUD）
    # ══════════════════════════════════════════════════════
    @classmethod
    def register(cls, name: str, file_path: str = "", framework: str = "",
                 description: str = "", locators: list = None) -> dict:
        script_id = uuid.uuid4().hex[:12]
        now = time.time()
        conn = cls._conn()
        conn.execute(
            """INSERT INTO scripts
               (id, name, file_path, framework, description, locators_json,
                total_runs, success_runs, fail_runs, status,
                health_score, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, 'healthy', 100.0, ?, ?)""",
            (script_id, name, file_path, framework, description,
             json.dumps(locators or []), now, now),
        )
        return cls.get(script_id) or {"id": script_id}

    @classmethod
    def get(cls, script_id: str) -> Optional[dict]:
        conn = cls._conn()
        row = conn.execute(
            "SELECT * FROM scripts WHERE id = ?", (script_id,)
        ).fetchone()
        return cls._row_to_dict(row)

    @classmethod
    def list(cls, status: Optional[str] = None, search: Optional[str] = None,
             limit: int = 100, offset: int = 0) -> list:
        query = "SELECT * FROM scripts WHERE 1=1"
        params: List = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if search:
            query += " AND (name LIKE ? OR file_path LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        conn = cls._conn()
        rows = conn.execute(query, params).fetchall()
        return [cls._row_to_dict(r) for r in rows]

    @classmethod
    def update(cls, script_id: str, **kwargs) -> Optional[dict]:
        existing = cls.get(script_id)
        if not existing:
            return None

        allowed = {"name", "file_path", "framework", "description", "locators",
                   "total_runs", "success_runs", "fail_runs", "last_run_at",
                   "last_status", "health_score", "status"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}

        if "locators" in updates and isinstance(updates["locators"], list):
            updates["locators_json"] = json.dumps(updates["locators"])
            del updates["locators"]

        if not updates:
            return existing

        updates["updated_at"] = time.time()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [script_id]

        conn = cls._conn()
        conn.execute(f"UPDATE scripts SET {set_clause} WHERE id = ?", values)
        return cls.get(script_id)

    @classmethod
    def delete(cls, script_id: str) -> bool:
        conn = cls._conn()
        cur = conn.execute("DELETE FROM scripts WHERE id = ?", (script_id,))
        return cur.rowcount > 0

    # ══════════════════════════════════════════════════════
    # 执行记录与健康度监控
    # ══════════════════════════════════════════════════════
    @classmethod
    def record_execution(cls, script_id: str, success: bool = True,
                         duration: float = 0, error_type: str = "",
                         error_message: str = "", locator_failures: list = None) -> dict:
        """记录一次脚本执行，并自动更新健康度评分。"""
        script = cls.get(script_id)
        if not script:
            return {"success": False, "error": f"脚本 {script_id} 不存在"}

        now = time.time()
        hist_id = uuid.uuid4().hex[:12]
        conn = cls._conn()
        conn.execute(
            """INSERT INTO execution_history
               (id, script_id, script_name, success, duration,
                error_type, error_message, locator_failures_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (hist_id, script_id, script.get("name", ""),
             1 if success else 0, duration,
             error_type, error_message,
             json.dumps(locator_failures or []), now),
        )

        # 更新脚本统计
        total = script.get("total_runs", 0) + 1
        success_count = script.get("success_runs", 0) + (1 if success else 0)
        fail_count = script.get("fail_runs", 0) + (0 if success else 1)

        health_score = cls._calc_health_score(
            total, success_count, fail_count,
            script.get("health_score", 100.0), success,
        )
        status = cls._determine_status(health_score)

        cls.update(
            script_id,
            total_runs=total, success_runs=success_count, fail_runs=fail_count,
            last_run_at=now, last_status="success" if success else "failed",
            health_score=health_score, status=status,
        )

        # 有定位器失败时触发自动修复
        repair_results = []
        if locator_failures:
            for failure in locator_failures:
                repair = cls.auto_repair(script_id, failure.get("name", ""))
                if repair.get("success"):
                    repair_results.append(repair)

        return {
            "success": True,
            "history_id": hist_id,
            "health_score": health_score,
            "status": status,
            "auto_repairs": repair_results,
        }

    @classmethod
    def auto_repair(cls, script_id: str, locator_name: str) -> dict:
        """自动修复失效的定位器。分析失败原因，从替代策略中选取最优方案并更新。"""
        script = cls.get(script_id)
        if not script:
            return {"success": False, "error": f"脚本 {script_id} 不存在"}

        locators = script.get("locators", [])
        target = None
        for loc in locators:
            if loc.get("name") == locator_name:
                target = loc
                break

        if not target:
            return {"success": False, "error": f"定位器 {locator_name} 不存在"}

        # 获取替代策略
        alternatives = target.get("alternatives", [])
        if not alternatives:
            recommendation = cls.recommend_strategy(
                target.get("current_selector", ""),
                target.get("current_strategy", LOCATOR_CSS),
            )
            alternatives = recommendation.get("alternatives", [])

        if not alternatives:
            return {
                "success": False,
                "error": "无法自动修复，需要手动更新定位器",
                "suggestion": "建议在页面元素上添加 data-testid 属性",
            }

        # 选择最优替代方案（优先 data-testid）
        best = None
        for alt in alternatives:
            if alt["strategy"] == LOCATOR_TESTID:
                best = alt
                break
        if not best and alternatives:
            best = alternatives[0]

        # 更新定位器
        target["current_strategy"] = best["strategy"]
        target["current_selector"] = best["selector"]
        target["best_strategy"] = best["strategy"]
        target["best_selector"] = best["selector"]
        target["status"] = "repaired"
        target["updated_at"] = time.time()

        # 更新脚本中的定位器
        for i, loc in enumerate(locators):
            if loc.get("name") == locator_name:
                locators[i] = target
                break

        cls.update(script_id, locators=locators)

        return {
            "success": True,
            "locator": locator_name,
            "old_strategy": target.get("current_strategy", ""),
            "new_strategy": best["strategy"],
            "new_selector": best["selector"],
            "message": f"已自动修复定位器，改用 {best['strategy']} 策略",
        }

    @classmethod
    def list_executions(cls, script_id: str, limit: int = 20) -> list:
        query = "SELECT * FROM execution_history WHERE 1=1"
        params: List = []
        if script_id:
            query += " AND script_id = ?"
            params.append(script_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        conn = cls._conn()
        rows = conn.execute(query, params).fetchall()
        return [cls._execution_to_dict(r) for r in rows]

    @classmethod
    def stats(cls) -> dict:
        """获取脚本健康度整体统计。"""
        conn = cls._conn()
        script_total = conn.execute("SELECT COUNT(*) FROM scripts").fetchone()[0]
        by_status = {s: 0 for s in ("healthy", "unstable", "degraded")}
        for row in conn.execute(
            "SELECT status, COUNT(*) AS cnt FROM scripts GROUP BY status"
        ):
            if row["status"] in by_status:
                by_status[row["status"]] = row["cnt"]

        exec_total = conn.execute("SELECT COUNT(*) FROM execution_history").fetchone()[0]
        exec_success = conn.execute(
            "SELECT COUNT(*) FROM execution_history WHERE success = 1"
        ).fetchone()[0]
        exec_fail = exec_total - exec_success

        avg_health = conn.execute(
            "SELECT AVG(health_score) FROM scripts"
        ).fetchone()[0] or 0

        recent_failures = conn.execute(
            "SELECT COUNT(*) FROM execution_history WHERE success = 0 AND created_at > ?",
            (time.time() - 24 * 3600,),
        ).fetchone()[0]

        return {
            "script_total": script_total,
            "script_by_status": by_status,
            "exec_total": exec_total,
            "exec_success": exec_success,
            "exec_fail": exec_fail,
            "avg_health_score": round(float(avg_health), 1),
            "recent_24h_failures": recent_failures,
        }


# 兼容类方法调用（部分上层代码按类使用）
script_repo = ScriptRepo
