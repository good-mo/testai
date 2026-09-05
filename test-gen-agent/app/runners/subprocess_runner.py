# app/runners/subprocess_runner.py
"""
测试运行器（Docker 沙箱优先）
==============================
使用 Docker 容器隔离运行 pytest，避免被测/测试代码在宿主机上执行，
提升安全性（P0）。Docker 不可用时自动降级为宿主机子进程。
"""
from app.config import settings
from app.graph.state import AgentState
from app.logging_config import get_logger
from app.sandbox.docker_runner import run_in_sandbox

logger = get_logger(__name__)


def _parse_pytest_counts(output: str) -> dict:
    """从 pytest 输出解析 passed / failed / error 用例计数。

    兼容典型输出（pytest -v --tb=short）：
        "2 passed in 0.01s"
        "1 failed, 2 passed in 0.05s"
        "1 failed, 3 passed, 1 warning in 1.2s"
        "5 errors in 0.2s"
    """
    import re
    counts = {"passed": 0, "failed": 0, "error": 0}
    # 匹配 "N passed"（pytest 输出末尾摘要）
    m = re.search(r"(\d+)\s+passed", output)
    if m:
        counts["passed"] = int(m.group(1))
    m = re.search(r"(\d+)\s+failed", output)
    if m:
        counts["failed"] = int(m.group(1))
    m = re.search(r"(\d+)\s+errors?", output)
    if m:
        counts["error"] = int(m.group(1))
    return counts


def run_tests(state: AgentState) -> dict:
    """LangGraph 节点：运行生成/修复后的测试代码（沙箱隔离）。"""
    logger.debug("开始运行 pytest（沙箱）")
    module_name = state.get("file_path", "demo").replace(".py", "").replace("/", "_")
    try:
        timeout = settings.test_timeout
        result = run_in_sandbox(
            source_code=state["source_code"],
            test_code=state["generated_tests"],
            module_name=module_name,
            timeout=timeout,
        )
        passed = result.returncode == 0
        # 解析 pytest 输出的用例计数，供前端展示
        output_text = f"{result.stdout or ''}\n{result.stderr or ''}"
        counts = _parse_pytest_counts(output_text)
        passed_count = counts["passed"]
        # 若 returncode==0 但未解析出通过数，则视为至少 1 条通过（空测试集时 returncode 也是 0）
        if passed and counts["passed"] == 0 and "collected 0" not in output_text:
            passed_count = 1
        if passed:
            logger.info(
                "测试运行通过 ✅ [passed=%d]",
                passed_count,
            )
        else:
            # 失败用 WARNING（可恢复，会进入修复循环）
            logger.warning(
                "测试运行失败 [returncode=%d, passed=%d, failed=%d]",
                result.returncode, counts["passed"], counts["failed"],
            )
        return {
            "test_result": {
                "passed": result.returncode == 0,
                "passed_count": passed_count,
                "failed_count": counts["failed"],
                "error_count": counts["error"],
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        }
    except Exception as e:
        logger.error("测试运行异常 [err=%s]", e, exc_info=True)
        return {"test_result": {"passed": False, "passed_count": 0, "failed_count": 0, "error_count": 1, "stderr": f"Runner error: {e}"}}
