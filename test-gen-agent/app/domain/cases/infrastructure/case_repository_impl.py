"""用例聚合仓储实现（Adapter）。

把"面向聚合的仓储接口"翻译为既有 CaseRepo（四层 Repository）的命令，
实现防腐层（Anti-Corruption Layer），保留已验证的存储逻辑，同时让领域
层获得聚合级的读写语义。后续如需换存储，仅替换本文件即可。
"""
from __future__ import annotations

import json
from typing import List, Optional, Tuple

from app.domain.cases.domain.entities.case import TestCase
from app.repositories.case_repo import CaseRepo


class CaseRepoAdapter:
    """将既有 CaseRepo 封装为面向聚合的仓储。"""

    # ── 标识生成（沿用既有主键策略，与旧代码一致）────
    def next_id(self) -> str:
        import uuid
        return uuid.uuid4().hex[:12]

    # ── 读：聚合重建 ────────────────────────────────
    def find_by_id(self, case_id: str) -> Optional[TestCase]:
        row = CaseRepo.get(case_id)
        return TestCase.from_dict(row) if row else None

    def find_deleted(self, case_id: str) -> Optional[TestCase]:
        for r in self._raw_trash():
            if str(r.get("case_id")) == str(case_id):
                return self._mark_deleted(TestCase.from_dict(r))
        return None


    @staticmethod
    def _mark_deleted(case: TestCase) -> TestCase:
        """回收站快照读取后，强制标记为已删除（快照内 status 可能是删除前的旧值）。"""
        case._deleted = True
        return case

    def _raw_trash(self) -> List[dict]:
        rows = CaseRepo.list_trash_cases()
        out = []
        for r in rows:
            item = dict(r)
            cd = item.get("case_data")
            if isinstance(cd, str):
                try:
                    cd = json.loads(cd)
                except Exception:
                    cd = {}
            if isinstance(cd, dict):
                merged = dict(cd)
                merged["case_id"] = item.get("case_id")
                out.append(merged)
            else:
                item["case_id"] = item.get("case_id")
                out.append(item)
        return out

    # ── 写：以聚合为粒度落库 ────────────────────────
    def save(self, case: TestCase) -> TestCase:
        d = case.to_dict()
        d["id"] = case.id.value
        result = CaseRepo.create(d)
        return TestCase.from_dict(result) if result else case

    def update(self, case: TestCase) -> bool:
        d = case.to_dict()
        # 仅持久化主表标量字段；reviews/version/metadata 等由副作用流程处理
        persist = {k: v for k, v in d.items() if k not in (
            "id", "reviews", "version", "created_at",
        )}
        # test_type 已在 metadata.test_type 同步；去掉顶层 test_type，
        # 避免 CaseRepo.update() 用旧值覆盖 metadata 中更新的 test_type。
        persist.pop("test_type", None)
        return bool(CaseRepo.update(case.id.value, persist))

    def soft_delete(self, case_id: str, deleted_by: str = "", reason: str = "") -> bool:
        return bool(CaseRepo.trash_case(case_id, deleted_by=deleted_by, reason=reason))

    def restore(self, case_id: str, operator: str = "") -> bool:
        return bool(CaseRepo.restore_case(case_id, operator=operator))

    def list_deleted(self, limit: int = 100, offset: int = 0) -> Tuple[List[TestCase], int]:
        all_rows = self._raw_trash()
        total = len(all_rows)
        return [self._mark_deleted(TestCase.from_dict(r)) for r in all_rows[offset:offset + limit]], total

    def list_cases(self, *, status: str = "", priority: str = "", tag: str = "",
                   search: str = "", test_type: str = "", module_id: str = "",
                   limit: int = 100, offset: int = 0) -> Tuple[List[TestCase], int]:
        rows = CaseRepo.list_cases(
            status=status or None, priority=priority or None, tag=tag or None,
            search=search or None, test_type=test_type or None,
            module_id=module_id or None,
            limit=limit, offset=offset,
        )
        total = CaseRepo.count_cases(
            status=status or None, priority=priority or None, tag=tag or None,
            search=search or None, test_type=test_type or None,
            module_id=module_id or None,
        )
        return [TestCase.from_dict(r) for r in rows], total

    # ── 副作用表（版本/审计/缓存）────────────────────
    def create_version(self, case_id: str, snapshot: dict, version: int,
                       operator: str = "", change_desc: str = "") -> int:
        return CaseRepo.create_version(case_id, created_by=operator, change_desc=change_desc)

    def record_change(self, case_id: str, action: str, field: str = "",
                      old_value: str = "", new_value: str = "", operator: str = "") -> None:
        CaseRepo.record_change(case_id, action, field=field,
                               old_value=old_value, new_value=new_value, operator=operator)

    def invalidate_mindmap_cache(self) -> None:
        CaseRepo.invalidate_mindmap_cache()



    # ── 副属能力：评审管理表（case_reviews）────────────
    def submit_review_record(self, case_id: str, reviewer: str = "",
                             comment: str = "") -> dict:
        """仅在 case_reviews 表登记一条评审提交记录。

        不更新 test_cases.status（由聚合状态机负责），避免与 DDD 聚合
        更新路径重复写入。
        """
        import time
        CaseRepo._ensure_management_tables()
        rev_id = CaseRepo._mgmt_id()
        CaseRepo.execute(
            """INSERT INTO case_reviews
               (id, case_id, review_status, reviewer, comment, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (rev_id, case_id, "pending", reviewer, comment, time.time()),
        )
        return {"id": rev_id, "case_id": case_id, "review_status": "pending"}

    def approve_review_record(self, case_id: str, reviewer: str = "",
                              comment: str = "") -> dict:
        """仅更新 case_reviews 表评审状态为通过，不更新 test_cases.status。"""
        import time
        CaseRepo._ensure_management_tables()
        CaseRepo.execute(
            """UPDATE case_reviews
               SET review_status=?, reviewer=?, comment=?, reviewed_at=?
               WHERE case_id=?""",
            ("approved", reviewer, comment, time.time(), case_id),
        )
        return {"case_id": case_id, "review_status": "approved"}

    def reject_review_record(self, case_id: str, reviewer: str = "",
                             comment: str = "",
                             review_status: str = "rejected") -> dict:
        """仅更新 case_reviews 表评审状态为驳回/需修改，不更新 test_cases.status。"""
        import time
        CaseRepo._ensure_management_tables()
        CaseRepo.execute(
            """UPDATE case_reviews
               SET review_status=?, reviewer=?, comment=?, reviewed_at=?
               WHERE case_id=?""",
            (review_status, reviewer, comment, time.time(), case_id),
        )
        return {"case_id": case_id, "review_status": review_status}

    def get_reviews(self, case_id: str) -> list:
        return CaseRepo.get_reviews(case_id)

    # ── 副属能力：关联（case_relations）───────────────
    def add_relation(self, case_id: str, related_case_id: str,
                     relation_type: str = "related") -> dict:
        return CaseRepo.add_relation(case_id, related_case_id, relation_type)

    def remove_relation(self, case_id: str, related_id: str) -> bool:
        return CaseRepo.remove_relation(case_id, related_id)

    def list_relations(self, case_id: str) -> list:
        return CaseRepo.list_relations(case_id)

    # ── 副属能力：依赖（case_dependencies）─────────────
    def add_dependency(self, case_id: str, depends_on: str,
                       dep_type: str = "before", description: str = "") -> dict:
        return CaseRepo.add_dependency(case_id, depends_on, dep_type, description)

    def remove_dependency(self, case_id: str, depends_on: str) -> bool:
        return CaseRepo.remove_dependency(case_id, depends_on)

    def list_dependencies(self, case_id: str) -> list:
        return CaseRepo.list_dependencies(case_id)

    # ── 导入 / 导出（透传既有 CaseRepo 格式工具，保持字节/结构契约）──
    def export_excel(self, cases: list) -> bytes:
        return CaseRepo.export_excel(cases)

    def export_mindmap(self, cases: list = None) -> str:
        return CaseRepo.export_mindmap(cases)

    def import_excel(self, content: str, operator: str = "") -> dict:
        return CaseRepo.import_excel(content, operator)

    def import_mindmap(self, content: str, operator: str = "") -> dict:
        return CaseRepo.import_mindmap(content, operator)

# 单例（进程内复用）
case_repository = CaseRepoAdapter()
