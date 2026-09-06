# app/routers/generation.py
"""测试生成与任务管理路由（Phase 3 重构：从 main.py 拆分）。"""
import asyncio
import os

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from app.core.response import fail, ok
from app.logging_config import get_logger
from app.models.schemas import ChatRequest
from app.domain.task_center.application.task_center_app_service import task_center_service
from app.tasks.manager import get_app_context, register_handler

logger = get_logger(__name__)
router = APIRouter(tags=["generation"])


async def _run_generation_impl(graph, req: ChatRequest) -> dict:
    """执行完整的测试生成工作流并落盘产物。"""
    config = {"configurable": {"thread_id": req.file_path}}
    result = await graph.ainvoke(
        {
            "source_code": req.source_code,
            "file_path": req.file_path,
            "test_type": req.test_type,
            "generate_script": req.generate_script,
            "retry_count": 0,
        },
        config=config,
    )

    # 同步 SQLite I/O（用例库/缺陷/运行记录/执行追溯）统一放入后台线程执行，
    # 避免在事件循环上直接跑阻塞操作。
    out_path = await asyncio.to_thread(_persist_run_result, req, result)

    return {
        "file_path": req.file_path,
        "test_type": req.test_type,
        "generated_tests": result.get("generated_tests", ""),
        "structured_cases": result.get("structured_cases", []),
        "test_result": result.get("test_result", {}),
        "coverage_report": result.get("coverage_report", {}),
        "performance_report": result.get("performance_report", {}),
        "retry_count": result.get("retry_count", 0),
        "saved_to": out_path,
    }


def _persist_run_result(req: ChatRequest, result: dict) -> str:
    """在后台线程执行落盘与 SQLite 持久化（调用方用 asyncio.to_thread 包裹）。"""
    generated_tests = result.get("generated_tests", "")
    out_path = None
    if generated_tests:
        os.makedirs("output", exist_ok=True)
        out_path = os.path.join("output", f"test_{os.path.basename(req.file_path)}")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(generated_tests)

    # 保存到用例库
    try:
        from app.domain.cases.application.case_app_service import case_service
        test_result = result.get("test_result", {})
        case = case_service.create({
            "title": f"测试: {req.file_path}",
            "source_code": req.source_code,
            "test_code": generated_tests,
            "file_path": req.file_path,
            "status": "review" if test_result.get("passed") else "draft",
            "test_type": req.test_type,
            "structured_cases": result.get("structured_cases", []),
        })
        if case:
            case_service.update_case_result(case.get("id", ""), test_result)
    except Exception as e:
        logger.warning("用例入库失败 [err=%s]", e)

    # 自动创建缺陷
    try:
        test_result = result.get("test_result", {})
        if test_result and not test_result.get("passed", True):
            from app.domain.defects.application.defect_app_service import defect_service
            defect_service.auto_create_from_result(
                file_path=req.file_path,
                test_result=test_result,
            )
    except Exception as e:
        logger.warning("缺陷自动创建失败 [err=%s]", e)

    # 保存运行记录（阶段 B：经 generation 域 DDD 应用服务生命周期 + 契约桥落库，
    # 与既有 run_service.save 逐字段契约等价，/api/runs 与报告兼容层零感知；
    # 失败时降级回 run_service.save 保证双轨可回滚）。
    try:
        from app.domain.generation.application.generation_app_service import (
            generation_app_service,
        )
        generation_app_service.persist_completed_run(
            file_path=req.file_path,
            source_code=req.source_code,
            generated_tests=generated_tests,
            test_result=result.get("test_result", {}),
            coverage_report=result.get("coverage_report", {}),
            performance_report=result.get("performance_report", {}),
            retry_count=result.get("retry_count", 0),
            saved_to=out_path,
            error="",
            source="single",
            operator="system",
            metadata={"via": "run_generation", "request": req.model_dump()},
        )
    except Exception as e:
        logger.warning("DDD 运行记录落库失败，回退 run_service [err=%s]", e)
        try:
            from app.domain.runs.application.run_app_service import run_service
            run_service.save(
                file_path=req.file_path,
                source_code=req.source_code,
                generated_tests=generated_tests,
                test_result=result.get("test_result", {}),
                coverage_report=result.get("coverage_report", {}),
                performance_report=result.get("performance_report", {}),
                retry_count=result.get("retry_count", 0),
                saved_to=out_path,
                error="",
                source="single",
                metadata={"via": "run_generation", "request": req.model_dump()},
            )
        except Exception as e2:
            logger.warning("运行记录保存失败 [err=%s]", e2)

    # 记录测试执行追溯
    try:
        test_result = result.get("test_result", {})
        if test_result:
            passed = bool(test_result.get("passed", True))
            from app.domain.test_insight.application.test_insight_app_service import insight_service
            insight_service.record_trace(
                file_path=req.file_path,
                result="passed" if passed else "failed",
                passed_count=int(test_result.get("passed_count", 0)),
                failed_count=int(test_result.get("failed_count", 0)),
                error_count=int(test_result.get("error_count", 0)),
                coverage=float((result.get("coverage_report", {}) or {}).get("coverage_pct", 0) or 0),
                created_by="test-agent",
            )
    except Exception as e:
        logger.warning("执行追溯记录失败 [err=%s]", e)

    return out_path


@register_handler("generation.run")
async def run_generation_named(req_data: dict) -> dict:
    """可恢复任务处理器：从全局上下文获取 graph，执行测试生成。

    参数 req_data 为 ChatRequest 的 dict 序列化形式，
    可通过 submit_named("generation.run", req_data) 提交。
    """
    from app.models.schemas import ChatRequest as _CR
    req = _CR(**req_data)
    graph = get_app_context("graph")
    if graph is None:
        from app.graph.builder import get_graph as _get_graph
        graph = _get_graph()
    return await _run_generation_impl(graph, req)


@router.post("/api/generate")
async def generate_tests_api(request: Request, req: ChatRequest, async_mode: bool = False):
    """一次性生成测试用例并返回完整结果。

    前置校验：source_code 为空时直接 400。
    此前空源码会一路走到 LLM 调用，在 CI/无 Key 环境下抛出
    认证/连接异常并被打成 500 —— 这属于调用方传参问题，
    应在入口拦掉，而不是让前端看到「服务器内部错误」。
    """
    if not (req.source_code or "").strip():
        return fail("source_code 不能为空", 400)

    if async_mode:
        task = await task_center_service.submit_task(
            "generation.run", req.model_dump(mode="json")
        )
        return ok({"task_id": task.task_id, "status": task.status})

    graph = request.app.state.graph
    result = await _run_generation_impl(graph, req)
    return ok(result)


@router.post("/api/generate/structured")
def generate_structured_api(request: Request, req: ChatRequest):
    """仅生成结构化测试用例。"""
    if not (req.source_code or "").strip():
        return fail("source_code 不能为空", 400)

    from app.generators.mock_generator import generate_mocks
    from app.generators.test_generator import generate_structured_cases
    from app.scanners.python_scanner import scan_python_code

    try:
        scan_result = scan_python_code(req.source_code)
        signatures = scan_result.get("functions", [])
    except Exception:
        signatures = []

    mock_state = {"source_code": req.source_code}
    mocks_result = generate_mocks(mock_state)
    mocks = mocks_result.get("mocks", {})

    result = generate_structured_cases({
        "source_code": req.source_code,
        "file_path": req.file_path,
        "test_type": req.test_type,
        "signatures": signatures,
        "mocks": mocks,
    })

    return ok({
        "file_path": req.file_path,
        "test_type": result.get("test_type", req.test_type),
        "structured_cases": result.get("structured_cases", []),
    })


@router.post("/api/tasks")
async def submit_task(request: Request, req: ChatRequest):
    """提交生成任务到后台队列。"""
    if not (req.source_code or "").strip():
        return fail("source_code 不能为空", 400)

    task = await task_center_service.submit_task(
        "generation.run", req.model_dump(mode="json")
    )
    return ok({"task_id": task.task_id, "status": task.status})


@router.get("/api/tasks/{task_id}")
def get_task(request: Request, task_id: str):
    """查询任务状态与结果。"""
    task = task_center_service.get_task(task_id)
    if not task:
        return fail(f"task {task_id} 不存在", 404)
    return ok(task)


@router.get("/api/tasks")
def list_tasks(request: Request, limit: int = 20):
    """列出最近的任务。"""
    tasks = task_center_service.list_raw_tasks(limit=limit)
    return ok({"tasks": tasks, "total": len(tasks)})


@router.websocket("/ws/generate")
async def generate_ws(ws: WebSocket):
    """流式输出 LangGraph 每个节点的执行进度。"""
    await ws.accept()
    client = ws.client.host if ws.client else "unknown"
    logger.info("WebSocket 连接建立 [client=%s]", client)
    try:
        data = await ws.receive_json()
        source = data.get("source_code", "").strip()
        file_path = data.get("file_path", "demo.py")
        test_type = data.get("test_type", "functional")
        generate_script = data.get("generate_script", True)

        if not source:
            await ws.send_json({"error": "源代码不能为空"})
            await ws.close()
            return

        graph = ws.app.state.graph
        config = {"configurable": {"thread_id": file_path}}

        async for event in graph.astream(
            {"source_code": source, "file_path": file_path, "test_type": test_type,
             "generate_script": generate_script, "retry_count": 0},
            config=config,
            stream_mode="updates",
        ):
            for node_name, node_output in event.items():
                await ws.send_json({"step": {"__node": node_name, **(node_output or {})}})

        await ws.send_json({"done": True})

        try:
            final = await graph.aget_state(config)
            values = (final.values if final else {}) or {}
            from app.domain.generation.application.generation_app_service import (
                generation_app_service,
            )

            # 同步 DB 写操作放入线程池执行，避免阻塞事件循环。
            # 阶段 B：WS 生成记录同样经 generation 域 DDD 生命周期 + 契约桥落库，
            # 失败时降级回 run_service.save 保证可回滚。
            def _persist() -> None:
                ok_row = generation_app_service.persist_completed_run(
                    file_path=file_path,
                    source_code=source,
                    generated_tests=values.get("generated_tests", ""),
                    test_result=values.get("test_result", {}),
                    coverage_report=values.get("coverage_report", {}),
                    performance_report=values.get("performance_report", {}),
                    retry_count=values.get("retry_count", 0),
                    saved_to="",
                    error="",
                    source="websocket",
                    operator="system",
                    metadata={"via": "ws_generate", "client": client},
                )
                if ok_row is None:
                    raise RuntimeError("persist_completed_run returned None")

            try:
                await asyncio.to_thread(_persist)
            except Exception as e:
                logger.warning("DDD WS 落库失败，回退 run_service [err=%s]", e)
                from app.domain.runs.application.run_app_service import run_service
                await asyncio.to_thread(
                    run_service.save,
                    file_path=file_path,
                    source_code=source,
                    generated_tests=values.get("generated_tests", ""),
                    test_result=values.get("test_result", {}),
                    coverage_report=values.get("coverage_report", {}),
                    performance_report=values.get("performance_report", {}),
                    retry_count=values.get("retry_count", 0),
                    saved_to="",
                    error="",
                    source="websocket",
                    metadata={"via": "ws_generate", "client": client},
                )
        except Exception as e:
            logger.warning("WS 运行记录保存失败 [err=%s]", e)

    except WebSocketDisconnect:
        logger.warning("客户端断开连接 [client=%s]", client)
    except Exception as e:
        logger.error("测试生成失败 [client=%s, err=%s]", client, e, exc_info=True)
        try:
            await ws.send_json({"error": f"生成失败: {str(e)}"})
        except Exception:
            pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass
