# app/routers/projects_scan.py
"""项目扫描与批量生成路由（Phase 3 重构 · 4 层对齐）。"""
import asyncio

from fastapi import APIRouter, Request

from app.core.response import fail, ok
from app.logging_config import get_logger
from app.domain.project.application.dto import ProjectGenerateRequest, ProjectScanRequest

logger = get_logger(__name__)
router = APIRouter(tags=["projects-scan"])


@router.post("/api/projects/scan")
async def api_scan_project(body: ProjectScanRequest):
    """递归扫描项目目录，返回所有源文件与函数签名。"""
    from app.domain.project.application.project_app_service import project_service
    project_path = body.project_path
    if not project_path:
        return fail("缺少 project_path 参数", 400)
    try:
        result = await asyncio.to_thread(project_service.scan_project, project_path)
        return ok(result)
    except FileNotFoundError as e:
        return fail(str(e), 404)
    except PermissionError as e:
        return fail(f"没有权限访问: {e}", 403)
    except Exception as e:
        logger.error("项目扫描失败 [path=%s, err=%s]", project_path, e, exc_info=True)
        return fail(f"扫描失败: {str(e)[:100]}", 400)


@router.post("/api/projects/generate")
async def api_generate_project(request: Request, body: ProjectGenerateRequest, async_mode: bool = False):
    """项目级批量生成测试用例。"""
    from app.config import settings
    from app.domain.project.application.project_app_service import project_service
    project_path = body.project_path

    if not project_path:
        return fail("缺少 project_path 参数", 400)
    try:
        scan_result = await asyncio.to_thread(project_service.scan_project, project_path)
        paths = [f["path"] for f in scan_result["files"]]
        sources = await asyncio.to_thread(project_service.collect_sources_from_paths, paths)
    except FileNotFoundError as e:
        return fail(str(e), 404)
    except Exception as e:
        logger.error("项目批量生成扫描失败 [path=%s, err=%s]", project_path, e, exc_info=True)
        return fail(f"扫描失败: {str(e)[:100]}", 400)

    graph = request.app.state.graph

    async def _process_one(src):
        """处理单个源文件。单文件失败不阻断批量流程，返回 error 标记。"""
        try:
            config = {"configurable": {"thread_id": src["file_path"]}}
            result = await graph.ainvoke(
                {
                    "source_code": src["source_code"],
                    "file_path": src["file_path"],
                    "test_type": "functional",
                    "retry_count": 0,
                },
                config=config,
            )
            generated_tests = result.get("generated_tests", "")
            test_result = result.get("test_result", {})
            try:
                from app.domain.runs.application.run_app_service import run_service
                await asyncio.to_thread(
                    run_service.save,
                    file_path=src["file_path"],
                    source_code=src["source_code"],
                    generated_tests=generated_tests,
                    test_result=test_result,
                    coverage_report=result.get("coverage_report", {}),
                    performance_report=result.get("performance_report", {}),
                    retry_count=result.get("retry_count", 0),
                    saved_to="",
                    error="",
                    source="project",
                    metadata={"via": "project_batch"},
                )
            except Exception as e:
                logger.warning("项目运行记录保存失败 [err=%s]", e)
            return {
                "file_path": src["file_path"],
                "generated_tests": generated_tests,
                "test_result": test_result,
                "coverage_report": result.get("coverage_report", {}),
                "retry_count": result.get("retry_count", 0),
            }
        except Exception as e:
            # 单文件 LLM/执行失败不阻断整个批量任务
            logger.error(
                "批量生成单文件失败 [path=%s, err=%s]",
                src["file_path"], e, exc_info=True,
            )
            return {
                "file_path": src["file_path"],
                "generated_tests": "",
                "test_result": {"passed": False, "error": str(e)[:200]},
                "error": str(e)[:200],
            }

    async def run_batch():
        sem = asyncio.Semaphore(settings.task_workers)

        async def _with_sem(src):
            async with sem:
                return await _process_one(src)

        results = await asyncio.gather(*(_with_sem(src) for src in sources))
        return list(results)

    if async_mode:
        tm = request.app.state.task_manager
        task = await tm.submit(run_batch)
        return ok({"task_id": task.task_id, "status": task.status})

    results = await run_batch()
    return ok({"results": results, "total": len(results)})
