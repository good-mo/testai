"""用例评审 DTO 契约桥（Web/Service 层 ↔ DDD 聚合视图翻译）。

DDD 聚合 `CaseReview.to_dict()` 与既有 `CaseReviewRepo`（四层 Repository）返回的
header dict 存在字段差异：
  - 评审人：聚合输出 `reviewers`（[{userId,userName}]），Repo 侧契约是
    `reviewers_json`（解析后的 JSON 数组），供 `_reviewers_of` 等前端格式化读取；
  - 聚合额外带 `links` / `case_count` / `deleted`（软删 0/1），Repo 侧契约只到
    header 级别（关联用例经独立 `list_links` 读取）。

本模块提供 `to_header_dict`，把聚合视图翻译回 Repo header dict 契约，
保证 `case_review_service`（router 唯一入口）委托 DDD 应用服务后，返回给上层
（router / 其它调用方）的 schema 与迁移前完全一致，实现零回归的渐进式迁移。
"""
from __future__ import annotations

from typing import Any, Dict


def _reviewers_json(agg: Dict[str, Any]) -> list:
    """从聚合视图提取评审人数组（含字符串/对象归一）。"""
    raw = agg.get("reviewers")
    if raw is None:
        return []
    out = []
    for r in raw or []:
        if isinstance(r, dict):
            uid = str(r.get("userId", "") or r.get("user_id", "") or r.get("id", "") or "")
            uname = str(r.get("userName", "") or r.get("name", "") or uid or "")
            out.append({"userId": uid, "userName": uname})
        else:
            s = str(r)
            out.append({"userId": s, "userName": s})
    return out


def to_header_dict(agg: Dict[str, Any]) -> Dict[str, Any]:
    """把 DDD 聚合视图翻译为既有 Repo header dict 契约。

    返回字段与 `CaseReviewRepo.header_to_dict` 一致，供 service 层上游无感消费。
    """
    reviewers = _reviewers_json(agg)
    # DDD 默认注入 admin 评审人；若确实为空则回退空数组
    if not reviewers and not agg.get("reviewers"):
        reviewers = [{"userId": "admin", "userName": "admin"}]
    return {
        "id": agg.get("id", ""),
        "name": agg.get("name", ""),
        "num": int(agg.get("num") or 1),
        "module_id": agg.get("module_id", "root"),
        "project_id": agg.get("project_id", ""),
        "status": agg.get("status", "UNDERWAY"),
        "review_pass_rule": agg.get("review_pass_rule", "SINGLE"),
        "pos": int(agg.get("pos") or 0),
        "start_time": agg.get("start_time") or 0,
        "end_time": agg.get("end_time") or 0,
        "tags": list(agg.get("tags") or []),
        "description": agg.get("description", ""),
        "create_time": agg.get("create_time"),
        "create_user": agg.get("create_user", "admin"),
        "update_time": agg.get("update_time"),
        "update_user": agg.get("update_user", "admin"),
        "deleted": 1 if agg.get("deleted") else 0,
        "reviewers_json": reviewers,
    }


def header_to_command_input(header: Dict[str, Any]) -> Dict[str, Any]:
    """把 Repo/Web header dict 归一为应用命令可读的字段。

    供 service 把上游请求（经 header 形态）翻译为 DDD 应用服务命令。
    """
    return {
        "name": header.get("name", ""),
        "description": header.get("description", ""),
        "module_id": header.get("module_id", "root"),
        "project_id": header.get("project_id", ""),
        "status": header.get("status", "UNDERWAY"),
        "review_pass_rule": header.get("review_pass_rule", "SINGLE"),
        "reviewers": header.get("reviewers", None) if "reviewers" in header else
                     header.get("reviewers_json"),
        "tags": header.get("tags"),
        "start_time": header.get("start_time"),
        "end_time": header.get("end_time"),
    }


__all__ = ["to_header_dict", "header_to_command_input"]
