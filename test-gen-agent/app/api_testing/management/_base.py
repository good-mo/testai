# -*- coding: utf-8 -*-
"""app.api_testing.management 包基础层（自原 management.py 拆出，行为不变）。

提供统一数据库连接、列迁移与表结构初始化，被 definitions/cases/scenarios/
mocks/environments/assertions/imports/debug/execution 各子模块共享。
"""
import sqlite3

from app.apitest.schema_ddl import ensure_api_definitions_table
from app.core.database import Database


def _get_conn() -> sqlite3.Connection:
    """获取数据库连接（统一使用 Database 连接池）。"""
    return Database.get_conn("apitest.db")


def _ensure_api_columns(conn, table: str, columns: dict) -> None:
    """确保表中存在指定列，不存在则添加。"""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cursor.fetchall()}
    for col, definition in columns.items():
        if col not in existing:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
            except Exception:
                pass


def _init_tables() -> None:
    """初始化所有接口测试相关的表结构。"""
    conn = _get_conn()
    try:
        # 接口定义表
        # 说明：本模块（V1 前端兼容层）与 app.apitest.store（V2 主引擎）共用同一张
        # api_definitions 表。历史上本文件自带一份 CREATE TABLE，与 V2 的列集合不同，
        # 物理结构由 import 顺序决定 —— 这正是「注册表与实际建表漂移」的根因。
        # 现统一委托 app/apitest/schema_ddl.py 的权威 DDL（V1 ∪ V2 超集 + module_id），
        # 本模块不再持有第二份建表声明。
        ensure_api_definitions_table(conn)

        # 接口用例表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_test_cases (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                definition_id TEXT,
                method TEXT NOT NULL DEFAULT 'GET',
                path TEXT NOT NULL,
                request_headers TEXT DEFAULT '{}',
                request_params TEXT DEFAULT '{}',
                request_body TEXT DEFAULT '',
                request_body_type TEXT DEFAULT 'json',
                assertions TEXT DEFAULT '[]',      -- JSON 数组: [{type, field, value}]
                pre_scripts TEXT DEFAULT '[]',      -- JSON 数组
                post_scripts TEXT DEFAULT '[]',     -- JSON 数组
                pre_sql TEXT DEFAULT '',
                post_sql TEXT DEFAULT '',
                variables TEXT DEFAULT '{}',        -- JSON 对象: {name: {type, value}}
                enabled INTEGER DEFAULT 1,
                status TEXT DEFAULT 'draft',        -- draft/approved/deprecated
                environment_id TEXT,
                timeout INTEGER DEFAULT 30,
                retry_count INTEGER DEFAULT 0,
                created_at REAL,
                updated_at REAL,
                created_by TEXT DEFAULT 'system',
                deleted INTEGER DEFAULT 0,
                deleted_at REAL,
                project_id TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_cases_name ON api_test_cases(name)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_cases_def ON api_test_cases(definition_id)
        """)

        # Mock 服务表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mock_services (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                method TEXT NOT NULL DEFAULT 'GET',
                path TEXT NOT NULL,
                response_code INTEGER DEFAULT 200,
                response_headers TEXT DEFAULT '{}',
                response_body TEXT DEFAULT '{}',
                delay_ms INTEGER DEFAULT 0,
                enabled INTEGER DEFAULT 1,
                created_at REAL,
                updated_at REAL,
                created_by TEXT DEFAULT 'system',
                deleted INTEGER DEFAULT 0,
                deleted_at REAL,
                project_id TEXT DEFAULT ''
            )
        """)

        # 断言规则模板表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS assertion_rules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                rule_type TEXT NOT NULL,   -- text/regex/jsonpath/xpath/status_code/header
                target TEXT DEFAULT '',
                expression TEXT DEFAULT '',
                expected TEXT DEFAULT '',
                description TEXT DEFAULT '',
                created_at REAL
            )
        """)

        # 调试执行记录统一落入 api_execution_logs
        # （见 app/apitest/execution_log.py，exec_type='debug'），避免 api_debug_logs 重复建表。

        # 迁移：为历史库补充软删除列和 project_id 列
        # 注意：api_scenarios 由 app.apitest.store（V2 主引擎）建表，本模块(V1)并不负责创建。
        # 此处仅对"已存在"的表做列迁移，避免在本模块先于 V2 被 import 时
        # 因 api_scenarios 尚不存在而触发 "no such table"（import 顺序问题）。
        for table in ('api_definitions', 'api_test_cases', 'api_scenarios', 'api_environments', 'mock_services'):
            try:
                cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            except Exception:
                cols = []
            if not cols:
                # 表不存在：跳过（后续由对应创建方建表），避免 ALTER 报 no such table
                continue
            if "deleted" not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN deleted INTEGER DEFAULT 0")
                conn.execute(f"ALTER TABLE {table} ADD COLUMN deleted_at REAL")
            if "project_id" not in cols:
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN project_id TEXT DEFAULT ''")
                except Exception:
                    pass
        conn.commit()
    finally:
        pass  # shared cached conn


_init_tables()
