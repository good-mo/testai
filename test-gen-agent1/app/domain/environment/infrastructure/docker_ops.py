"""环境域 Docker 运维辅助（Infrastructure 层）。

把「拉起/停止/健康检查」所需的 Docker 子进程调用、HTTP 探测等外部副作用
收敛到 Infrastructure 适配层，供 Application Service 编排复用。保持 Domain
层对 Docker/网络零依赖。
"""
from __future__ import annotations

import subprocess
import time
from typing import Dict, Optional

_DOCKER_TIMEOUT = 120
_STOP_TIMEOUT = 60
_HEALTH_TIMEOUT = 10
_HTTP_TIMEOUT = 5


def docker_available() -> bool:
    """检查 Docker CLI 是否可用。"""
    try:
        result = subprocess.run(
            ["docker", "--version"], capture_output=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def launch_container(env: Dict) -> Dict:
    """拉起容器（compose up -d 或 docker run -d）。

    env: 环境字典（来自 repo/聚合 to_dict），需要含
         docker_compose_path 或 container_name+image。

    返回 {success, command?, output?, error?}。不落状态/告警——由调用方编排。
    """
    if env.get("docker_compose_path"):
        command = ["docker", "compose", "-f", env["docker_compose_path"], "up", "-d"]
        command_desc = f"docker compose -f {env['docker_compose_path']} up -d"
    elif env.get("container_name") and env.get("image"):
        command = ["docker", "run", "-d", "--name", env["container_name"], env["image"]]
        command_desc = f"docker run -d --name {env['container_name']} {env['image']}"
    else:
        return {
            "success": False,
            "error": "缺少容器配置（compose 文件或 image）",
        }

    try:
        result = subprocess.run(command, capture_output=True, timeout=_DOCKER_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "容器启动超过 120 秒未完成"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)}

    if result.returncode == 0:
        return {
            "success": True,
            "command": command_desc,
            "output": result.stdout.decode("utf-8", errors="replace")[:500],
        }
    return {
        "success": False,
        "error": result.stderr.decode("utf-8", errors="replace")[:500],
    }


def stop_container(env: Dict) -> Dict:
    """停止容器（compose down 或 docker stop）。"""
    try:
        if env.get("docker_compose_path"):
            result = subprocess.run(
                ["docker", "compose", "-f", env["docker_compose_path"], "down"],
                capture_output=True, timeout=_STOP_TIMEOUT,
            )
        elif env.get("container_name"):
            result = subprocess.run(
                ["docker", "stop", env["container_name"]],
                capture_output=True, timeout=_STOP_TIMEOUT,
            )
        else:
            return {"success": False, "error": "缺少容器配置"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "停止容器超时"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)}

    if result.returncode == 0:
        return {"success": True}
    return {
        "success": False,
        "error": result.stderr.decode("utf-8", errors="replace")[:300],
    }


def check_container_running(env: Dict) -> bool:
    """检查容器是否处于运行态（Docker inspect / compose ps）。"""
    try:
        if env.get("container_name"):
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Running}}",
                 env["container_name"]],
                capture_output=True, timeout=_HEALTH_TIMEOUT,
            )
            return result.returncode == 0 and result.stdout.strip() == "true"
        if env.get("docker_compose_path"):
            result = subprocess.run(
                ["docker", "compose", "-f", env["docker_compose_path"], "ps", "-q"],
                capture_output=True, timeout=_HEALTH_TIMEOUT,
            )
            return result.returncode == 0 and result.stdout.strip() != ""
    except Exception:  # noqa: BLE001
        pass
    return False


def check_http_health(health_check_url: str) -> tuple:
    """HTTP 健康探测。返回 (ok: bool, detail: str)。"""
    if not health_check_url:
        return False, ""
    import urllib.request
    try:
        req = urllib.request.Request(
            health_check_url, method="GET", timeout=_HTTP_TIMEOUT,
        )
        with urllib.request.urlopen(req) as resp:
            return resp.status == 200, f"HTTP {resp.status}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:200]


__all__ = [
    "docker_available",
    "launch_container",
    "stop_container",
    "check_container_running",
    "check_http_health",
]
