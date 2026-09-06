"""缺陷聚合仓储实现（Adapter）。

把"面向聚合的仓储接口"翻译为既有 DefectRepo（四层 Repository）的命令，
实现防腐层（Anti-Corruption Layer）。复用已验证的存储逻辑，同时让领域层
获得聚合级读写语义；后续如需换存储仅替换本文件。
"""
from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from app.domain.defects.domain.entities.defect import Defect
from app.repositories.defect_repo import DefectRepo


class DefectRepoAdapter:
    """将既有 DefectRepo 封装为面向聚合的仓储。"""

    def next_id(self) -> str:
        return uuid.uuid4().hex[:12]

    # ── 读：聚合重建 ────────────────────────────────
    def find_by_id(self, defect_id: str, include_deleted: bool = False) -> Optional[Defect]:
        if include_deleted:
            # 回收站 / 全部：直接查主表（含已删除行）
            for r in DefectRepo.list_trash(limit=9999, offset=0):
                if str(r.get("id")) == str(defect_id):
                    return Defect.from_dict(dict(r))
            return None
        row = DefectRepo.get_checked(defect_id)
        return Defect.from_dict(dict(row)) if row else None

    def list_trash(self, limit: int = 100, offset: int = 0) -> Tuple[List[Defect], int]:
        rows = DefectRepo.list_trash(limit=limit, offset=offset)
        total = DefectRepo.count_trash()
        return [Defect.from_dict(dict(r)) for r in rows], total

    def list(self, *, status: str = "", severity: str = "", limit: int = 100,
             offset: int = 0) -> Tuple[List[Defect], int]:
        rows = DefectRepo.list(status=status, severity=severity, limit=limit, offset=offset)
        total = DefectRepo.count(status=status, severity=severity)
        return [Defect.from_dict(dict(r)) for r in rows], total

    def stats(self) -> dict:
        return DefectRepo.get_stats()

    # ── 写：以聚合为粒度落库 ────────────────────────
    def save(self, defect: Defect) -> Defect:
        d = defect.to_dict()
        d["id"] = defect.id.value
        result = DefectRepo.create(d)
        return Defect.from_dict(dict(result)) if result else defect

    def update(self, defect: Defect) -> Optional[Defect]:
        d = defect.to_dict()
        persist = {k: v for k, v in d.items() if k not in ("id", "created_at")}
        # tags 以 JSON 字符串落库（DefectRepo.update 会做 JSON 序列化）
        result = DefectRepo.update(defect.id.value, persist)
        return Defect.from_dict(dict(result)) if result else None

    def soft_delete(self, defect_id: str) -> bool:
        return DefectRepo.soft_delete(defect_id)

    def restore(self, defect_id: str) -> bool:
        return DefectRepo.restore(defect_id)

    def purge(self, defect_id: str) -> bool:
        return DefectRepo.purge(defect_id)

    # ── 评论（子表旁路读写，透传既有 DefectRepo）────────────
    def list_comments(self, bug_id: str) -> List[dict]:
        return DefectRepo.list_comments(bug_id)

    def create_comment(self, bug_id: str, content: str = "", parent_id: str = "",
                       create_user: str = "", reply_user: str = "",
                       notifier: str = "") -> dict:
        return DefectRepo.create_comment(
            bug_id=bug_id, content=content, parent_id=parent_id,
            create_user=create_user, reply_user=reply_user, notifier=notifier,
        )

    def update_comment(self, comment_id: str, content: str) -> Optional[dict]:
        return DefectRepo.update_comment(comment_id, content)

    def delete_comment(self, comment_id: str) -> bool:
        return DefectRepo.delete_comment(comment_id)

    # ── 旁路：自动创建 / 永久删除 ────────────────────────
    def auto_create_from_result(self, file_path: str, test_result: dict,
                                test_case_id: str = "") -> Optional[dict]:
        return DefectRepo.auto_create_from_result(
            file_path=file_path, test_result=test_result,
            test_case_id=test_case_id,
        )

    def permanent_delete(self, defect_id: str) -> bool:
        return DefectRepo.delete(defect_id, permanent=True)
