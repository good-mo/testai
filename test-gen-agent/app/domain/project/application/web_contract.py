"""项目域 DTO 契约桥（Application → Web 层翻译）。

背景
----
Phase A 落地的 `ProjectAppService` 返回 `Project.to_dict()`，其口径与既有
四层 Web 层（`app/routers/projects.py` → `project_service` → `ProjectRepo`
返回的**仓库行**）存在两处差异：
  1. 聚合导出含 `members` 子实体数组，而 Web 契约里项目对象不含内嵌成员
     （成员经 `/project/member*` 等独立接口分页返回）；
  2. 聚合导出缺 `deleted_at`（软删时间戳由仓储维护，聚合不承载）。

为了让 router 在「阶段 B」改调 `ProjectAppService` 时对外 schema 零变化
（前端 / 契约测试 / 前端矩阵均可回归），本模块提供唯一的翻译出口：
聚合导出 dict → 既有仓库行口径 dict。

规则
----
- 只读翻译、无副作用、纯函数，便于单测；
- 保底字段缺省补 `""` / 0 / None，与既有 `ProjectRepo` 返回行对齐；
- 不在此处拼接业务规则（业务规则在领域层）。
"""
from __future__ import annotations

from typing import List


def to_row(project: dict) -> dict:
    """把 DDD 聚合导出 dict 翻译为既有 Web 层项目对象（仓库行口径）。

    入参：`ProjectAppService.create/get/update` 返回的 `Project.to_dict()`。
    出参：与 `ProjectRepo.get/list/update` 返回行字段对齐的对象，供 router 原样返回。
    """
    project = project or {}
    return {
        "id": project.get("id", ""),
        "name": project.get("name", ""),
        "description": project.get("description", ""),
        "repo_url": project.get("repo_url", ""),
        "language": project.get("language", "python"),
        "path": project.get("path", ""),
        "status": project.get("status", "active"),
        "organization_id": project.get("organization_id", ""),
        "deleted": int(bool(project.get("deleted", False))),
        # 聚合不承载软删时间戳，Web 契约兼容层统一给 None
        # （既有正常列表/详情读取软删项目均被过滤，deleted_at 恒为 None）
        "deleted_at": project.get("deleted_at"),
        "created_at": project.get("created_at"),
        "updated_at": project.get("updated_at"),
    }


def to_row_list(projects: List[dict]) -> List[dict]:
    """批量翻译列表结果。"""
    return [to_row(p) for p in (projects or [])]


def to_row_page(items: List[dict]) -> dict:
    """把 DDD `list()` 返回的 `{"list":[...]}` 转成 router 对外 `{"projects":[...]}`。"""
    return {"projects": to_row_list((items or {}).get("list", []))}


__all__ = ["to_row", "to_row_list", "to_row_page"]
