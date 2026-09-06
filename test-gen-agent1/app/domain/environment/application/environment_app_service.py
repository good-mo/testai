"""环境应用服务（Application Service / Use Case 门面）。

Docker 拉起/停止/健康检查等运维副作用已下沉到 Infrastructure（docker_ops），
应用层负责编排：校验 → before_launch/after_* 状态钩子 → 告警联动。
"""
from __future__ import annotations

import uuid
from typing import Dict, Optional

from app.domain.common.domain_events import event_bus
from app.domain.environment.application.dto import (
    CreateAlertCommand,
    CreateCommand,
    DeleteCommand,
    EnvQuery,
    GetCommand,
    HealthCheckCommand,
    LaunchCommand,
    ListAlertsQuery,
    ResolveAlertCommand,
    StatusChangeCommand,
    StopCommand,
    UpdateCommand,
)
from app.domain.environment.domain.entities.environment import Environment
from app.domain.environment.domain.exceptions import (
    DomainValidationError,
    EnvironmentNotFound,
)
from app.domain.environment.domain.value_objects.env_status import EnvStatusEnum
from app.domain.environment.infrastructure.docker_ops import (
    check_container_running,
    check_http_health,
    docker_available,
    launch_container,
    stop_container,
)
from app.domain.environment.infrastructure.environment_repository_impl import (
    EnvironmentRepoAdapter,
)

# 告警级别与旧 environment_service 一致
_ALERT_WARNING = "warning"
_ALERT_CRITICAL = "critical"
_ENV_MAINTENANCE = "maintenance"


class EnvironmentAppService:
    """环境用例编排服务（含 Docker 运维编排）。"""

    def __init__(self, repo=None):
        self._repo = repo or EnvironmentRepoAdapter()

    # ── CRUD ─────────────────────────────────────────────
    def create(self, cmd: CreateCommand) -> dict:
        env = Environment(
            env_id=uuid.uuid4().hex[:12],
            name=cmd.name,
            description=cmd.description,
            env_type=cmd.env_type,
            endpoint=cmd.endpoint,
            docker_compose_path=cmd.docker_compose_path,
            container_name=cmd.container_name,
            image=cmd.image,
            health_check_url=cmd.health_check_url,
            owner=cmd.owner,
            tags=cmd.tags,
            _created=True,
        )
        saved = self._repo.create(env)
        self._publish(env)
        return saved.to_dict()

    def get(self, cmd: GetCommand) -> Optional[dict]:
        env = self._repo.get(cmd.env_id)
        if env is None:
            raise EnvironmentNotFound(f"环境 {cmd.env_id} 不存在")
        return env.to_dict()

    def list(self, query: EnvQuery) -> list:
        envs = self._repo.list(
            search=query.search, status=query.status, env_type=query.env_type
        )
        return [e.to_dict() for e in envs]

    def update(self, cmd: UpdateCommand) -> Optional[dict]:
        env = self._repo.get(cmd.env_id)
        if not env:
            raise EnvironmentNotFound(f"环境 {cmd.env_id} 不存在")
        env.update_meta(cmd.data)
        saved = self._repo.update(env)
        self._publish(env)
        return saved.to_dict() if saved else None

    def change_status(self, cmd: StatusChangeCommand) -> Optional[dict]:
        env = self._repo.get(cmd.env_id)
        if not env:
            raise EnvironmentNotFound(f"环境 {cmd.env_id} 不存在")
        env.change_status(cmd.new_status, cmd.error_message)
        saved = self._repo.update(env)
        self._publish(env)
        return saved.to_dict() if saved else None

    def delete(self, cmd: DeleteCommand) -> bool:
        env = self._repo.get(cmd.env_id)
        if env:
            # 删除语义上落为 offline；已在 offline 视为幂等（不触发非法自迁移）。
            if env.status.value != EnvStatusEnum.OFFLINE.value:
                try:
                    env.change_status("offline", "环境已删除")
                except DomainValidationError:
                    # 极端状态下无法迁移到 offline（如异常维护态）仍继续软删，
                    # 不让删除操作因状态机严格校验而失败。
                    env.update_meta({"error_message": "环境已删除"})
                self._publish(env)
        return self._repo.delete(cmd.env_id, permanent=cmd.permanent)

    # ── 回收站 ─────────────────────────────────────────────
    def list_trash(self) -> list:
        return self._repo.list_trash()

    def restore(self, env_id: str) -> bool:
        return self._repo.restore(env_id)

    def trash(self, env_id: str) -> bool:
        return self._repo.trash(env_id)

    def purge(self, env_id: str) -> bool:
        return self._repo.purge(env_id)

    # ── 告警 ─────────────────────────────────────────────
    def create_alert(self, cmd: CreateAlertCommand) -> dict:
        return self._repo.create_alert(
            cmd.env_id, cmd.env_name, cmd.level, cmd.message, cmd.detail
        )

    def list_alerts(self, query: ListAlertsQuery) -> list:
        return self._repo.list_alerts(limit=query.limit, level=query.level)

    def resolve_alert(self, cmd: ResolveAlertCommand) -> bool:
        return self._repo.resolve_alert(cmd.alert_id)

    def get_stats(self) -> dict:
        return self._repo.get_stats()

    # ── 生命周期（状态钩子）─────────────────────────────
    def before_launch(self, env_id: str) -> Environment:
        """拉起前校验并更新状态。返回环境对象。"""
        env = self._repo.get(env_id)
        if not env:
            raise EnvironmentNotFound(f"环境 {env_id} 不存在")
        env.change_status(EnvStatusEnum.LAUNCHING.value)
        self._repo.update(env)
        return env

    def after_launch_success(self, env_id: str) -> None:
        env = self._repo.get(env_id)
        if not env:
            raise EnvironmentNotFound(f"环境 {env_id} 不存在")
        env.change_status(EnvStatusEnum.ONLINE.value, "")
        self._repo.update(env)
        self._publish(env)

    def after_launch_error(self, env_id: str, error_msg: str) -> None:
        env = self._repo.get(env_id)
        if not env:
            return
        env.change_status(EnvStatusEnum.ERROR.value, error_msg)
        self._repo.update(env)
        self._publish(env)

    # ── Docker 运维编排（Docker 副作用经 infra docker_ops）──
    def launch(self, cmd: LaunchCommand) -> Dict:
        """拉起环境容器。经 infra docker_ops 执行 Docker 命令。"""
        env_id = cmd.env_id
        env = self._repo.get(env_id)
        if not env:
            return {"success": False, "error": f"环境 {env_id} 不存在"}

        env_dict = env.to_dict()

        if not docker_available():
            self._change_status_safe(env_id, EnvStatusEnum.ERROR.value,
                                     "Docker 不可用")
            self._create_alert(env_dict, "Docker 命令不可用，无法拉起容器",
                               _ALERT_CRITICAL)
            return {"success": False, "error": "Docker 不可用"}

        try:
            self.before_launch(env_id)
        except (EnvironmentNotFound, DomainValidationError) as exc:
            return {"success": False, "error": str(getattr(exc, "message", exc) or exc)}

        result = launch_container(env_dict)
        if not result["success"]:
            error_msg = result.get("error", "容器启动失败")
            self.after_launch_error(env_id, error_msg)
            self._create_alert(env_dict, error_msg, _ALERT_CRITICAL)
            return result

        self.after_launch_success(env_id)
        return result

    def stop(self, cmd: StopCommand) -> Dict:
        """停止环境容器。"""
        env_id = cmd.env_id
        env = self._repo.get(env_id)
        if not env:
            return {"success": False, "error": f"环境 {env_id} 不存在"}

        if not docker_available():
            return {"success": False, "error": "Docker 不可用"}

        result = stop_container(env.to_dict())
        if result["success"]:
            self._change_status_safe(env_id, EnvStatusEnum.OFFLINE.value, "")
        return result

    def health_check(self, cmd: HealthCheckCommand) -> Dict:
        """检查环境健康状态。"""
        env_id = cmd.env_id
        env = self._repo.get(env_id)
        if not env:
            return {"success": False, "error": f"环境 {env_id} 不存在"}

        env_dict = env.to_dict()

        # 维护态跳过检查
        if env_dict.get("status") == _ENV_MAINTENANCE:
            return {"success": True, "status": _ENV_MAINTENANCE,
                    "docker": True, "http": True}

        docker_ok = check_container_running(env_dict) if docker_available() else False
        http_ok, http_detail = check_http_health(env_dict.get("health_check_url", ""))

        if not docker_ok and not http_ok:
            self._change_status_safe(env_id, EnvStatusEnum.OFFLINE.value,
                                     "容器未运行且健康检查失败")
            self._create_alert(env_dict, "容器未运行，健康检查失败", _ALERT_CRITICAL)
            return {"success": False, "status": EnvStatusEnum.OFFLINE.value,
                    "docker": docker_ok, "http": http_ok}
        if not docker_ok:
            self._change_status_safe(env_id, EnvStatusEnum.ERROR.value,
                                     f"Docker 容器未运行 (HTTP: {http_detail})")
            self._create_alert(env_dict, "容器未运行，但健康检查通过", _ALERT_WARNING)
            return {"success": False, "status": EnvStatusEnum.ERROR.value,
                    "docker": docker_ok, "http": http_ok}
        if not http_ok:
            self._change_status_safe(env_id, EnvStatusEnum.ERROR.value,
                                     f"健康检查失败 ({http_detail})")
            self._create_alert(env_dict, f"HTTP 健康检查失败: {http_detail}", _ALERT_WARNING)
            return {"success": False, "status": EnvStatusEnum.ERROR.value,
                    "docker": docker_ok, "http": http_ok}

        self._change_status_safe(env_id, EnvStatusEnum.ONLINE.value, "")
        return {"success": True, "status": EnvStatusEnum.ONLINE.value,
                "docker": docker_ok, "http": http_ok}

    def health_check_all(self) -> Dict:
        """批量检查所有环境健康状态。"""
        envs = self._repo.list(search="", status="", env_type="")
        results = {
            "total": len(envs), "online": 0, "error": 0, "offline": 0, "detail": [],
        }
        for env in envs:
            env_dict = env.to_dict()
            if env_dict.get("status") == _ENV_MAINTENANCE:
                results["detail"].append({
                    "env_id": env.id.value, "name": env.name,
                    "status": _ENV_MAINTENANCE, "success": True,
                })
                continue
            r = self.health_check(HealthCheckCommand(env_id=env.id.value))
            detail = {
                "env_id": env.id.value,
                "name": env.name,
                "status": r.get("status", env_dict.get("status", "offline")),
                "success": r.get("success", False),
                "error": r.get("error", ""),
            }
            results["detail"].append(detail)
            if detail["status"] == EnvStatusEnum.ONLINE.value:
                results["online"] += 1
            elif detail["status"] == EnvStatusEnum.ERROR.value:
                results["error"] += 1
            else:
                results["offline"] += 1
        return results

    # ── 内部辅助 ────────────────────────────────────────
    def _change_status_safe(self, env_id: str, status: str, error_msg: str) -> None:
        try:
            self.change_status(StatusChangeCommand(
                env_id=env_id, new_status=status, error_message=error_msg))
        except (EnvironmentNotFound, DomainValidationError):
            pass

    def _create_alert(self, env: dict, message: str, level: str) -> None:
        try:
            self._repo.create_alert(
                env["id"], env.get("name", ""), level,
                "环境运行告警", message,
            )
        except Exception:
            pass

    @staticmethod
    def _publish(env: Environment) -> None:
        for ev in env.pull_domain_events():
            event_bus.dispatch(ev)


# 单例门面
environment_app_service = EnvironmentAppService()

__all__ = ["EnvironmentAppService", "environment_app_service"]
