# app/apitest/execution_log.py
"""测试执行数据统一落库模块

将接口用例执行、场景执行等所有测试数据持久化到数据库，便于调试与测试追溯。
作为接口测试域的单一执行结果流水，统一承载接口用例/场景/调试的完整执行数据；
接口调试（debug_api_call）亦收敛于此（exec_type='debug'）。
本模块统一记录「用例运行」与「场景运行」的完整执行数据（请求、响应、断言、提取变量等）。
"""
import json
import sqlite3
import time
import uuid
from typing import Optional

from app.core.database import Database
from app.logging_config import get_logger

logger = get_logger(__name__)


def _get_conn() -> sqlite3.Connection:
    """获取数据库连接（统一使用 Database 连接池）。"""
    return Database.get_conn("apitest.db")


def _init_table() -> None:
    """初始化测试执行记录表。"""
    try:
        conn = _get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_execution_logs (
                id TEXT PRIMARY KEY,
                exec_type TEXT DEFAULT 'case',      -- case/scenario/debug
                target_id TEXT DEFAULT '',          -- 用例ID或场景ID
                target_name TEXT DEFAULT '',
                method TEXT DEFAULT 'GET',
                url TEXT DEFAULT '',
                request_data TEXT DEFAULT '{}',      -- JSON: 完整请求
                response_data TEXT DEFAULT '{}',     -- JSON: 完整响应
                asserts TEXT DEFAULT '[]',           -- JSON: 断言结果
                extracted_variables TEXT DEFAULT '{}',-- JSON: 提取的变量
                passed INTEGER DEFAULT 0,
                response_code INTEGER DEFAULT 0,
                duration_ms REAL DEFAULT 0,
                error TEXT DEFAULT '',
                detail TEXT DEFAULT '{}',            -- JSON: 附加详情(场景步骤等)
                created_at REAL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_exec_logs_type ON api_execution_logs(exec_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_exec_logs_target ON api_execution_logs(target_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_exec_logs_time ON api_execution_logs(created_at)")
        conn.commit()
    except Exception as e:
        logger.warning("初始化 api_execution_logs 表失败: %s", e)


def log_execution(
    exec_type: str,
    target_id: str = "",
    target_name: str = "",
    method: str = "GET",
    url: str = "",
    request_data: Optional[dict] = None,
    response_data: Optional[dict] = None,
    asserts: Optional[list] = None,
    extracted_variables: Optional[dict] = None,
    passed: bool = False,
    response_code: int = 0,
    duration_ms: float = 0,
    error: str = "",
    detail: Optional[dict] = None,
) -> None:
    """记录一次测试执行数据到数据库。失败静默，不影响主流程。"""
    try:
        conn = _get_conn()
        conn.execute("""
            INSERT INTO api_execution_logs (
                id, exec_type, target_id, target_name, method, url,
                request_data, response_data, asserts, extracted_variables,
                passed, response_code, duration_ms, error, detail, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            str(uuid.uuid4()),
            exec_type, target_id, target_name, method, url,
            json.dumps(request_data or {}, ensure_ascii=False),
            json.dumps(response_data or {}, ensure_ascii=False),
            json.dumps(asserts or [], ensure_ascii=False),
            json.dumps(extracted_variables or {}, ensure_ascii=False),
            1 if passed else 0,
            int(response_code or 0),
            round(float(duration_ms or 0), 2),
            error or '',
            json.dumps(detail or {}, ensure_ascii=False),
            time.time(),
        ))
        conn.commit()
    except Exception as e:
        logger.warning("记录测试执行数据失败: %s", e)


def list_execution_logs(exec_type: str = "", target_id: str = "",
                        limit: int = 100, offset: int = 0,
                        keyword: str = "") -> list:
    """查询测试执行记录（仓库内直连 SQL 已下沉）。"""
    from app.repositories.apitest_repo import ApitestRepo
    return ApitestRepo.list_execution_logs(
        exec_type, target_id, limit, offset=offset, keyword=keyword)


def count_execution_logs(exec_type: str = "", target_id: str = "",
                         keyword: str = "") -> int:
    """统计测试执行记录总数（仓库内直连 SQL 已下沉）。"""
    from app.repositories.apitest_repo import ApitestRepo
    return ApitestRepo.count_execution_logs(
        exec_type, target_id, keyword=keyword)


def clear_execution_logs(exec_type: str = "") -> int:
    """清空测试执行记录（仓库内直连 SQL 已下沉）。"""
    from app.repositories.apitest_repo import ApitestRepo
    return ApitestRepo.clear_execution_logs(exec_type)


# 模块加载时初始化表
_init_table()
