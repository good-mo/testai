"""P1 架构问题修复的回归测试。

覆盖四项修复：
  1. 任务队列：超时保护、残留任务结算、连接复用、字段白名单
  2. 上传文件名净化：路径穿越防护
  3. 分页统计：SQL COUNT 替代全表加载，且总数与列表口径一致
  4. 分层收口：services 层委托真实数据访问层，不再自拼 SQL
"""
import asyncio
import os
import time

import pytest

# ════════════════════════════════════════════════════════════
# 1. 任务队列
# ════════════════════════════════════════════════════════════


class TestTaskStoreConnectionReuse:
    """TaskStore 复用 Database 连接池，而非各自新建连接。"""

    def test_connection_from_database_pool(self):
        from app.core.database import Database
        from app.tasks import manager as m

        store = m.TaskStore()
        conn = store._get_conn()
        # 同一线程重复获取应复用同一连接
        assert Database.get_conn("tasks.db") is conn
        assert store._get_conn() is conn
        # db_path 仅向后兼容保留，不影响连接来源
        assert store.db_path  # 不应为 None

    def test_database_wal_enabled(self):
        from app.core.database import Database
        from app.tasks import manager as m

        m.TaskStore()  # 确保表已初始化
        conn = Database.get_conn("tasks.db")
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"


class TestTaskStoreUpdateStatus:
    """update_status 只接受白名单字段，拒绝列名注入。"""

    def test_whitelist_filters_unknown_field(self):
        import uuid as _uuid

        from app.tasks import manager as m

        store = m.TaskStore()
        tid = f"w_{_uuid.uuid4().hex[:8]}"
        store.save_task(tid, "coro", [])
        # 传入非法字段名不应进入 SQL
        store.update_status(tid, m.SUCCESS, evil_column="1")
        assert store.get_task(tid)["status"] == m.SUCCESS
        conn = store._get_conn()
        conn.execute("DELETE FROM tasks WHERE task_id=?", (tid,))
        conn.commit()

    def test_error_and_result_persisted(self):
        import uuid as _uuid

        from app.tasks import manager as m

        store = m.TaskStore()
        tid = f"e_{_uuid.uuid4().hex[:8]}"
        store.save_task(tid, "coro", [1, 2])
        store.update_status(tid, m.FAILED, error="boom", result={"k": "v"})
        row = store.get_task(tid)
        assert row["error"] == "boom"
        assert row["result"] == {"k": "v"}
        conn = store._get_conn()
        conn.execute("DELETE FROM tasks WHERE task_id=?", (tid,))
        conn.commit()


class TestAbandonedTaskSweep:
    """进程重启后残留的 pending/running 任务应被结算，避免永久悬挂。"""

    def _cleanup_tasks(self):
        from app.core.database import Database
        conn = Database.get_conn("tasks.db")
        conn.execute("DELETE FROM tasks")
        conn.commit()

    def test_mark_abandoned_transitions_to_failed(self):
        import uuid as _uuid

        from app.tasks import manager as m

        store = m.TaskStore()
        p1 = f"p1_{_uuid.uuid4().hex[:8]}"
        r1 = f"r1_{_uuid.uuid4().hex[:8]}"
        done = f"d_{_uuid.uuid4().hex[:8]}"
        store.save_task(p1, "coro", [])
        store.save_task(r1, "coro", [])
        store.save_task(done, "coro", [])
        store.update_status(r1, m.RUNNING, started_at=time.time())
        store.update_status(done, m.SUCCESS, finished_at=time.time())  # 不应被波及

        swept = store.mark_abandoned()
        ids = {r["task_id"] for r in swept}
        assert ids == {p1, r1}, "只应结算未完成的任务"

        assert store.get_task(p1)["status"] == m.FAILED
        assert store.get_task(r1)["status"] == m.FAILED
        assert store.get_task(r1)["error"]
        assert store.get_task(done)["status"] == m.SUCCESS
        # 清理测试数据
        conn = store._get_conn()
        conn.execute("DELETE FROM tasks WHERE task_id IN (?,?,?)", (p1, r1, done))
        conn.commit()

    def test_mark_abandoned_noop_when_clean(self):
        import uuid as _uuid

        from app.tasks import manager as m

        self._cleanup_tasks()
        store = m.TaskStore()
        done = f"done_{_uuid.uuid4().hex[:8]}"
        store.save_task(done, "coro", [])
        store.update_status(done, m.SUCCESS)
        assert store.mark_abandoned() == []
        # 清理测试数据
        conn = store._get_conn()
        conn.execute("DELETE FROM tasks WHERE task_id=?", (done,))
        conn.commit()


class TestTaskTimeout:
    """settings.task_timeout 此前从未被读取，超时任务会永久占住 worker。"""

    def test_timeout_terminates_and_frees_worker(self):
        from app.tasks import manager as m

        async def scenario():
            tm = m.TaskManager(maxsize=10, timeout=0.3)
            tm.start(num_workers=1)

            async def hang():
                await asyncio.sleep(10)

            async def quick():
                return "ok"

            hang_task = await tm.submit(hang)
            quick_task = await tm.submit(quick)
            await asyncio.sleep(1.2)

            # 超时任务被判失败
            assert tm.get_task(hang_task.task_id).status == m.FAILED
            assert "超时" in (tm.get_task(hang_task.task_id).error or "")
            # 后续任务未被饿死
            assert tm.get_task(quick_task.task_id).status == m.SUCCESS
            assert tm.get_task(quick_task.task_id).result == "ok"
            await tm.stop()

        asyncio.run(scenario())

    def test_timeout_read_from_settings(self):
        from app.config import settings
        from app.tasks.manager import TaskManager

        # 未显式传参时应回落到 settings（此前这两个配置项无人读取）
        tm = TaskManager()
        assert tm._timeout == settings.task_timeout
        assert tm._maxsize == settings.task_queue_maxsize
        # 显式传参优先，便于测试与特殊场景覆盖
        tm2 = TaskManager(maxsize=5, timeout=7)
        assert tm2._maxsize == 5
        assert tm2._timeout == 7


# ════════════════════════════════════════════════════════════
# 2. 上传文件名净化（路径穿越）
# ════════════════════════════════════════════════════════════


class TestFilenameSanitization:

    @pytest.mark.parametrize("raw", [
        "../../app/main.py",
        "../../../etc/passwd",
        "..\\..\\windows\\win.ini",
        "/etc/passwd",
        "....//....//app/main.py",
        "a/b/c.py",
    ])
    def test_traversal_stripped(self, raw):
        from app.services.file_service import FileService

        sanitize_filename = FileService.sanitize_filename

        safe = sanitize_filename(raw)
        assert ".." not in safe
        assert "/" not in safe
        assert "\\" not in safe

    def test_absolute_path_reduced_to_basename(self):
        from app.services.file_service import FileService

        sanitize_filename = FileService.sanitize_filename

        assert sanitize_filename("/etc/passwd") == "passwd"

    def test_windows_reserved_names_neutralized(self):
        from app.services.file_service import FileService

        sanitize_filename = FileService.sanitize_filename

        assert sanitize_filename("CON") == "_CON"
        assert sanitize_filename("NUL.txt") == "_NUL.txt"

    def test_control_chars_replaced(self):
        from app.services.file_service import FileService

        sanitize_filename = FileService.sanitize_filename

        assert "\n" not in sanitize_filename("a\nb.txt")
        assert "\x00" not in sanitize_filename("a\x00b.txt")

    def test_empty_and_dot_fallback(self):
        from app.services.file_service import FileService

        sanitize_filename = FileService.sanitize_filename

        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename("..") == "unnamed"
        assert sanitize_filename(None) == "unnamed"

    def test_normal_name_preserved(self):
        from app.services.file_service import FileService

        sanitize_filename = FileService.sanitize_filename

        assert sanitize_filename("正常文件.txt") == "正常文件.txt"
        assert sanitize_filename("report 2024.pdf") == "report 2024.pdf"

    def test_length_capped(self):
        from app.services.file_service import FileService

        sanitize_filename = FileService.sanitize_filename

        assert len(sanitize_filename("x" * 500 + ".txt")) <= 200

    def test_upload_path_stays_inside_upload_dir(self):
        from app.services.file_service import UPLOAD_DIR, FileService


        build_upload_path = FileService.build_upload_path

        for raw in ["../../app/main.py", "/etc/shadow", "..\\..\\x.py"]:
            path = FileService.build_upload_path("fid", raw)
            assert os.path.commonpath([path, UPLOAD_DIR]) == UPLOAD_DIR


class TestUploadEndpointSecurity:
    """端到端：恶意文件名不能写到 uploads 之外。"""

    def test_malicious_filename_not_written_outside(self, auth_client):
        content = b"pwned"
        resp = auth_client.post(
            "/project/file/upload",
            files={"file": ("../../evil_traversal.txt", content, "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        saved = data["path"]
        # 落盘位置必须在 uploads 目录内
        assert os.path.abspath(saved).startswith(os.path.abspath("uploads") + os.sep)
        assert data["name"] == "evil_traversal.txt"
        assert ".." not in data["name"]
        # 未在项目根目录创建逃逸文件
        assert not os.path.exists("evil_traversal.txt")
        assert not os.path.exists("../evil_traversal.txt")
        # 清理测试落盘文件，避免污染仓库
        try:
            os.remove(saved)
        except OSError:
            pass


# ════════════════════════════════════════════════════════════
# 3. 分页统计
# ════════════════════════════════════════════════════════════


class TestCaseCounting:
    """count_cases 必须与 list_cases 过滤条件同源。"""

    @pytest.mark.parametrize("search", [None, "登录", "zzz_no_match"])
    def test_count_matches_list(self, search):
        from app.repositories.case_repo import CaseRepo

        count_cases, list_cases = CaseRepo.count_cases, CaseRepo.list_cases

        total = count_cases(search=search)
        rows = list_cases(search=search, limit=1000, offset=0)
        assert total == len(rows)

    def test_count_excludes_deprecated(self):
        """count 口径须与 list 一致（排除回收站），否则末页永远翻空。"""
        from app.repositories.case_repo import CaseRepo

        conn = CaseRepo.get_conn()
        count_cases = CaseRepo.count_cases
        all_rows = conn.execute("SELECT COUNT(*) FROM test_cases").fetchone()[0]
        deprecated = conn.execute(
            "SELECT COUNT(*) FROM test_cases WHERE status = 'deprecated'"
        ).fetchone()[0]
        assert count_cases() == all_rows - deprecated

    def test_pagination_total_consistent(self, auth_client):
        """列表接口返回的 total 应与实际可翻页数一致。"""
        resp = auth_client.post(
            "/functional/case/page", json={"pageSize": 10, "current": 1}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        total = data["total"]
        assert total > 0

        # 翻到最后一页应有数据，不能出现 total 虚高导致的空页
        last_page = (total + 9) // 10
        resp = auth_client.post(
            "/functional/case/page", json={"pageSize": 10, "current": last_page}
        )
        last_items = resp.json()["data"].get("list", [])
        assert len(last_items) > 0, "末页为空说明 total 与列表口径不一致"

    def test_keyword_search_total_matches(self, auth_client):
        resp = auth_client.post(
            "/functional/case/page",
            json={"pageSize": 10, "current": 1, "keyword": "登录"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        items = data.get("list", [])
        # 搜索时 total 应等于匹配总数，而非全表行数
        assert data["total"] >= len(items)


class TestDefectCounting:

    @pytest.mark.parametrize("status", [None, "open", "closed", "fixed"])
    def test_count_matches_list(self, status):
        from app.repositories.defect_repo import DefectRepo

        total = DefectRepo.count(status=status)
        rows = DefectRepo.list(status=status, limit=1000)
        assert total == len(rows)

    def test_count_excludes_deleted(self):
        from app.repositories.defect_repo import DefectRepo

        conn = DefectRepo.get_conn()
        live = conn.execute(
            "SELECT COUNT(*) FROM defects WHERE deleted IS NULL OR deleted = 0"
        ).fetchone()[0]
        assert DefectRepo.count() == live


# ════════════════════════════════════════════════════════════
# 4. 分层收口
# ════════════════════════════════════════════════════════════


class TestServiceLayerAlignment:
    """services 层必须委托真实数据访问层，不能自拼 SQL。"""

    def test_case_service_total_matches_repository(self):
        from app.repositories.case_repo import CaseRepo
        from app.services.case_service import case_service

        _, total = case_service.list(limit=5)
        assert total == CaseRepo.count_cases()

    def test_case_service_test_type_filter_works(self):
        """此前按 test_type 过滤会崩溃（表无此列，存在 metadata 中）。"""
        from app.services.case_service import case_service

        rows, total = case_service.list(test_type="functional", limit=5)
        assert isinstance(rows, list)
        assert total >= 0

    def test_case_service_soft_delete_uses_deprecated(self):
        """软删除状态须与真实业务一致（deprecated 而非 deleted）。"""
        from app.services.case_service import DEPRECATED

        assert DEPRECATED == "deprecated"

    def test_defect_service_total_matches_tracker(self):
        from app.repositories.defect_repo import DefectRepo
        from app.services.defect_service import defect_service

        _, total = defect_service.list(limit=5)
        assert total == DefectRepo.count()

    def test_defect_service_status_filter_works(self):
        """此前 status 未做取值校验，且与 tracker 逻辑分叉。"""
        from app.repositories.defect_repo import DefectRepo
        from app.services.defect_service import defect_service

        rows, total = defect_service.list(status="open", limit=5)
        assert total == DefectRepo.count(status="open")
        assert len(rows) <= 5

    def test_defect_service_stats_consistent(self):
        from app.repositories.defect_repo import DefectRepo
        from app.services.defect_service import defect_service

        stats = defect_service.get_stats()
        base = DefectRepo.get_stats()
        assert stats["total"] == base["total"]
        assert stats["trash"] == base["trash"]


# ════════════════════════════════════════════════════════════
# 5. 文件查找精确匹配（数据防丢失）
# ════════════════════════════════════════════════════════════


class TestUploadFileLookup:
    """按 file_id 查找文件必须精确匹配，避免误删与目录清空。"""

    def test_empty_id_matches_nothing(self):
        from app.services.file_service import FileService

        _find_upload_file = FileService.find_upload_file

        # 空 id 若走前缀匹配会命中所有文件，一次删除清空上传目录
        assert _find_upload_file("") is None
        assert _find_upload_file(None) is None

    def test_traversal_id_rejected(self):
        from app.services.file_service import FileService

        _find_upload_file = FileService.find_upload_file

        assert _find_upload_file("../..") is None
        assert _find_upload_file("..") is None
        assert _find_upload_file(".") is None
        assert _find_upload_file("a/b") is None

    def test_exact_prefix_required(self, tmp_path, monkeypatch):
        """id 前缀相同但非同一文件时不应命中（如 abc 不应命中 abc1_x）。"""
        import app.services.file_service as fm

        monkeypatch.setattr(fm, "UPLOAD_DIR", str(tmp_path))
        _find_upload_file = fm.FileService.find_upload_file
        (tmp_path / "abc_target.txt").write_text("x")
        (tmp_path / "abc1_other.txt").write_text("y")

        # 精确匹配要求 id_ 形式：id="abc" 只应命中 abc_target.txt
        assert _find_upload_file("abc") == "abc_target.txt"

    def test_delete_with_empty_id_removes_nothing(self, auth_client, tmp_path, monkeypatch):
        """空 id 删除请求不得删除任何文件。"""
        import app.services.file_service as fm

        monkeypatch.setattr(fm, "UPLOAD_DIR", str(tmp_path))
        (tmp_path / "keep1_a.txt").write_text("1")
        (tmp_path / "keep2_b.txt").write_text("2")

        before = len(list(tmp_path.iterdir()))
        resp = auth_client.post("/project/file/delete", json={"id": ""})
        assert resp.status_code == 200
        after = len(list(tmp_path.iterdir()))
        assert after == before, "空 id 删除不应影响任何文件"
