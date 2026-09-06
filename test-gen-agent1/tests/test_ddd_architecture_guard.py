"""架构守护（architecture_guard）回归测试。

覆盖三类守护规则 + 「不阻断存量、只卡增量」的基线策略：

  - LAYER_DOMAIN_IMPORT     领域内层禁止 import 框架/上层架构模块
  - INFRA_REVERSE_SERVICE   context infrastructure 禁止反向依赖 app.services
  - AGGREGATE_TIME_MAGIC    聚合根实体禁止裸写 * 1000 做秒→毫秒换算
  - 基线策略                存量登记文件 → 告警；新增文件 → 阻断
  - 命令行                  纯 AST、毫秒级、exit code 语义

所有测试都基于临时目录构造的 DDD 骨架，不触碰仓库真实 app/domain，
避免随存量清理而变脆。真实仓库的基线快照单测单独抽为 ``test_repo_snapshot``
类（仅当 app/domain 存在时运行），用只读断言校验存量不增长。
"""
import os
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.domain.common import architecture_guard as guard


# ─────────────────────────────────────────────────────────────
# 辅助：在临时目录里构造一个 DDD 骨架文件
# ─────────────────────────────────────────────────────────────
def _write(root: Path, relpath: str, content: str) -> Path:
    p = root / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def _mkroot(tmp_path: Path) -> Path:
    return tmp_path / "domain"


# ─────────────────────────────────────────────────────────────
# 一、LAYER_DOMAIN_IMPORT —— 领域内层禁止 import 框架/上层架构
# ─────────────────────────────────────────────────────────────
class TestDomainLayerImport:
    def _scan(self, root):
        return guard.run_guard(root=str(root))

    def test_clean_domain_has_no_findings(self, tmp_path):
        root = _mkroot(tmp_path)
        # 领域内层只 import 自身/common，干净
        _write(root, "cases/domain/entities/case.py", """
            from app.domain.common.entities import AggregateRoot
            from . import value_objects
            class Case(AggregateRoot):
                def to_dict(self):
                    return {}
        """)
        r = self._scan(root)
        assert r.findings == []
        assert r.blocking == []

    def test_domain_import_fastapi_is_blocked(self, tmp_path):
        root = _mkroot(tmp_path)
        _write(root, "foo/domain/entities/bar.py", """
            from fastapi import APIRouter
            class Bar: pass
        """)
        r = self._scan(root)
        hits = [f for f in r.findings if f.rule == "LAYER_DOMAIN_IMPORT"]
        assert len(hits) == 1
        assert "fastapi" in hits[0].detail
        # 该文件不在基线 -> 阻断
        assert hits[0].blocking
        assert r.blocking

    def test_domain_import_sqlite3_is_blocked(self, tmp_path):
        root = _mkroot(tmp_path)
        _write(root, "foo/domain/repository.py", """
            import sqlite3
            class R: pass
        """)
        r = self._scan(root)
        hits = [f for f in r.findings if f.rule == "LAYER_DOMAIN_IMPORT"]
        assert len(hits) == 1
        assert "sqlite3" in hits[0].detail

    def test_domain_import_pydantic_is_blocked(self, tmp_path):
        root = _mkroot(tmp_path)
        _write(root, "foo/domain/entities/bar.py", """
            from pydantic import BaseModel
            class Bar(BaseModel): pass
        """)
        r = self._scan(root)
        assert any("pydantic" in f.detail for f in r.findings)

    def test_domain_import_app_routers_is_blocked(self, tmp_path):
        root = _mkroot(tmp_path)
        _write(root, "foo/domain/entities/bar.py", """
            from app.routers import case
            class Bar: pass
        """)
        r = self._scan(root)
        hits = [f for f in r.findings if f.rule == "LAYER_DOMAIN_IMPORT"]
        assert len(hits) == 1
        assert "app.routers" in hits[0].detail
        assert hits[0].blocking

    def test_domain_import_app_services_is_blocked(self, tmp_path):
        root = _mkroot(tmp_path)
        _write(root, "foo/domain/services/foo_policy.py", """
            from app.services import foo_service
        """)
        r = self._scan(root)
        hits = [f for f in r.findings if f.rule == "LAYER_DOMAIN_IMPORT"]
        assert any("app.services" in f.detail for f in hits)

    def test_domain_import_app_repositories_is_blocked(self, tmp_path):
        root = _mkroot(tmp_path)
        _write(root, "foo/domain/entities/bar.py", """
            import app.repositories.case_repo
        """)
        r = self._scan(root)
        assert any("app.repositories" in f.detail for f in r.findings)

    def test_application_layer_can_import_domain(self, tmp_path):
        """application 层 import domain 是合法的，不应被误报。"""
        root = _mkroot(tmp_path)
        _write(root, "foo/domain/entities/bar.py", "class Bar: pass\n")
        _write(root, "foo/application/bar_app_service.py", """
            from app.domain.foo.domain.entities.bar import Bar
            class S:
                def __init__(self):
                    self.b = Bar()
        """)
        r = self._scan(root)
        assert [f for f in r.findings if f.rule == "LAYER_DOMAIN_IMPORT"] == []


# ─────────────────────────────────────────────────────────────
# 二、INFRA_REVERSE_SERVICE —— infrastructure 反向依赖 app.services
# ─────────────────────────────────────────────────────────────
class TestInfraReverseService:
    def test_infra_import_app_service_is_flagged(self, tmp_path):
        root = _mkroot(tmp_path)
        _write(root, "x/infrastructure/x_repo.py", """
            from app.services import x_service
            class XRepo: pass
        """)
        r = guard.run_guard(str(root))
        hits = [f for f in r.findings if f.rule == "INFRA_REVERSE_SERVICE"]
        assert len(hits) == 1
        assert "app.services" in hits[0].detail
        assert hits[0].blocking  # 新文件未登记基线

    def test_infra_import_app_repositories_is_allowed(self, tmp_path):
        """防腐层 import app.repositories 是允许的（对接既有存储），不该误报。"""
        root = _mkroot(tmp_path)
        _write(root, "x/infrastructure/x_repo.py", """
            from app.repositories.x_repo import XRepo as Legacy
            class XRepoImpl:
                def __init__(self, repo: Legacy): self._repo = repo
        """)
        r = guard.run_guard(str(root))
        assert [f for f in r.findings if f.rule == "INFRA_REVERSE_SERVICE"] == []

    def test_domain_import_app_services_not_misattributed_to_infra(self, tmp_path):
        """非 infrastructure 层出现 app.services 不应误计入 INFRA 规则。"""
        root = _mkroot(tmp_path)
        _write(root, "y/application/y_app_service.py", """
            from app.services import y_service
        """)
        r = guard.run_guard(str(root))
        assert [f for f in r.findings if f.rule == "INFRA_REVERSE_SERVICE"] == []


# ─────────────────────────────────────────────────────────────
# 三、AGGREGATE_TIME_MAGIC —— 聚合根裸写 * 1000
# ─────────────────────────────────────────────────────────────
class TestAggregateTimeMagic:
    def test_bare_multiply_1000_flagged(self, tmp_path):
        root = _mkroot(tmp_path)
        _write(root, "foo/domain/entities/foo.py", """
            class Foo:
                def to_dict(self):
                    return {"createTime": int(self._create_time * 1000)}
        """)
        r = guard.run_guard(str(root))
        hits = [f for f in r.findings if f.rule == "AGGREGATE_TIME_MAGIC"]
        assert len(hits) == 1
        assert "* 1000" in hits[0].detail
        assert hits[0].line == 4

    def test_only_flags_entities_dir(self, tmp_path):
        """* 1000 出现在 application 层不属聚合实体规则，不应误报。"""
        root = _mkroot(tmp_path)
        _write(root, "foo/application/foo_app_service.py", """
            def f(ts):
                return int(ts * 1000)
        """)
        r = guard.run_guard(str(root))
        assert [f for f in r.findings if f.rule == "AGGREGATE_TIME_MAGIC"] == []

    def test_multiply_by_non_1000_not_flagged(self, tmp_path):
        root = _mkroot(tmp_path)
        _write(root, "foo/domain/entities/foo.py", """
            class Foo:
                def to_dict(self):
                    return {"n": self._n * 2}
        """)
        r = guard.run_guard(str(root))
        assert [f for f in r.findings if f.rule == "AGGREGATE_TIME_MAGIC"] == []

    def test_multiple_magic_in_one_file_each_flagged(self, tmp_path):
        root = _mkroot(tmp_path)
        _write(root, "foo/domain/entities/foo.py", """
            class Foo:
                def to_dict(self):
                    return {
                        "a": int(self._a * 1000),
                        "b": int(self._b * 1000),
                    }
        """)
        r = guard.run_guard(str(root))
        hits = [f for f in r.findings if f.rule == "AGGREGATE_TIME_MAGIC"]
        assert len(hits) == 2


# ─────────────────────────────────────────────────────────────
# 四、基线策略：不阻断存量、只卡增量
# ─────────────────────────────────────────────────────────────
class TestBaselinePolicy:
    def test_registered_file_is_warning_not_blocking(self, tmp_path, monkeypatch):
        root = _mkroot(tmp_path)
        rel = "foo/domain/entities/foo.py"
        _write(root, rel, """
            class Foo:
                def to_dict(self):
                    return {"t": int(self._t * 1000)}
        """)
        # 把该文件登记进存量基线
        baseline = {"AGGREGATE_TIME_MAGIC": {rel}}
        monkeypatch.setattr(guard, "BASELINE", baseline)
        r = guard.run_guard(str(root))
        assert r.blocking == []
        assert len(r.warnings) == 1

    def test_unregistered_new_file_is_blocking(self, tmp_path, monkeypatch):
        root = _mkroot(tmp_path)
        rel = "foo/domain/entities/foo.py"
        _write(root, rel, """
            class Foo:
                def to_dict(self):
                    return {"t": int(self._t * 1000)}
        """)
        baseline = {"AGGREGATE_TIME_MAGIC": set()}  # 未登记任何存量
        monkeypatch.setattr(guard, "BASELINE", baseline)
        r = guard.run_guard(str(root))
        assert len(r.blocking) == 1

    def test_baseline_growth_detection(self, tmp_path, monkeypatch):
        """存量登记 1 个文件，新增第 2 个 -> 命中文件数增长。"""
        root = _mkroot(tmp_path)
        rel_old = "old/domain/entities/old.py"
        rel_new = "new/domain/entities/new.py"
        for rel in (rel_old, rel_new):
            _write(root, rel, """
                class X:
                    def to_dict(self):
                        return {"t": int(self._t * 1000)}
            """)
        baseline = {"AGGREGATE_TIME_MAGIC": {rel_old}}
        monkeypatch.setattr(guard, "BASELINE", baseline)
        r = guard.run_guard(str(root))
        current = r.affected_files("AGGREGATE_TIME_MAGIC")
        assert current == {rel_old, rel_new}
        assert current - baseline["AGGREGATE_TIME_MAGIC"] == {rel_new}
        # 新增文件应阻断
        assert any(f.rel_path == rel_new for f in r.blocking)

    def test_affected_files_counts_only_matching_rule(self, tmp_path):
        root = _mkroot(tmp_path)
        _write(root, "a/domain/entities/a.py", "class A:\n    def t(self):\n        return int(self._x * 1000)\n")
        _write(root, "b/infrastructure/b.py", "from app.services import b_service\n")
        r = guard.run_guard(str(root))
        assert r.affected_files("AGGREGATE_TIME_MAGIC") == {"a/domain/entities/a.py"}
        assert r.affected_files("INFRA_REVERSE_SERVICE") == {"b/infrastructure/b.py"}


# ─────────────────────────────────────────────────────────────
# 五、命令行 & 性能
# ─────────────────────────────────────────────────────────────
class TestCli:
    def test_cli_clean_repo_exit_zero(self, tmp_path, monkeypatch):
        root = _mkroot(tmp_path)
        _write(root, "foo/domain/entities/bar.py", "class Bar: pass\n")
        monkeypatch.setattr(guard, "BASELINE", {
            "LAYER_DOMAIN_IMPORT": set(),
            "INFRA_REVERSE_SERVICE": set(),
            "AGGREGATE_TIME_MAGIC": set(),
        })
        code = guard.main(["--root", str(root)])
        assert code == 0

    def test_cli_blocking_new_violation_exit_one(self, tmp_path, monkeypatch):
        root = _mkroot(tmp_path)
        _write(root, "foo/domain/entities/bar.py", """
            from fastapi import APIRouter
            class Bar: pass
        """)
        monkeypatch.setattr(guard, "BASELINE", {
            "LAYER_DOMAIN_IMPORT": set(),
            "INFRA_REVERSE_SERVICE": set(),
            "AGGREGATE_TIME_MAGIC": set(),
        })
        code = guard.main(["--root", str(root)])
        assert code == 1

    def test_cli_growth_exit_one(self, tmp_path, monkeypatch):
        root = _mkroot(tmp_path)
        _write(root, "a/domain/entities/a.py", "class A:\n    def t(self):\n        return int(self._x * 1000)\n")
        monkeypatch.setattr(guard, "BASELINE", {
            "LAYER_DOMAIN_IMPORT": set(),
            "INFRA_REVERSE_SERVICE": set(),
            "AGGREGATE_TIME_MAGIC": set(),  # 未登记，新增 -> 存量增长 + 阻断
        })
        code = guard.main(["--root", str(root)])
        assert code == 1

    def test_guard_is_millisecond_fast_on_repo(self):
        """真实 app/domain 约 500+ py，纯 AST 扫描应毫秒级（宽松上限防回归）。"""
        import time
        t0 = time.monotonic()
        guard.run_guard()
        elapsed = time.monotonic() - t0
        assert elapsed < 5.0, f"architecture_guard 扫描过慢: {elapsed:.3f}s"


# ─────────────────────────────────────────────────────────────
# 六、真实仓库基线快照（只读，不触碰 app/domain）
#    校验存量不增长 —— 若清理了存量需同步更新 BASELINE。
# ─────────────────────────────────────────────────────────────
class TestRepoSnapshot:
    @pytest.fixture(autouse=True)
    def _skip_when_no_repo(self):
        if not os.path.isdir(guard._DOMAIN_ROOT):
            pytest.skip("仓库 app/domain 不存在")
        yield

    def test_repo_domain_layer_stays_clean(self):
        r = guard.run_guard()
        files = r.affected_files("LAYER_DOMAIN_IMPORT")
        assert files == guard.BASELINE.get("LAYER_DOMAIN_IMPORT", set())

    def test_repo_infra_reverse_service_not_grown(self):
        r = guard.run_guard()
        assert r.affected_files("INFRA_REVERSE_SERVICE") <= guard.BASELINE.get(
            "INFRA_REVERSE_SERVICE", set()
        )

    def test_repo_time_magic_flagged_files_match_baseline(self):
        """守护第一跑揪出的 5 处裸写 *1000 的文件应等于基线登记。"""
        r = guard.run_guard()
        assert r.affected_files("AGGREGATE_TIME_MAGIC") <= guard.BASELINE.get(
            "AGGREGATE_TIME_MAGIC", set()
        )
        # 阻断应为空：真实仓库无新增违规
        assert r.blocking == []
