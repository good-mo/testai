"""
异步任务队列管理器
====================
将耗时任务（LLM 生成 + 测试运行）从 HTTP 请求中解耦，
提交到后台异步执行，REST 接口立即返回 task_id，轮询查询进度/结果。

架构设计（v2：SQLite 作为共享队列 + 可恢复任务注册）
--------------------------------------------------------
原实现仅用 in-memory asyncio.Queue 分发任务，存在两个核心缺陷：
  1. 多 worker 进程/实例部署时，每个进程有独立的 in-memory 队列，
     任务只在一个 worker 内可见 —— 提交到进程 A 的任务进程 B 无法看到。
  2. 进程重启后 pending 任务丢失：协程对象无法跨进程序列化，
     只能统一标记为 failed。

v2 修复方案（不引入 Redis/Celery 等外部依赖）：
  - SQLite 即任务队列：任务状态机由磁盘驱动，任何 worker 进程都能
    通过 SQLite 看到并认领 pending 任务。
  - 命名处理器注册（task handler registry）：可恢复任务通过
    `submit_named(name, *serializable_args)` 提交，参数须 JSON 可序列化。
    处理器函数在模块级注册，进程重启后可凭 handler_name 从磁盘重建并执行。
  - 启动恢复策略：命名任务重启后保持 pending，等待新 worker 认领执行；
    仅对不可恢复的匿名协程任务标记 failed（协程引用已随进程丢失）。

任务状态机：pending → running → success/failed/cancelled

数据库访问统一走 Database 连接池（线程本地连接，见 app.core.database），
任务表逻辑名经 Database 统一路由到 tga.db。
"""
import asyncio
import json
import os
import time
import uuid
from typing import Any, Callable, Dict, Optional, Tuple

from app.db import PROJECT_ROOT
from app.logging_config import get_logger

logger = get_logger(__name__)

# 任务状态
PENDING = "pending"
RUNNING = "running"
SUCCESS = "success"
FAILED = "failed"
CANCELLED = "cancelled"

# 任务持久化数据库逻辑名（经 Database 统一路由到 tga.db）
_TASK_DB_NAME = "tasks.db"
# 向后兼容：旧版直接路径
_TASK_DB_PATH = os.path.join(PROJECT_ROOT, "tasks.db")

# ── 任务处理器注册表 ───────────────────────────────────────
# 注册可恢复（restartable）任务处理器。
# 键：handler 名称（字符串）；值：可调用对象（async 或 sync）。
_TASK_HANDLERS: Dict[str, Callable] = {}


def register_handler(name: str) -> Callable:
    """装饰器：将函数注册为可恢复任务处理器。

    Example:
        @register_handler("generation.run")
        async def run_generation(req_data: dict) -> dict: ...
    """
    def decorator(func: Callable) -> Callable:
        _TASK_HANDLERS[name] = func
        logger.debug("已注册任务处理器: %s", name)
        return func
    return decorator


def get_handler(name: str) -> Optional[Callable]:
    """按名称查找已注册的处理器函数。"""
    return _TASK_HANDLERS.get(name)


def list_handlers() -> list:
    """列出所有已注册的处理器名称。"""
    return sorted(_TASK_HANDLERS.keys())


class TaskStore:
    """任务持久化存储（tasks 表数据访问门面，委托 app.repositories.task_repo）。

    tasks 表建表 / CRUD / 跨进程认领 / 重启恢复 SQL 已下沉至
    app/repositories/task_repo.py，本类保留旧接口签名，内部统一委托
    TaskRepo，使 TaskManager 调用方零改动。
    """

    def __init__(self, db_path: str = None):
        # db_path 仅向后兼容保留；实际连接由 Database 统一管理
        self.db_path = db_path or _TASK_DB_PATH
        from app.repositories import task_repo
        self._repo = task_repo

    def _init_db(self) -> None:
        """初始化任务表（委托 task_repo.ensure_table）。"""
        self._repo.ensure_table()

    @staticmethod
    def _get_conn():
        """获取 Database 连接（兼容旧接口，直接委托 repo）。"""
        from app.repositories.task_repo import _get_conn as _repo_conn
        return _repo_conn()

    @staticmethod
    def _decode(row):
        """DB 行解码（兼容旧接口，委托 repo）。"""
        from app.repositories.task_repo import _decode as _repo_decode
        return _repo_decode(row)

    def save_task(
        self,
        task_id: str,
        coro_name: str = "",
        args: list = None,
        handler_name: str = "",
        handler_args: list = None,
        handler_kwargs: dict = None,
        restartable: bool = False,
    ) -> None:
        """保存任务到磁盘（委托 repo）。"""
        self._repo.save_task(
            task_id, status=PENDING, coro_name=coro_name,
            args=args, handler_name=handler_name,
            handler_args=handler_args, handler_kwargs=handler_kwargs,
            restartable=restartable,
        )

    def update_status(self, task_id: str, status: str, **kwargs) -> None:
        """更新任务状态（委托 repo）。"""
        self._repo.update_status(task_id, status, **kwargs)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """从磁盘读取任务（委托 repo）。"""
        return self._repo.get_task(task_id)

    def list_recent(self, limit: int = 50) -> list:
        """获取最近任务列表（委托 repo）。"""
        return self._repo.list_recent(limit=limit)

    def list_pending(self) -> list:
        """返回所有 pending 状态任务（委托 repo）。"""
        return self._repo.list_pending()

    def delete_task(self, task_id: str) -> bool:
        """物理删除任务记录（委托 repo）。"""
        return self._repo.delete_task(task_id)

    def claim_next_pending(self, worker_id: str = "") -> Optional[Dict[str, Any]]:
        """原子认领 pending 任务（委托 repo）。"""
        return self._repo.claim_next_pending(worker_id=worker_id)

    def release_claim(self, task_id: str) -> None:
        """释放任务认领（委托 repo）。"""
        self._repo.release_claim(task_id)

    def recover_after_restart(self) -> Tuple[list, list]:
        """重启后任务恢复（委托 repo）。"""
        return self._repo.recover_after_restart()

    def recover_pending(self) -> list:
        """[deprecated] 返回未完成任务（委托 repo）。"""
        return self._repo.recover_pending()

    def mark_abandoned(self, reason: str = "进程重启，任务未完成") -> list:
        """[deprecated] 标记不可恢复任务（委托 repo）。"""
        return self._repo.mark_abandoned()

    def close(self) -> None:
        """兼容接口：连接由 Database 统一管理，无需手动关闭。"""
        pass


class Task:
    """单个后台任务（内存态 + 可持久化元数据）。

    两种构造方式：
      - from_coro():  提交匿名协程（不可恢复，仅本进程可执行）
      - from_handler(): 提交命名处理器（可恢复，跨进程）
    """

    @classmethod
    def from_coro(cls, task_id: str, coro: Callable, args: tuple = (),
                  kwargs: dict = None) -> "Task":
        """创建匿名协程任务（旧版 submit 兼容路径）。"""
        t = cls(task_id)
        t._coro = coro
        t._args = tuple(args)
        t._kwargs = dict(kwargs or {})
        t.restartable = False
        return t

    @classmethod
    def from_handler(cls, task_id: str, handler_name: str,
                     handler_args: tuple = (), handler_kwargs: dict = None) -> "Task":
        """创建命名处理器任务（可恢复）。"""
        t = cls(task_id)
        t.handler_name = handler_name
        t.handler_args = tuple(handler_args)
        t.handler_kwargs = dict(handler_kwargs or {})
        t.restartable = bool(get_handler(handler_name))
        return t

    def __init__(self, task_id: str):
        self.task_id = task_id
        self._coro: Optional[Callable] = None       # 匿名协程引用（内存态）
        self._args: tuple = ()
        self._kwargs: dict = {}
        self.handler_name: str = ""                 # 命名处理器名称
        self.handler_args: tuple = ()
        self.handler_kwargs: dict = {}
        self.restartable: bool = False
        self.status = PENDING
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.finished_at: Optional[float] = None
        self.result: Any = None
        self.error: Optional[str] = None
        self.traceback: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "result": self.result,
            "error": self.error,
            "duration": (
                (self.finished_at - self.created_at)
                if self.finished_at else None
            ),
            "handler_name": self.handler_name,
            "restartable": self.restartable,
        }

    async def _execute(self, timeout: float) -> Tuple[Any, Optional[str], Optional[str]]:
        """执行任务。

        Returns:
            (result, error, error_type):
            - error_type == "TimeoutError": 超时
            - error_type == "CancelledError": 被取消
            - error_type == "HandlerError": 常规异常
            - error_type == None: 成功
        """
        try:
            if self._coro is not None:
                # 旧版兼容路径：直接执行传入的 coroutine
                result = await asyncio.wait_for(
                    self._coro(*self._args, **self._kwargs),
                    timeout=timeout,
                )
            elif self.handler_name:
                # 命名处理器路径：从 registry 查找并执行
                handler = get_handler(self.handler_name)
                if handler is None:
                    return None, f"处理器未注册: {self.handler_name}", "HandlerError"
                ret = handler(*self.handler_args, **self.handler_kwargs)
                if asyncio.iscoroutine(ret) or asyncio.isfuture(ret):
                    result = await asyncio.wait_for(ret, timeout=timeout)
                else:
                    result = ret
            else:
                return None, "任务既无协程引用也未注册处理器", "HandlerError"
            return result, None, None
        except asyncio.TimeoutError:
            return None, f"任务超时（>{timeout}s）已被终止", "TimeoutError"
        except asyncio.CancelledError:
            return None, "任务被取消", "CancelledError"
        except Exception as e:
            return None, str(e), e.__class__.__name__


class TaskManager:
    """异步任务队列。

    v2 设计：SQLite 即跨进程共享任务队列。
      - submit():      提交匿名协程任务（in-process，仅本进程可执行，不可恢复）。
      - submit_named(): 提交命名处理器任务（可恢复，任意进程均可认领执行）。
      - worker 循环：从本地 asyncio.Queue（快速路径）+ SQLite（跨进程）
        两个来源获取任务并执行。
    """

    def __init__(self, maxsize: int = None, timeout: float = None):
        if maxsize is None or timeout is None:
            from app.config import settings as _settings
            if maxsize is None:
                maxsize = _settings.task_queue_maxsize
            if timeout is None:
                timeout = _settings.task_timeout
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._tasks: Dict[str, Task] = {}
        self._workers: list = []
        self._running: Dict[str, asyncio.Task] = {}  # task_id -> 正在执行该任务的 asyncio.Task（供停止取消）
        self._maxsize = maxsize
        self._timeout = timeout
        self._store = TaskStore()

    def start(self, num_workers: int = 2) -> None:
        """启动后台 worker，并恢复上次进程残留的未完成任务。"""
        try:
            restartable, abandoned = self._store.recover_after_restart()
            if restartable:
                logger.info(
                    "启动恢复：%d 个可恢复任务已重新入队",
                    len(restartable),
                )
                for rec in restartable:
                    t = self._task_from_record(rec)
                    if t:
                        self._tasks[t.task_id] = t
                        self._queue.put_nowait(t)
            if abandoned:
                logger.warning(
                    "启动清理：%d 个不可恢复的未完成任务已标记为失败",
                    len(abandoned),
                )
        except Exception as e:
            logger.warning("启动任务恢复失败: %s", e)
        for i in range(num_workers):
            w = asyncio.create_task(self._worker_loop(i))
            self._workers.append(w)
        logger.info(
            "任务队列已启动 [workers=%d, maxsize=%d, timeout=%ss]",
            num_workers, self._maxsize, self._timeout,
        )

    async def stop(self) -> None:
        """停止所有 worker。"""
        for w in self._workers:
            w.cancel()
        for w in self._workers:
            try:
                await w
            except asyncio.CancelledError:
                pass
        self._workers.clear()
        self._store.close()
        logger.info("任务队列已停止")

    # ── Task 构造与记录恢复 ─────────────────────────────────

    def _task_from_record(self, rec: Dict[str, Any]) -> Optional[Task]:
        """从磁盘记录构造 Task（仅用于 restartable 任务）。"""
        task_id = rec.get("task_id", "")
        handler_name = rec.get("handler_name", "") or ""
        if not handler_name:
            return None
        handler = get_handler(handler_name)
        if handler is None:
            logger.warning("恢复任务 %s 失败：处理器 %s 未注册", task_id, handler_name)
            return None
        try:
            handler_args = json.loads(rec.get("handler_args") or "[]")
        except (ValueError, TypeError):
            handler_args = []
        try:
            handler_kwargs = json.loads(rec.get("handler_kwargs") or "{}")
        except (ValueError, TypeError):
            handler_kwargs = {}
        t = Task.from_handler(
            task_id=task_id,
            handler_name=handler_name,
            handler_args=tuple(handler_args),
            handler_kwargs=handler_kwargs,
        )
        t.created_at = rec.get("created_at", time.time())
        t.status = PENDING
        return t

    # ── Worker 循环 ─────────────────────────────────────────

    async def _worker_loop(self, idx: int) -> None:
        """Worker 主循环：本地队列 + SQLite 跨进程认领。"""
        logger.debug("worker-%d 启动", idx)
        while True:
            task: Optional[Task] = None

            # 1) 优先从本地 asyncio.Queue 取（快速路径，零等待）
            try:
                task = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                task = None

            # 2) 本地队列空时，从 SQLite 原子认领跨进程 pending 任务
            if task is None:
                claimed = self._claim_from_db(idx)
                if claimed:
                    task = claimed
                else:
                    await asyncio.sleep(0.1)  # 无任务时短暂休眠
                    continue

            # 将任务放入独立子协程执行，以便按 task_id 单独取消（停止）。
            runner = asyncio.create_task(self._run_task(task, idx))
            self._running[task.task_id] = runner
            try:
                await runner
            except asyncio.CancelledError:
                pass  # 子任务被取消（停止）时正常收尾，状态已在 _run_task 持久化
            finally:
                self._running.pop(task.task_id, None)
                try:
                    self._queue.task_done()
                except ValueError:
                    pass  # DB 认领的任务未入 queue，task_done() 会抛 ValueError

    def _claim_from_db(self, worker_idx: int) -> Optional[Task]:
        """从 SQLite 原子认领一个 pending 的 restartable 任务。"""
        try:
            rec = self._store.claim_next_pending(worker_id=f"worker-{worker_idx}")
            if not rec:
                return None
            t = self._task_from_record(rec)
            if t is None:
                self._store.release_claim(rec.get("task_id", ""))
                return None
            self._tasks[t.task_id] = t
            logger.info("worker-%d 从 SQLite 认领任务 %s", worker_idx, t.task_id)
            return t
        except Exception as e:
            logger.warning("worker-%d SQLite 认领任务失败: %s", worker_idx, e)
            return None

    async def _run_task(self, task: Task, worker_idx: int) -> None:
        """执行单个任务并更新持久化状态。"""
        # 任务在排队期间已被停止（stop_task 置为 CANCELLED）：跳过执行。
        if task.status == CANCELLED:
            task.finished_at = time.time()
            task.error = task.error or "任务已被停止"
            try:
                self._store.update_status(
                    task.task_id, CANCELLED,
                    finished_at=task.finished_at, error=task.error,
                )
            except Exception:
                pass
            return
        task.status = RUNNING
        task.started_at = time.time()
        try:
            self._store.update_status(
                task.task_id, RUNNING, started_at=task.started_at
            )
        except Exception:
            pass  # 持久化失败不阻断执行

        result, error, error_type = await task._execute(self._timeout)
        task.finished_at = time.time()

        if error is None:
            task.result = result
            task.status = SUCCESS
            try:
                self._store.update_status(
                    task.task_id, SUCCESS,
                    finished_at=task.finished_at, result=result,
                )
            except Exception:
                pass
            logger.info("任务完成 [task=%s]", task.task_id)
        elif error_type == "TimeoutError":
            task.status = FAILED
            task.error = error
            try:
                self._store.update_status(
                    task.task_id, FAILED,
                    finished_at=task.finished_at, error=error,
                )
            except Exception:
                pass
            logger.error("任务超时 [task=%s, timeout=%ss]",
                         task.task_id, self._timeout)
        elif error_type == "CancelledError":
            task.status = CANCELLED
            task.error = error
            try:
                self._store.update_status(
                    task.task_id, CANCELLED,
                    finished_at=task.finished_at, error=error,
                )
            except Exception:
                pass
        else:
            task.status = FAILED
            task.error = error
            try:
                self._store.update_status(
                    task.task_id, FAILED,
                    finished_at=task.finished_at, error=error,
                )
            except Exception:
                pass
            logger.error(
                "任务执行失败 [task=%s, err=%s]", task.task_id, error, exc_info=True
            )

    # ── 任务提交 API ────────────────────────────────────────

    async def submit(self, coro: Callable, *args, **kwargs) -> Task:
        """提交匿名协程任务（in-process，不可恢复）。

        ⚠️ 协程对象无法跨进程序列化。如需可恢复任务，
        请改用 submit_named(name, *serializable_args)。
        """
        task_id = uuid.uuid4().hex[:12]
        task = Task.from_coro(task_id, coro, args=args, kwargs=kwargs)
        task.restartable = False
        self._tasks[task_id] = task
        self._store.save_task(
            task_id,
            coro_name=getattr(coro, "__name__", coro.__class__.__name__),
            args=list(args),
            restartable=False,
        )
        await self._queue.put(task)
        logger.info("任务已提交 [task=%s]", task_id)
        return task

    async def submit_named(self, name: str, *args, **kwargs) -> Task:
        """提交命名处理器任务（可恢复，支持跨进程）。

        Args:
            name: 已在 register_handler 注册的处理器名称。
            *args/**kwargs: 传给处理器的参数（须 JSON 可序列化）。
        """
        handler = get_handler(name)
        if handler is None:
            raise ValueError(f"未注册的任务处理器: {name}")
        task_id = uuid.uuid4().hex[:12]
        task = Task.from_handler(task_id, name, args, kwargs)
        self._tasks[task_id] = task
        self._store.save_task(
            task_id,
            coro_name=name,
            args=list(args),
            handler_name=name,
            handler_args=list(args),
            handler_kwargs=dict(kwargs),
            restartable=True,
        )
        await self._queue.put(task)
        logger.info("命名任务已提交 [task=%s, handler=%s]", task_id, name)
        return task

    # ── 任务查询 ───────────────────────────────────────────

    def get_task(self, task_id: str) -> Optional[Task]:
        """查询任务（先查内存，再查磁盘）。"""
        task = self._tasks.get(task_id)
        if task:
            return task
        stored = self._store.get_task(task_id)
        if stored:
            t = Task(task_id)
            t.status = stored.get("status", PENDING)
            t.created_at = stored.get("created_at", 0)
            t.started_at = stored.get("started_at")
            t.finished_at = stored.get("finished_at")
            t.result = stored.get("result")
            t.error = stored.get("error")
            t.handler_name = stored.get("handler_name", "")
            t.restartable = bool(stored.get("restartable"))
            return t
        return None

    def get_task_dict(self, task_id: str) -> Optional[Dict[str, Any]]:
        """查询任务（返回 dict）。"""
        t = self.get_task(task_id)
        return t.to_dict() if t else None

    def list_tasks(self, limit: int = 50) -> list:
        """按创建时间倒序返回最近的任务（摘要）。"""
        items = sorted(
            self._tasks.values(), key=lambda t: t.created_at, reverse=True
        )
        result = [t.to_dict() for t in items[:limit]]
        if len(result) < limit:
            stored = self._store.list_recent(limit)
            known_ids = {t["task_id"] for t in result}
            for s in stored:
                if s["task_id"] not in known_ids:
                    result.append(s)
                    known_ids.add(s["task_id"])
                    if len(result) >= limit:
                        break
        return result[:limit]


    # ── 任务操作（停止 / 删除 / 重跑）─────────────────────────

    def stop_task(self, task_id: str) -> Tuple[bool, str]:
        """停止（取消）一个任务。

        对排队中（pending）的任务：置为 CANCELLED，worker 出队时跳过执行；
        对运行中（running）的任务：取消正在执行该任务的子协程并持久化 CANCELLED。
        已结束任务不可停止。
        """
        if not task_id:
            return False, "缺少任务 ID"
        t = self.get_task(task_id)
        if t is None:
            return False, "任务不存在"
        if t.status in (SUCCESS, FAILED, CANCELLED):
            return False, "任务已结束，无法停止"
        t.status = CANCELLED
        t.error = "任务已被用户停止"
        t.finished_at = time.time()
        try:
            self._store.update_status(
                task_id, CANCELLED,
                finished_at=t.finished_at, error=t.error,
            )
        except Exception as e:
            logger.warning("停止任务持久化失败 %s: %s", task_id, e)
        # 正在执行中的任务：取消其子协程（_run_task 捕获后持久化 CANCELLED）
        runner = self._running.get(task_id)
        if runner is not None and not runner.done():
            try:
                runner.cancel()
            except Exception as e:
                logger.warning("取消运行中任务协程失败 %s: %s", task_id, e)
        return True, "任务已停止"

    def delete_task(self, task_id: str) -> Tuple[bool, str]:
        """删除一个任务（从内存与磁盘移除）。"""
        if not task_id:
            return False, "缺少任务 ID"
        # 若正在运行，先取消再删除，避免删除后仍有执行进程
        runner = self._running.get(task_id)
        if runner is not None and not runner.done():
            try:
                runner.cancel()
            except Exception:
                pass
        removed_mem = self._tasks.pop(task_id, None) is not None
        removed_db = self._store.delete_task(task_id)
        if not removed_mem and not removed_db:
            return False, "任务不存在"
        logger.info("任务已删除 [task=%s]", task_id)
        return True, "任务已删除"

    def rerun_task(self, task_id: str) -> Tuple[bool, str]:
        """重跑一个任务。

        仅支持基于已注册命名处理器（restartable）提交的任务：
        以原 handler + 参数重新入队一个新 pending 任务。
        """
        if not task_id:
            return False, "缺少任务 ID"
        stored = self._store.get_task(task_id)
        if stored is None:
            return False, "任务不存在"
        handler_name = stored.get("handler_name") or ""
        if not handler_name:
            return False, "该任务不可重跑（非命名处理器任务）"
        if get_handler(handler_name) is None:
            return False, f"任务处理器未注册: {handler_name}"
        try:
            handler_args = json.loads(stored.get("handler_args") or "[]")
        except (ValueError, TypeError):
            handler_args = []
        try:
            handler_kwargs = json.loads(stored.get("handler_kwargs") or "{}")
        except (ValueError, TypeError):
            handler_kwargs = {}
        new_task_id = uuid.uuid4().hex[:12]
        task = Task.from_handler(
            task_id=new_task_id,
            handler_name=handler_name,
            handler_args=tuple(handler_args),
            handler_kwargs=handler_kwargs,
        )
        self._tasks[new_task_id] = task
        self._store.save_task(
            new_task_id,
            coro_name=handler_name,
            args=list(handler_args),
            handler_name=handler_name,
            handler_args=list(handler_args),
            handler_kwargs=dict(handler_kwargs),
            restartable=True,
        )
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._queue.put(task))
            else:
                self._queue.put_nowait(task)
        except RuntimeError:
            self._queue.put_nowait(task)
        logger.info("任务已重跑 [old=%s, new=%s, handler=%s]",
                    task_id, new_task_id, handler_name)
        return True, new_task_id


# ── 模块级应用上下文 ────────────────────────────────────────
# 由 main.py lifespan 启动时注入，供可恢复任务处理器在后台获取
# 与主流程一致的 graph 等应用级依赖。
_APP_CONTEXT: Dict[str, Any] = {}


def set_app_context(key: str, value: Any) -> None:
    """设置全局应用上下文（如 graph、checkpointer 等）。"""
    _APP_CONTEXT[key] = value
    logger.debug("应用上下文已更新: %s", key)


def get_app_context(key: str, default: Any = None) -> Any:
    """获取全局应用上下文值。"""
    return _APP_CONTEXT.get(key, default)


# 模块级单例
manager = TaskManager()
