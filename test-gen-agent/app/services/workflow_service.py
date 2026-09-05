# app/services/workflow_service.py
"""工作流状态业务逻辑层（workflow 域 DDD 接入 · 阶段 C 薄门面）。

工作流状态 CRUD / 排序 / 流转 / 定义标记 / 播种等落库业务已收敛到 `workflow`
域 DDD 应用服务 `workflow_app_service`（见 `app/domain/workflow/`，聚合根
`WorkflowStatus`）。本 Service 收敛为对 DDD 应用门面的**薄委托门面**，仅保留既有
方法签名以兼容 `app/routers/project_compat_extra.py`、`app/routers/system_compat.py`、
`app/routers/system_compat_extra.py` 等调用方，参数经 DTO 翻译、返回沿用 DDD 门面
输出（含 `statusFlowTargets` / ms 时间 / pos，与重构前 `workflow_repo` 直连口径
零回归、可回滚）。

接线前修复的 DDD 缺陷：
  - `WorkflowRepoAdapter.save` 新建忽略聚合根 id → 返回 id ≠ 落库 id（id 漂移）；
    现 `workflow_repo.add_status` 支持可选 status_id，创建返回 id == 落库 id。
  - DDD `update` 空 name 抛校验错、不存在抛异常 → 对齐旧语义：空 name 视为不改名、
    状态不存在返回 None（由门面映射 404）。
  - `set_definition` START 清理按状态自身 scope 定位（PROJECT / ORGANIZATION 通用）。

> 推荐调用方直接使用 `workflow_app_service`；本类仅作过渡兼容层保留。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.domain.workflow.application.dto import (
    CreateStatusCommand,
    DeleteStatusCommand,
    GetStatusCommand,
    ListStatusesCommand,
    SeedDefaultsCommand,
    SetDefinitionCommand,
    SortStatusesCommand,
    UpdateFlowsCommand,
    UpdateStatusCommand,
)
from app.domain.workflow.application.workflow_app_service import (
    workflow_app_service as _ddd,
)


class WorkflowService:
    """工作流状态管理服务：router 层唯一业务入口（workflow 域 DDD 薄门面）。"""

    # ── 查询 ──────────────────────────────────────────────
    def list_statuses(self, scope_type: str, scope_id: str, scene: str) -> List[Dict[str, Any]]:
        """获取指定范围下的工作流状态列表。"""
        return _ddd.list(ListStatusesCommand(
            scope_type=scope_type, scope_id=scope_id, scene=scene,
        ))

    def get_status(self, status_id: str) -> Optional[Dict[str, Any]]:
        """获取单个状态，不存在返回 None。"""
        return _ddd.get(GetStatusCommand(status_id=status_id))

    # ── 变更 ──────────────────────────────────────────────
    def add_status(
        self,
        name: str,
        scene: str,
        scope_id: str,
        scope_type: str = "PROJECT",
        remark: str = "",
        all_transfer_to: bool = False,
    ) -> Dict[str, Any]:
        """创建工作流状态。"""
        return _ddd.create(CreateStatusCommand(
            name=name, scene=scene, scope_id=scope_id,
            scope_type=scope_type, remark=remark,
            all_transfer_to=all_transfer_to,
        ))

    def update_status(
        self,
        status_id: str,
        name: str = "",
        remark: str = "",
        all_transfer_to: bool = False,
        status_definitions: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """更新工作流状态，不存在返回 None。"""
        return _ddd.update(UpdateStatusCommand(
            status_id=status_id,
            name=name or None,
            remark=remark or None,
            all_transfer_to=all_transfer_to,
            status_definitions=status_definitions,
        ))

    def delete_status(self, status_id: str) -> bool:
        """删除工作流状态（级联清空其流转关系）。"""
        return _ddd.delete(DeleteStatusCommand(status_id=status_id))

    def sort_statuses(self, status_ids: List[str]) -> bool:
        """重新排序状态。"""
        return _ddd.sort(SortStatusesCommand(status_ids=list(status_ids)))

    def update_flows(self, status_id: str, target_ids: List[str]) -> bool:
        """更新状态流转关系。"""
        return _ddd.update_flows(UpdateFlowsCommand(
            status_id=status_id, target_ids=list(target_ids),
        ))

    def set_definition(self, status_id: str, definition_id: str, enable: bool) -> bool:
        """设置状态为初始态/结束态，状态不存在返回 False。"""
        return _ddd.set_definition(SetDefinitionCommand(
            status_id=status_id, definition_id=definition_id, enable=enable,
        ))

    # ── 播种 ──────────────────────────────────────────────
    def seed_default_statuses(self, scope_type: str, scope_id: str, scene: str) -> List[Dict[str, Any]]:
        """范围内不存在状态时播种默认（新建/处理中/已完成）。"""
        return _ddd.seed_defaults(SeedDefaultsCommand(
            scope_type=scope_type, scope_id=scope_id, scene=scene,
        ))


# 模块级单例（与其它 service 风格一致）
workflow_service = WorkflowService()


__all__ = ["workflow_service", "WorkflowService"]
