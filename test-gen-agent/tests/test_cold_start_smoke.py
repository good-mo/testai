"""冷启动（空库）冒烟：删库后第一批访问不得 500「no such table」。

根因回溯（P0 真 Bug #624）：
  - schema_registry 声明 75 张表，但冷启动只建出 31 张；
  - 各 repository 的建表守卫（_ensure_*）只散落在部分方法里，
    大量公开方法（get / list_cases / update / soft_delete / stats /
    list_comments / load_all / save …）在空库上裸查 → OperationalError。
  - 测试一直跑在提交进仓库的热库上（有表），永远走不到建表分支。

修复方向：把 ensure 守卫收敛到连接获取处（_conn()/get_conn()），
本测试删库冷启动验证关键公开方法不再报「no such table」。

为不污染共享 tga.db，本测试把 DB 重定向到临时目录（隔离空库）。
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

import app.db  # noqa: E402
from app.core.database import Database  # noqa: E402

# 每个用例都在临时空库上跑，保证是真正冷启动；并记录原始 DB 根目录，
# 用例结束后必须还原，避免污染共享 tga.db / 影响同进程后续测试。
_TMP = tempfile.mkdtemp(prefix="tga_cold_")
_ORIG_ROOT = app.db.PROJECT_ROOT


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_fresh_db():
    """把 DB 指向一个全新的空临时库（isolated），确保首访无表。用例后还原。

    建表守卫用类级一次性 _schema_ensured 标记（生产单库进程下正确）。
    若本用例前同进程其它测试已访问过共享库并把标记置真，则需在此重置，
    以模拟真正冷启动的新进程。
    """
    # 重置受测仓库的一次性建表标记，模拟新进程冷启动
    from app.repositories import ai_model_repo as _ai
    from app.repositories import case_repo as _case
    from app.repositories import debug_repo as _debug
    from app.repositories import defect_repo as _defect
    from app.repositories import project_repo as _proj
    from app.repositories import project_version_repo as _pver
    for _repo in (_case.CaseRepo, _defect.DefectRepo, _debug.DebugRepo,
                  _ai.AiModelRepo, _proj.ProjectRepo, _pver.ProjectVersionRepo):
        _repo._schema_ensured = False

    # 清空当前线程连接池，再重置到新路径
    Database.close_all()
    app.db.PROJECT_ROOT = _TMP
    # 确保临时目录里没有残留 tga.db
    for f in ("tga.db", "tga.db-wal", "tga.db-shm"):
        p = os.path.join(_TMP, f)
        if os.path.exists(p):
            os.remove(p)
    yield
    # 还原共享库：清连接池 + 还原根目录，并把标记复位为 False，
    # 让同进程后续针对真实共享库的测试重新走一次幂等建表，避免错指临时库。
    Database.close_all()
    app.db.PROJECT_ROOT = _ORIG_ROOT
    for _repo in (_case.CaseRepo, _defect.DefectRepo, _debug.DebugRepo,
                  _ai.AiModelRepo, _proj.ProjectRepo, _pver.ProjectVersionRepo):
        _repo._schema_ensured = False


@pytest.fixture(scope="session", autouse=True)
def _cleanup_tmp():
    yield
    try:
        shutil.rmtree(_TMP)
    except Exception:
        pass


def _table_exists(db_name, table):
    conn = Database.get_conn(db_name)
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def test_case_repo_cold_start_no_missing_table():
    """CaseRepo 首批访问不再报 no such table: test_cases。"""
    from app.repositories.case_repo import CaseRepo
    # 直接落到 testcases.db（统一路由 tga.db）
    assert not _table_exists("testcases.db", "test_cases")
    # 以下任一方法都应在空库上自动建表而非抛异常
    assert CaseRepo.get("x") is None
    assert CaseRepo.list_cases() == []
    assert CaseRepo.get_stats()["total"] == 0
    assert CaseRepo.update("x", {"title": "t"}) is None
    assert CaseRepo.soft_delete("x") is None
    assert _table_exists("testcases.db", "test_cases")


def test_defect_repo_cold_start_no_missing_table():
    """DefectRepo 首批访问不再报 no such table: defects。"""
    from app.repositories.defect_repo import DefectRepo
    assert not _table_exists("defects.db", "defects")
    assert DefectRepo.get("x") is None
    assert DefectRepo.list_comments("x") == []
    assert DefectRepo.get_stats()["total"] == 0
    assert _table_exists("defects.db", "defects")
    assert _table_exists("defects.db", "defect_comments")


def test_debug_repo_cold_start_no_missing_table():
    """DebugRepo 首批访问不再报 no such table: debug_items。"""
    from app.repositories.debug_repo import DebugRepo
    assert not _table_exists("apitest.db", "debug_items")
    assert DebugRepo.load_all() == []
    DebugRepo.save({"id": "dbg-1", "name": "n", "request": {}, "response": {}})
    assert len(DebugRepo.load_all()) == 1
    DebugRepo.delete("dbg-1")
    assert DebugRepo.load_all() == []
    assert _table_exists("apitest.db", "debug_items")


def test_project_version_repo_cold_start_no_missing_table():
    """ProjectVersionRepo 无守卫方法在空库不再报 no such table。"""
    from app.repositories.project_version_repo import ProjectVersionRepo
    assert ProjectVersionRepo.update_version("x", {"name": "n"}) is None
    assert ProjectVersionRepo.get_feature_enabled("p") is False
    assert _table_exists("projects.db", "project_versions")


def test_ai_model_repo_cold_start_upsert_no_missing_table():
    """AiModelRepo upsert 冷启动路径不再报 no such table。"""
    from app.repositories.ai_model_repo import AiModelRepo
    assert AiModelRepo.upsert({"name": "model-x"}) is not None
    assert _table_exists("auth.db", "ai_model_sources")


def test_project_repo_cold_start_no_missing_table():
    """ProjectRepo 主项目表访问在空库自动建表。"""
    from app.repositories.project_repo import ProjectRepo
    assert ProjectRepo.get("x") is None
    assert ProjectRepo.list_custom_funcs() == []
    assert _table_exists("projects.db", "projects")
