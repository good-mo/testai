# app/services/case_service.py
"""用例业务逻辑层（Phase 3 重构 · 4 层对齐）。

本层是 routers 的唯一业务编排入口。
职责：
  - 只做业务编排（校验 + 调用 repo + 组装），不直接拼 SQL；
  - 所有数据访问统一下沉到 app.repositories.case_repo.CaseRepo，
    不再直接回调 app.cases.management，形成单一数据出口。
"""
import json
from typing import Optional

from app.repositories.case_repo import STATUS_DEPRECATED, CaseRepo
from app.services.apitest_service import apitest_service

DEPRECATED = STATUS_DEPRECATED


class CaseService:
    """用例管理服务。"""

    # ── 基础 CRUD（repo 层）────────────────────────────────
    def create(self, data: dict) -> dict:
        """创建用例（委托 DDD 应用服务，规则单一来源在领域层）。

        Phase A→B→C：cases 域 DDD 已就绪后，把既有四层门面这一高频写入口
        接到 `case_app_service`（参数经 DTO 翻译）。聚合根负责守护不变量与
        落库 + 审计/版本副作用；此处保留门面以兼容 router 及 15+ 处调用方。
        返回 schema 与既有 CaseRepo 归一化结果保持一致。
        """
        from app.domain.cases.application.case_app_service import case_app_service
        from app.domain.cases.application.dto import CreateCaseCommand
        from app.domain.common.exceptions import DomainValidationError

        # 新建用例默认草稿；显式 status 经 DDD 聚合创建（兼容 generation 等
        # 直接以 review 等状态入库的场景），废弃态禁止作为初始态。
        status = data.get("status") or "draft"
        if status == STATUS_DEPRECATED:
            status = "draft"
        try:
            created = case_app_service.create(CreateCaseCommand(
                title=data.get("title", ""),
                case_id=str(data.get("id") or ""),
                description=data.get("description", ""),
                source_code=data.get("source_code", ""),
                test_code=data.get("test_code", ""),
                file_path=data.get("file_path", ""),
                tags=list(data.get("tags") or []),
                priority=data.get("priority", "P2"),
                requirement_ref=data.get("requirement_ref", ""),
                test_type=data.get("test_type", "functional"),
                structured_cases=data.get("structured_cases"),
                metadata=data.get("metadata"),
                status=status,
                operator=str(data.get("operator") or "system"),
            ))
        except DomainValidationError as exc:
            raise ValueError(str(exc)) from exc
        # 回读归一化记录，保证返回 schema 与既有调用方契约一致
        case_id = created.get("id", "")
        return CaseRepo.get(case_id) if case_id else created

    def get(self, case_id: str) -> Optional[dict]:
        """获取未删除用例详情（委托 DDD 读路径）。

        DDD 聚合从 `case_repository` 加载并重建（含 last_result 等持久化
        字段的 round-trip），`to_dict()` 补齐归一化 schema。与既有 CaseRepo
        归一化输出字段一致（另有 version/reviews 聚合视图字段），零破坏。
        """
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.get(case_id)

    def update(self, case_id: str, data=None, **kwargs) -> Optional[dict]:
        """更新用例（委托 DDD 应用服务，规则单一来源在领域层）。

        支持两种调用方式:
          - case_service.update(case_id, {"title": "x"})  # dict 形式
          - case_service.update(case_id, title="x")       # kwargs 形式

        聚合根守护标题非空、状态机迁移、优先级/测试类型合法性等不变量。
        领域异常转 ValueError 兼容既有调用方捕获。返回与既有 CaseRepo
        归一化记录一致的 schema。
        """
        from app.domain.cases.application.case_app_service import case_app_service
        from app.domain.cases.application.dto import UpdateCaseCommand
        from app.domain.common.exceptions import AggregateNotFound
        from app.domain.common.exceptions import DomainException

        if data is None and kwargs:
            data = kwargs
        elif isinstance(data, dict):
            pass
        updates = dict(data or {})

        # 兼容：metadata 可能以 JSON 字符串形式传入（router 预序列化）
        meta = updates.get("metadata")
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except (json.JSONDecodeError, TypeError):
                meta = {}
        if meta is not None and not isinstance(meta, dict):
            meta = {}

        try:
            result = case_app_service.update(UpdateCaseCommand(
                case_id=case_id,
                title=updates.get("title"),
                description=updates.get("description"),
                source_code=updates.get("source_code"),
                test_code=updates.get("test_code"),
                file_path=updates.get("file_path"),
                tags=updates.get("tags"),
                priority=updates.get("priority"),
                test_type=updates.get("test_type"),
                requirement_ref=updates.get("requirement_ref"),
                structured_cases=updates.get("structured_cases"),
                metadata=meta if isinstance(meta, dict) else None,
                status=updates.get("status"),
                operator=str(updates.get("operator") or "system"),
            ))
        except AggregateNotFound:
            return None  # 兼容旧 CaseRepo.update 对不存在用例返回 None
        except DomainException as exc:
            raise ValueError(str(getattr(exc, "message", exc))) from exc
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        if not result:
            return None
        # 回读归一化记录，保证返回 schema 与既有调用方契约一致
        return CaseRepo.get(case_id) if CaseRepo.get(case_id) else result

    def delete(self, case_id: str, soft: bool = True) -> bool:
        """删除用例。soft=True 软删除进回收站（deprecated）。

        委托 DDD case_app_service（soft→soft_delete 走聚合状态机+trash 原子快照；
        hard→hard_delete 物理清除关联子表）。
        """
        from app.domain.cases.application.case_app_service import case_app_service
        from app.domain.cases.application.dto import DeleteCaseCommand

        if soft:
            try:
                case_app_service.soft_delete(DeleteCaseCommand(
                    case_id=case_id, operator="system", reason="",
                ))
                return True
            except Exception:
                return False
        return case_app_service.hard_delete(case_id)

    def list(self, search: str = "", status: str = "", priority: str = "",
             tag: str = "", test_type: str = "", module_id: str = "",
             limit: int = 50, offset: int = 0) -> tuple:
        """分页查询未删除用例，返回 (rows, total)。

        委托 DDD `case_app_service.list_cases`：分页 + 过滤统一走领域仓储
        （含 module_id 过滤在 DDD 防腐层转发修复）。返回行经 to_dict 补齐
        last_result 等既有 schema 字段，保证与旧 CaseRepo 归一化输出一致。
        """
        from app.domain.cases.application.case_app_service import case_app_service
        from app.domain.cases.application.dto import ListQuery

        result = case_app_service.list_cases(ListQuery(
            search=search or "", status=status or "", priority=priority or "",
            tag=tag or "", test_type=test_type or "", module_id=module_id or "",
            limit=int(limit or 0), offset=int(offset or 0),
        ))
        return result.get("list", []), result.get("total", 0)

    def get_stats(self) -> dict:
        """获取用例统计（委托 DDD）。"""
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.get_stats()

    def count_cases(self, search=None, status=None, priority=None,
                    tag=None, test_type=None, module_id=None) -> int:
        """统计符合条件的用例数（委托 DDD，兼容旧 list_cases 契约）。"""
        from app.domain.cases.application.case_app_service import case_app_service
        from app.domain.cases.application.dto import ListQuery

        result = case_app_service.list_cases(ListQuery(
            search=search or "", status=status or "", priority=priority or "",
            tag=tag or "", test_type=test_type or "", module_id=module_id or "",
            limit=1, offset=0,  # 只需 total，不需要真实数据
        ))
        return int(result.get("total", 0))

    def list_cases(self, search=None, status=None, priority=None,
                   tag=None, test_type=None, module_id=None,
                   limit=100, offset=0) -> list:
        """列出用例（委托 DDD `case_app_service.list_cases`）。

        返回行 schema 与既有 CaseRepo 归一化结果一致（含 last_result /
        module_id 过滤）。供 /api/cases 及 15+ 处既有调用方复用。
        """
        from app.domain.cases.application.case_app_service import case_app_service
        from app.domain.cases.application.dto import ListQuery

        result = case_app_service.list_cases(ListQuery(
            search=search or "", status=status or "", priority=priority or "",
            tag=tag or "", test_type=test_type or "", module_id=module_id or "",
            limit=int(limit or 0), offset=int(offset or 0),
        ))
        return result.get("list", [])

    def update_case_result(self, case_id: str, result: dict) -> Optional[dict]:
        """更新用例的最后执行结果（委托 DDD）。"""
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.update_case_result(case_id, result)

    # ── 高级管理（数据访问经 CaseRepo）───────────────────
    def get_mindmap(self, project_filter: str = "") -> dict:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.get_mindmap(project_filter)

    # ── 导入/导出（委托 DDD case_app_service，语义与契约透传既有 CaseRepo）──
    def export_excel(self, cases: list) -> bytes:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.export_excel(cases)

    def export_mindmap(self, cases: list) -> str:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.export_mindmap(cases)

    def import_excel(self, content: str, operator: str = "") -> dict:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.import_excel(content, operator)

    def import_mindmap(self, content: str, operator: str = "") -> dict:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.import_mindmap(content, operator)

    def get_full_info(self, case_id: str) -> Optional[dict]:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.get_full_info(case_id)

    # ── 关系管理（委托 DDD case_app_service）─────────────
    def add_relation(self, case_id: str, related_case_id: str,
                     relation_type: str = "related") -> dict:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.add_relation(case_id, related_case_id, relation_type)

    def remove_relation(self, case_id: str, related_id: str) -> bool:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.remove_relation(case_id, related_id)

    def list_relations(self, case_id: str) -> list:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.list_relations(case_id)

    # ── 评审（委托 DDD 聚合状态机；case_reviews 管理表由 DDD infra 落）──
    def submit_review(self, case_id: str, reviewer: str = "",
                      comment: str = "") -> dict:
        """提交用例评审：委托 DDD case_app_service.submit_review。

        聚合根 `TestCase.submit_for_review()` 走状态机草稿→评审中；
        同时 DDD infrastructure 将评审记录落 case_reviews 管理表。
        返回与既有 CaseRepo.submit_review 相同 schema（id/case_id/review_status）。
        """
        from app.domain.cases.application.case_app_service import case_app_service
        from app.domain.cases.application.dto import ReviewCommand
        from app.domain.common.exceptions import AggregateNotFound
        from app.domain.common.exceptions import DomainException

        try:
            case_app_service.submit_review(ReviewCommand(
                case_id=case_id, outcome="submitted",
                reviewer=reviewer or "", comment=comment,
                operator=reviewer or "system",
            ))
        except AggregateNotFound as exc:
            raise ValueError(str(getattr(exc, "message", exc)))
        except DomainException as exc:
            raise ValueError(str(getattr(exc, "message", exc)))
        # 回读最新评审记录保持既有返回 schema
        records = CaseRepo.get_reviews(case_id)
        if records:
            return records[0]
        return {"case_id": case_id, "review_status": "pending"}

    def approve_review(self, case_id: str, reviewer: str = "",
                       comment: str = "") -> dict:
        """通过用例评审：委托 DDD case_app_service.review(outcome='approved')。"""
        from app.domain.cases.application.case_app_service import case_app_service
        from app.domain.cases.application.dto import ReviewCommand
        from app.domain.common.exceptions import AggregateNotFound
        from app.domain.common.exceptions import DomainException

        try:
            case_app_service.review(ReviewCommand(
                case_id=case_id, outcome="approved",
                reviewer=reviewer or "", comment=comment,
                operator=reviewer or "system",
            ))
        except AggregateNotFound as exc:
            raise ValueError(str(getattr(exc, "message", exc)))
        except DomainException as exc:
            raise ValueError(str(getattr(exc, "message", exc)))
        return {"case_id": case_id, "review_status": "approved"}

    def reject_review(self, case_id: str, reviewer: str = "",
                      comment: str = "") -> dict:
        """驳回用例评审：委托 DDD case_app_service.review(outcome='rejected')。"""
        from app.domain.cases.application.case_app_service import case_app_service
        from app.domain.cases.application.dto import ReviewCommand
        from app.domain.common.exceptions import AggregateNotFound
        from app.domain.common.exceptions import DomainException

        try:
            case_app_service.review(ReviewCommand(
                case_id=case_id, outcome="rejected",
                reviewer=reviewer or "", comment=comment,
                operator=reviewer or "system",
            ))
        except AggregateNotFound as exc:
            raise ValueError(str(getattr(exc, "message", exc)))
        except DomainException as exc:
            raise ValueError(str(getattr(exc, "message", exc)))
        return {"case_id": case_id, "review_status": "rejected"}

    def get_reviews(self, case_id: str) -> list:
        """获取用例评审记录（case_reviews 管理表，经 DDD case_app_service）。"""
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.get_reviews(case_id)

    # ── 依赖（委托 DDD case_app_service）────────────────
    def add_dependency(self, case_id: str, depends_on: str,
                       dep_type: str = "before", description: str = "") -> dict:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.add_dependency(case_id, depends_on, dep_type, description)

    def remove_dependency(self, case_id: str, depends_on: str) -> bool:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.remove_dependency(case_id, depends_on)

    def list_dependencies(self, case_id: str) -> list:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.list_dependencies(case_id)

    # ── 回收站（委托 DDD：软删/恢复状态机与不变量由聚合根守护）──
    def soft_delete(self, case_id: str, deleted_by: str = "",
                    reason: str = "") -> bool:
        """软删除：委托 DDD 聚合根 delete()（草稿/评审中/已批准 → 回收站）。

        对不存在或已在回收站的用例返回 False（与既有 trash_case 语义一致），
        由 router 统一映射为 404。
        """
        try:
            from app.domain.cases.application.case_app_service import case_app_service
            from app.domain.cases.application.dto import DeleteCaseCommand
            case_app_service.soft_delete(DeleteCaseCommand(
                case_id=case_id, operator=deleted_by or "system", reason=reason,
            ))
            return True
        except Exception:
            return False

    def restore(self, case_id: str, operator: str = "") -> bool:
        """从回收站恢复：委托 DDD 聚合根 restore()（回收站快照 → 草稿）。"""
        try:
            from app.domain.cases.application.case_app_service import case_app_service
            from app.domain.cases.application.dto import RestoreCaseCommand
            case_app_service.restore(RestoreCaseCommand(
                case_id=case_id, operator=operator or "system",
            ))
            return True
        except Exception:
            return False

    def purge(self, case_id: str) -> bool:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.purge_case(case_id)

    def list_trash(self) -> list:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.list_trash_cases()

    # ── 版本 ──────────────────────────────────────────────
    def list_versions(self, case_id: str) -> list:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.list_versions(case_id)

    def get_version(self, case_id: str, version: int) -> Optional[dict]:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.get_version(case_id, version)

    def rollback(self, case_id: str, version: int, operator: str = "") -> bool:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.rollback(case_id, version, operator)

    def list_changes(self, case_id: str, limit: int = 50) -> list:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.list_changes(case_id, limit)

    def count_changes(self, case_id: str) -> int:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.count_changes(case_id)

    # ── 需求关联 ──────────────────────────────────────────
    def add_requirement(self, case_id: str, requirement_id: str,
                        requirement_type: str = "jira",
                        requirement_title: str = "",
                        requirement_url: str = "") -> dict:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.add_requirement(
            case_id, requirement_id,
            requirement_type=requirement_type,
            requirement_title=requirement_title,
            requirement_url=requirement_url,
        )

    def remove_requirement(self, case_id: str, requirement_id: str) -> bool:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.remove_requirement(case_id, requirement_id)

    def list_requirements(self, case_id: str) -> list:
        from app.domain.cases.application.case_app_service import case_app_service
        return case_app_service.list_requirements(case_id)

    # ── 功能用例模块树 ──────────────────────────────────────
    def build_functional_module_tree(self) -> list:
        """构建功能用例模块树（前端契约）。

        原 routers/cases.py 直接延迟导入 module_store.build_module_tree，
        此处下沉到 service 层，router 只编排不触碰数据模块。

        include_api=False：功能用例模块树只展示功能用例模块（scope=functional），
        不混入接口测试的 api_definitions。否则会把 API 定义作为功能模块树的
        子节点，导致功能用例页面左侧树出现接口类型的节点。
        """
        return apitest_service.build_module_tree(
            "functional", include_api=False,
        )

    # ── 功能用例前端视图格式化 ─────────────────────────────
    def to_functional_case(self, case: dict) -> dict:
        """将后端用例记录转为 TestPilot 前端功能用例格式。

        原 app/routers/cases.py 直接承载，供 case_review_service 复用，
        属 router → service 反向依赖。此处下沉到 service 层，router 与
        case_review_service 统一经 case_service 调用。
        """
        created_at = case.get("created_at", 0) or 0
        updated_at = case.get("updated_at", 0) or 0
        raw_steps = case.get("structured_cases", [])
        if isinstance(raw_steps, str):
            try:
                raw_steps = json.loads(raw_steps)
            except (json.JSONDecodeError, TypeError):
                raw_steps = []
        if not isinstance(raw_steps, list):
            raw_steps = []
        metadata = case.get("metadata") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        _priority = case.get("priority", "P2") or "P2"
        _module_id = case.get("module_id", "") or metadata.get("module_id", "") or "root"
        _module_name = ""
        if _module_id and _module_id != "root":
            try:
                _mod = apitest_service.get_module(_module_id)
                if _mod:
                    _module_name = _mod.get("name", "")
            except Exception:
                _module_name = ""
        _prerequisite = metadata.get("prerequisite", "") or ""
        _case_level_fields = [{
            "fieldId": "functional_priority",
            "fieldName": "用例等级",
            "internal": True,
            "internalFieldKey": "functional_priority",
            "type": "SELECT",
            "required": True,
            "defaultValue": _priority,
            "options": [
                {"value": "P0", "text": "P0", "internal": True, "pos": 1},
                {"value": "P1", "text": "P1", "internal": True, "pos": 2},
                {"value": "P2", "text": "P2", "internal": True, "pos": 3},
                {"value": "P3", "text": "P3", "internal": True, "pos": 4},
            ],
        }]
        return {
            "id": case.get("id", ""),
            "num": case.get("num", 0) or case.get("id", "") or "",
            "name": case.get("title", ""),
            "title": case.get("title", ""),
            "description": case.get("description", ""),
            "priority": case.get("priority", "P2"),
            "status": case.get("status", "draft"),
            "testType": case.get("test_type", "functional") or metadata.get("test_type", "functional"),
            "type": "functional",
            "createTime": int(created_at * 1000),
            "updateTime": int(updated_at * 1000),
            "createUser": "admin",
            "createName": "admin",
            "createUserName": "admin",
            "updateUser": "admin",
            "updateName": "admin",
            "updateUserName": "admin",
            "tags": case.get("tags", []),
            "moduleId": _module_id,
            "modulePath": f"/{_module_name}" if _module_name else "/全部用例",
            "moduleName": _module_name or "全部用例",
            "steps": json.dumps(raw_steps, ensure_ascii=False) if raw_steps else '',
            "deleted": False,
            "projectId": case.get("project_id", "") or metadata.get("project_id", ""),
            "templateId": "",
            "reviewStatus": "UN_REVIEWED",
            "caseEditType": "STEP",
            "prerequisite": _prerequisite,
            "pos": 0,
            "versionId": "",
            "refId": "",
            "lastExecuteResult": "",
            "publicCase": False,
            "latest": True,
            "deleteUser": "",
            "deleteTime": 0,
            "customFields": _case_level_fields,
            "aiCreate": False,
            "versionName": "",
            "caseLevel": None,
            "statusName": case.get("status", "draft"),
            # Detail drawer tab counts - default to 0
            "bugCount": 0,
            "caseCount": 0,
            "caseReviewCount": 0,
            "demandCount": 0,
            "relateEdgeCount": 0,
            "testPlanCount": 0,
            "commentCount": 0,
            "historyCount": 0,
            # 关注状态
            "followFlag": self._functional_case_follow_flag(case.get("id", "")),
            # 附件列表
            "attachments": [],
        }

    def _functional_case_follow_flag(self, case_id: str) -> bool:
        """读取功能用例关注状态（api_follows 落库回读）。

        消灭假成功：此前功能用例详情/列表 followFlag 恒为 False，
        导致前端收藏图标永远显示未关注、跨会话读不回真实状态。
        按 resource_type=functional_case 回读真实关注状态。
        """
        if not case_id:
            return False
        try:
            return bool(apitest_service.is_followed("functional_case", case_id, "admin"))
        except Exception:
            return False

case_service = CaseService()
