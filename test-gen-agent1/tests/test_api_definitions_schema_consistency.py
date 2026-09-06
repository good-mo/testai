"""api_definitions 单一真源回归测试。

背景：app.api_testing.management（V1 前端兼容层）与 app.apitest.store（V2 主引擎）
曾各自持有一份 api_definitions 建表声明，物理列结构由 import 顺序决定，
既让 schema_registry 出现同表名 2 个物理版本，也让 module_id 这类
"SQL 在用、两边 DDL 都没建"的列在运行期炸出 no such column。

本测试锁定三点：
  1. 全仓只有一处 api_definitions 建表声明；
  2. 注册表的 DDL 与该权威声明逐列一致；
  3. 无论先 import 哪一侧，物理表列集合都等于权威 DDL 的列集合，
     且 V1/V2 两侧具备的列都在其中（含 module_id）。
"""
import os
import re
import subprocess
import sys
import textwrap

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.apitest.schema_ddl import (  # noqa: E402
    API_DEFINITIONS_DDL,
    api_definitions_columns,
)
from app.core.database import Database  # noqa: E402

# 权威 DDL 覆盖两侧列：V2 主引擎列 + V1 前端兼容层列 + 运行期使用的 module_id
V2_REQUIRED = [
    "headers", "body", "query", "params", "project_id", "version_id",
    "ref_id", "latest", "metadata",
]
V1_REQUIRED = [
    "request_headers", "request_params", "request_body", "request_body_type",
    "response_code", "response_headers", "response_body", "response_body_type",
    "created_by",
]
RUNTIME_REQUIRED = ["module_id", "deleted", "deleted_at"]


def _physical_columns(conn=None):
    """读取 apitest.db 中 api_definitions 的实际列。

    先触发权威建表，保证单跑本文件时（全新库）也能取到列。
    """
    from app.apitest.schema_ddl import ensure_api_definitions_table

    if conn is None:
        ensure_api_definitions_table()
        conn = Database.get_conn("apitest.db")
    return [row[1] for row in conn.execute("PRAGMA table_info(api_definitions)")]


class TestSingleSourceOfTruth:
    """全仓只有一处 api_definitions 建表声明。"""

    def test_only_one_create_table_statement(self):
        # schema_registry.py 是「声明注册处」，其 DDL 由同步脚本从权威声明采集而来，
        # 不参与实际建表，因此不计入建表声明来源。
        registry = "app/core/schema_registry.py"
        pattern = re.compile(
            r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+api_definitions\s*\(",
            re.IGNORECASE,
        )
        hits = []
        for root, _dirs, files in os.walk(os.path.join(PROJECT_ROOT, "app")):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                rel = os.path.relpath(os.path.join(root, fname), PROJECT_ROOT)
                if rel == registry:
                    continue
                with open(os.path.join(root, fname), encoding="utf-8") as f:
                    for _ in pattern.finditer(f.read()):
                        hits.append(rel)
        assert hits == ["app/apitest/schema_ddl.py"], (
            f"api_definitions 应只在 app/apitest/schema_ddl.py 建表，实际出现在: {hits}"
        )

    def test_registry_ddl_matches_authoritative_ddl(self):
        from app.core.schema_registry import TABLE_DDL

        def norm(sql):
            return re.sub(r"\s+", " ", re.sub(r"--[^\n]*", "", sql)).strip()

        assert norm(TABLE_DDL["api_definitions"]) == norm(API_DEFINITIONS_DDL)

    def test_sync_check_reports_no_conflict(self):
        """CI 用的漂移检查脚本应判定为 0 处 schema 冲突。"""
        proc = subprocess.run(
            [sys.executable, "scripts/sync_schema_registry.py", "--check"],
            cwd=PROJECT_ROOT, capture_output=True, text=True,
        )
        assert "0 处 schema 冲突" in proc.stdout, proc.stdout + proc.stderr
        assert proc.returncode == 0, proc.stdout + proc.stderr


class TestColumnsAreSuperset:
    """权威列集合 = V2 ∪ V1 ∪ 运行期使用列。"""

    def test_cover_both_impl_columns(self):
        cols = {name for name, _ in api_definitions_columns()}
        for required in (V2_REQUIRED, V1_REQUIRED, RUNTIME_REQUIRED):
            missing = [c for c in required if c not in cols]
            assert not missing, f"权威 DDL 缺列: {missing}"

    def test_soft_delete_pair(self):
        cols = {name for name, _ in api_definitions_columns()}
        assert {"deleted", "deleted_at"} <= cols

    def test_physical_table_matches_ddl(self):
        """存量库列顺序可能不同（历史 ALTER 追加），但列集合必须一致。"""
        expected = {name for name, _ in api_definitions_columns()}
        assert set(_physical_columns()) == expected


class TestImportOrderIndependence:
    """物理列集合不得受 import 顺序影响（原漂移的根因）。"""

    @staticmethod
    def _run_child(import_first: str, db_path: str):
        code = textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {PROJECT_ROOT!r})
            import app.db as _db
            _db.db_path = lambda filename: {db_path!r}
            import app.core.database as _cdb
            _cdb.db_path = lambda filename: {db_path!r}
            if {import_first!r} == "v1":
                import app.api_testing.management as _m  # noqa: F401
                import app.apitest.store as _s  # noqa: F401
            else:
                import app.apitest.store as _s  # noqa: F401
                import app.api_testing.management as _m  # noqa: F401
            from app.core.database import Database
            conn = Database.get_conn("apitest.db")
            print(",".join(r[1] for r in conn.execute("PRAGMA table_info(api_definitions)")))
            """
        )
        proc = subprocess.run(
            [sys.executable, "-c", code], cwd=PROJECT_ROOT,
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stderr
        return proc.stdout.strip().split(",")

    def test_v1_and_v2_first_produce_same_columns(self, tmp_path):
        expected = [name for name, _ in api_definitions_columns()]
        for tag, order in (("v1", "v1"), ("v2", "v2")):
            db_file = str(tmp_path / f"{tag}.db")
            assert self._run_child(order, db_file) == expected, (
                f"{order} 先建表时列集合与权威 DDL 不一致"
            )


class TestLegacyDatabaseMigration:
    """存量库补列：数据不丢、列集合收敛到权威 DDL。"""

    def test_legacy_table_gets_missing_columns(self, tmp_path):
        import sqlite3

        from app.apitest.schema_ddl import ensure_api_definitions_table

        db_file = str(tmp_path / "legacy.db")
        conn = sqlite3.connect(db_file)
        try:
            # 模拟历史遗留库：只有 V2 主引擎的列，没有 module_id 与 V1 兼容层列
            conn.execute(
                "CREATE TABLE IF NOT EXISTS api_definitions ("
                "id TEXT PRIMARY KEY, name TEXT NOT NULL, protocol TEXT DEFAULT 'HTTP',"
                "method TEXT DEFAULT 'GET', path TEXT DEFAULT '', headers TEXT DEFAULT '{}',"
                "project_id TEXT DEFAULT '', created_at REAL, updated_at REAL,"
                "deleted INTEGER DEFAULT 0, deleted_at REAL)"
            )
            conn.execute(
                "INSERT INTO api_definitions (id, name, path) VALUES ('1', 'legacy', '/x')"
            )
            conn.commit()

            ensure_api_definitions_table(conn)

            cols = {row[1] for row in conn.execute("PRAGMA table_info(api_definitions)")}
            assert cols == {name for name, _ in api_definitions_columns()}
            # 原有数据不丢，新增列取到 DDL 默认值
            row = conn.execute("SELECT name, path, module_id FROM api_definitions").fetchone()
            assert row[0] == "legacy" and row[1] == "/x" and row[2] == ""
        finally:
            conn.close()

    def test_migration_is_idempotent(self):
        from app.apitest.schema_ddl import ensure_api_definitions_table

        ensure_api_definitions_table()
        before = _physical_columns()
        ensure_api_definitions_table()
        ensure_api_definitions_table()
        assert _physical_columns() == before


class TestAlembicBaseline:
    """Alembic 基线建出的库与权威 DDL 一致（新库不再缺列）。"""

    def test_baseline_creates_authoritative_columns(self, tmp_path):
        db_file = tmp_path / "alembic.db"
        env = dict(os.environ, TGA_DB_PATH=str(db_file))
        proc = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, env=env,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr

        import sqlite3

        conn = sqlite3.connect(str(db_file))
        try:
            cols = [
                row[1] for row in conn.execute("PRAGMA table_info(api_definitions)")
            ]
        finally:
            conn.close()
        assert set(cols) == {name for name, _ in api_definitions_columns()}


class TestModuleFilterUsable:
    """module_id 列真实可用（历史上 SQL 在用、列却不存在）。"""

    def test_list_and_count_by_module_ids(self):
        from app.apitest import store as s

        created = []
        try:
            item = s.create_definition(name="[schema]模块筛选用例", module_id="mod-schema")
            created.append(item["id"])
            # 未归模块的记录：module_id 为空，按 root 口径处理
            unassigned = s.create_definition(name="[schema]未归模块用例")
            created.append(unassigned["id"])

            listed = [d["id"] for d in s.list_definitions(module_ids=["mod-schema"])]
            assert item["id"] in listed
            assert unassigned["id"] not in listed
            assert s.count_definitions(module_ids=["mod-schema"]) == 1
            # 空 module_id 与 root 同口径，能被 root 筛出
            root_ids = [d["id"] for d in s.list_definitions(module_ids=["root"])]
            assert unassigned["id"] in root_ids
            assert s.count_definitions(module_ids=["root"]) >= 1

            counts = s.count_definitions_by_module()
            assert counts.get("mod-schema") == 1
        finally:
            for def_id in created:
                s.purge_definition(def_id)

    def test_update_definition_module_id(self):
        from app.apitest import store as s

        item = s.create_definition(name="[schema]移动模块用例")
        try:
            moved = s.update_definition(item["id"], module_id="mod-target")
            assert moved["module_id"] == "mod-target"
            assert s.count_definitions_by_module().get("mod-target") == 1
        finally:
            s.purge_definition(item["id"])

    def test_definition_page_endpoint_with_module_ids(self, auth_client):
        """/api/definition/page 带 moduleIds 不再 500。"""
        resp = auth_client.post(
            "/api/definition/page",
            json={"current": 1, "pageSize": 10, "moduleIds": ["not-exist"]},
        )
        assert resp.status_code == 200
        data = resp.json().get("data", resp.json())
        assert "list" in data
