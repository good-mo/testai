"""tasks 表 Repository 下沉对齐测试（TaskRepo / TaskStore 门面）。

目的：tasks 表建表 / CRUD / 跨进程认领 / 重启恢复 SQL 已从
app/tasks/manager.py 下沉至 app/repositories/task_repo.py。本测试锁定
repo 的数据访问语义与 TaskStore 门面委托行为，保证下沉前后零回归。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.repositories import task_repo  # noqa: E402
from app.tasks.manager import FAILED, PENDING, RUNNING, SUCCESS, TaskStore  # noqa: E402


def _clean():
    conn = task_repo._get_conn()
    conn.execute("DELETE FROM tasks")
    conn.commit()


def test_task_repo_ddl_alignment():
    """repo DDL 与 schema_registry 引用一致，表结构含全部列。"""
    _clean()
    conn = task_repo._get_conn()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    for col in ("task_id", "status", "created_at", "started_at", "finished_at",
                "result", "error", "coro_name", "args",
                "handler_name", "handler_args", "handler_kwargs",
                "restartable", "claimed_by"):
        assert col in cols, f"列 {col} 应存在"


def test_task_repo_crud_via_store_facade():
    """TaskStore 门面委托 repo，CRUD 往返一致。"""
    _clean()
    store = TaskStore()
    tid = "repo-test-%d" % int(time.time())

    # save via store
    store.save_task(tid, "some_coro", [1, 2, 3], restartable=True)
    rec = task_repo.get_task(tid)
    assert rec is not None
    assert rec["task_id"] == tid
    assert rec["status"] == PENDING
    assert rec["restartable"] == 1

    # get via store
    rec2 = store.get_task(tid)
    assert rec2["task_id"] == tid

    # update via store
    store.update_status(tid, SUCCESS, result={"ok": True}, finished_at=time.time())
    rec3 = task_repo.get_task(tid)
    assert rec3["status"] == SUCCESS
    assert rec3["result"] == {"ok": True}  # json 自动反序列化

    # delete via store
    assert store.delete_task(tid) is True
    assert task_repo.get_task(tid) is None

    # direct repo delete
    task_repo.save_task("direct-del", status=RUNNING, coro_name="c")
    assert task_repo.delete_task("direct-del") is True


def test_task_repo_claim_and_release():
    """原子认领与释放。"""
    _clean()
    task_repo.save_task("claim-1", status=PENDING, restartable=True)
    task_repo.save_task("claim-2", status=PENDING, restartable=True)

    # claim one
    claimed = task_repo.claim_next_pending(worker_id="w1")
    assert claimed is not None
    assert claimed["claimed_by"] == "w1"
    assert claimed["status"] == PENDING

    # release claim then it can be claimed again
    task_repo.release_claim(claimed["task_id"])
    claimed2 = task_repo.claim_next_pending(worker_id="w2")
    assert claimed2 is not None

    # cleanup
    task_repo.delete_task("claim-1")
    task_repo.delete_task("claim-2")


def test_task_repo_recover_after_restart():
    """重启恢复：restartable 保留 pending，running 标记 failed。"""
    _clean()
    # restartable pending task
    task_repo.save_task("rec-keep", status=PENDING, restartable=True,
                        handler_name="handler.x")
    # non-restartable pending task
    task_repo.save_task("rec-orphan", status=PENDING, restartable=False)
    # running task
    task_repo.save_task("rec-running", status=RUNNING, restartable=True)

    keep, abandoned = task_repo.recover_after_restart()
    assert len(keep) == 1 and keep[0]["task_id"] == "rec-keep"
    assert len(abandoned) == 2

    # DB 状态已更新：running → failed，非 restartable pending → failed
    db_running = task_repo.get_task("rec-running")
    assert db_running["status"] == FAILED
    db_orphan = task_repo.get_task("rec-orphan")
    assert db_orphan["status"] == FAILED

    # restartable pending 保持 pending，等待认领
    db_keep = task_repo.get_task("rec-keep")
    assert db_keep["status"] == PENDING

    # cleanup
    task_repo.delete_task("rec-keep")
    task_repo.delete_task("rec-orphan")
    task_repo.delete_task("rec-running")


def test_task_store_facade_matches_repo():
    """TaskStore 门面与 TaskRepo 直接调用结果一致。"""
    _clean()
    store = TaskStore()
    tid = "facade-test-%d" % int(time.time())
    store.save_task(tid, "coro", [], restartable=False)
    assert store.get_task(tid) is not None
    store.delete_task(tid)
    assert store.get_task(tid) is None
