# app/services/defect_service.py
"""缺陷业务逻辑层（Phase 3 重构 · 4 层对齐）。

本层是 routers 的唯一业务编排入口。
核心生命周期写路径（create/update/trash/restore/purge）已委托到 defects 域
DDD 应用服务 `defect_app_service`：聚合根 `Defect` 守护标题非空、严重程度合法、
状态机迁移等业务不变量，业务规则单一来源在领域层。此处保留历史方法签名，
仅做薄委托 + 异常翻译 + schema 归一化（读回既有 DefectRepo 归一化行），以兼容
routers/兼容路由及 20+ 处既有调用方、便于回滚。数据访问统一委托
app.repositories.defect_repo.DefectRepo。
"""
import json
from typing import List, Optional

from app.core.exceptions import NotFoundError, ValidationError
from app.repositories.defect_repo import VALID_SEVERITIES, DefectRepo


class DefectService:
    """缺陷管理服务：router 层唯一业务入口。"""

    # ── schema 归一化 ─────────────────────────────────────
    @staticmethod
    def _to_row_schema(item: dict) -> dict:
        """DDD Defect.to_dict → 既有 DefectRepo 行 schema。

        DDD 聚合 to_dict 把 tags 输出为 list；既有 DefectRepo 行/tags 以
        JSON 字符串落库。此处把 tags 字符串化以维持对外返回 schema 不变
        （与 defect_service.get 走 DefectRepo 返回的形态一致）。
        """
        out = dict(item)
        if isinstance(out.get("tags"), list):
            out["tags"] = json.dumps(out["tags"], ensure_ascii=False)
        return out

    # ── 查询 ────────────────────────────────────────────────

    def get(self, defect_id: str) -> Optional[dict]:
        """获取缺陷，不存在返回 None（兼容 tracker.get_defect 语义）。"""
        defect = DefectRepo.get(defect_id)
        if not defect or defect.get("deleted"):
            return None
        return defect

    def get_checked(self, defect_id: str) -> dict:
        """获取缺陷，不存在时抛 404。"""
        defect = DefectRepo.get(defect_id)
        if not defect or defect.get("deleted"):
            raise NotFoundError(f"defect {defect_id} 不存在")
        return defect

    def list(self, status: str = "", severity: str = "", limit: int = 100,
             offset: int = 0) -> tuple:
        """分页查询有效缺陷（委托 DDD）。

        DefectAppService.list → DefectRepoAdapter.list → DefectRepo.list，
        业务数据访问经 DDD 应用门面编排；返回行经 `_to_row_schema` 归一
        为既有 DefectRepo 行结构（tags JSON 字符串化），保证对外 schema 不变。
        """
        from app.domain.defects.application.defect_app_service import (
            defect_app_service,
        )
        from app.domain.defects.application.dto import DefectListQuery

        result = defect_app_service.list(DefectListQuery(
            status=status or "", severity=severity or "",
            limit=int(limit or 100), offset=int(offset or 0),
        ))
        rows = [self._to_row_schema(d) for d in result.get("list", [])]
        return rows, int(result.get("total", 0))

    def get_stats(self) -> dict:
        """获取缺陷统计（委托 DDD `defect_app_service.stats`）。"""
        from app.domain.defects.application.defect_app_service import (
            defect_app_service,
        )

        base = defect_app_service.stats()
        return {
            "total": base.get("total", 0),
            "trash": base.get("trash", 0),
            "by_status": dict(base.get("by_status", {})),
        }

    # ── 变更（委托 DDD 应用服务，聚合根守护业务不变量）─────────
    def create(self, data: dict) -> dict:
        """创建缺陷。

        委托 defects 域 DDD 聚合根：标题非空、严重程度合法、状态值合法等
        不变量在领域层统一守护。返回经既有 DefectRepo 归一化的行记录，
        保持与重构前 DefectRepo.create 的返回 schema 一致。
        """
        from app.domain.defects.application.defect_app_service import (
            defect_app_service,
        )
        from app.domain.defects.application.dto import CreateDefectCommand

        tags = data.get("tags") or []
        if isinstance(tags, str):
            import json as _json
            try:
                tags = _json.loads(tags or "[]")
            except Exception:
                tags = []
        # 兼容既有 create 语义：非法严重程度不静默写脏，落到默认 major
        # （见 DefectRepo.create / bug_add 前端可能透传第三方平台未知严重度）。
        severity = data.get("severity", "major") or "major"
        if severity not in VALID_SEVERITIES:
            severity = "major"
        created = defect_app_service.create(CreateDefectCommand(
            title=data.get("title", ""),
            description=data.get("description", ""),
            severity=severity,
            file_path=data.get("file_path", ""),
            test_case_id=data.get("test_case_id", ""),
            error_snippet=data.get("error_snippet", ""),
            assignee=data.get("assignee", ""),
            tags=list(tags),
            status=data.get("status", "open"),
            operator=str(data.get("operator") or "system"),
        ))
        # 读回归一化记录，保证返回 schema 与既有调用方契约一致
        did = created.get("id", "")
        return DefectRepo.get(did) if did else created

    def update(self, defect_id: str, data: dict) -> Optional[dict]:
        """更新缺陷，校验失败抛 400。

        委托 DDD 聚合根逐字段变更（rename/change_severity/assign/状态机等），
        不存在抛 404、非法值抛 400（保持既有 service 异常语义）。
        """
        from app.domain.common.exceptions import (
            AggregateNotFound,
            DomainValidationError,
            InvariantViolation,
        )
        from app.domain.defects.application.defect_app_service import (
            defect_app_service,
        )
        from app.domain.defects.application.dto import UpdateDefectCommand

        try:
            updated = defect_app_service.update(UpdateDefectCommand(
                defect_id=defect_id,
                title=data.get("title"),
                description=data.get("description"),
                severity=data.get("severity"),
                status=data.get("status"),
                file_path=data.get("file_path"),
                test_case_id=data.get("test_case_id"),
                error_snippet=data.get("error_snippet"),
                assignee=data.get("assignee"),
                tags=list(data.get("tags")) if data.get("tags") is not None else None,
                operator=str(data.get("operator") or "system"),
            ))
        except AggregateNotFound as exc:
            raise NotFoundError(str(exc)) from exc
        except (DomainValidationError, InvariantViolation) as exc:
            raise ValidationError(str(exc)) from exc
        if not updated:
            return None
        return DefectRepo.get(defect_id)

    # ── 回收站（委托 DDD：软删/恢复状态机与不变量由聚合根守护）──
    def trash(self, defect_id: str) -> None:
        """软删除移入回收站（委托 DDD 聚合根 delete()）。

        对不存在或已在回收站的缺陷抛 404。
        """
        from app.domain.common.exceptions import (
            AggregateNotFound,
            DomainValidationError,
        )
        from app.domain.defects.application.defect_app_service import (
            defect_app_service,
        )

        try:
            defect_app_service.soft_delete(defect_id, operator="system")
        except AggregateNotFound as exc:
            raise NotFoundError(str(exc)) from exc
        except DomainValidationError as exc:
            # 已在回收站（重复删除）抛 404 以维持既有路由语义
            raise NotFoundError(str(exc)) from exc

    def restore(self, defect_id: str) -> None:
        """从回收站恢复缺陷（委托 DDD 聚合根 restore()）。

        不在回收站/不存在抛 404。
        """
        from app.domain.common.exceptions import (
            AggregateNotFound,
            DomainValidationError,
        )
        from app.domain.defects.application.defect_app_service import (
            defect_app_service,
        )

        try:
            defect_app_service.restore(defect_id, operator="system")
        except AggregateNotFound as exc:
            raise NotFoundError(str(exc)) from exc
        except DomainValidationError as exc:
            raise NotFoundError(str(exc)) from exc

    def purge(self, defect_id: str) -> None:
        """从回收站彻底删除缺陷（委托 DDD 应用服务）。

        不存在抛 404。
        """
        from app.domain.common.exceptions import AggregateNotFound
        from app.domain.defects.application.defect_app_service import (
            defect_app_service,
        )

        try:
            defect_app_service.purge(defect_id)
        except AggregateNotFound as exc:
            raise NotFoundError(str(exc)) from exc

    def list_trash(self, limit: int = 100, offset: int = 0) -> tuple:
        """列出回收站缺陷及其总数（委托 DDD）。

        返回行 schema 经 `_to_row_schema` 归一（tags 字符串化），
        与既有 DefectRepo.list_trash 行结构一致。
        """
        from app.domain.defects.application.defect_app_service import (
            defect_app_service,
        )

        result = defect_app_service.list_trash(
            limit=int(limit or 100), offset=int(offset or 0))
        rows = [self._to_row_schema(d) for d in result.get("list", [])]
        return rows, int(result.get("total", 0))

    def batch_restore(self, ids: List[str]) -> int:
        """批量从回收站恢复缺陷（逐条委托 DDD restore），返回成功数。"""
        restored = 0
        for did in ids:
            try:
                self.restore(did)
                restored += 1
            except NotFoundError:
                continue
        return restored

    def batch_purge(self, ids: List[str]) -> int:
        """批量从回收站彻底删除缺陷（逐条委托 DDD purge），返回成功数。"""
        purged = 0
        for did in ids:
            try:
                self.purge(did)
                purged += 1
            except NotFoundError:
                continue
        return purged

    def permanent_delete(self, defect_id: str) -> None:
        """彻底删除缺陷（非回收站路径，委托 DDD 门面）。

        直删存储行、绕过回收站流；不存在抛 404。
        """
        from app.domain.common.exceptions import AggregateNotFound
        from app.domain.defects.application.defect_app_service import (
            defect_app_service,
        )
        from app.domain.defects.application.dto import PermanentDeleteCommand

        try:
            defect_app_service.permanent_delete(PermanentDeleteCommand(
                defect_id=defect_id,
            ))
        except AggregateNotFound as exc:
            raise NotFoundError(str(exc)) from exc


    # ── 评论（评论走 DDD 门面，经缺陷域协调既有评论存储）──────────
    def list_comments(self, bug_id: str) -> List[dict]:
        """获取缺陷评论列表（委托 DDD `defect_app_service`）。"""
        from app.domain.defects.application.defect_app_service import (
            defect_app_service,
        )
        from app.domain.defects.application.dto import ListCommentsQuery

        return defect_app_service.list_comments(ListCommentsQuery(bug_id=bug_id))

    def create_comment(self, bug_id: str, content: str = "", parent_id: str = "",
                       create_user: str = "", reply_user: str = "",
                       notifier: str = "") -> Optional[dict]:
        """创建缺陷评论（委托 DDD `defect_app_service`）。"""
        from app.domain.defects.application.defect_app_service import (
            defect_app_service,
        )
        from app.domain.defects.application.dto import CreateCommentCommand

        return defect_app_service.create_comment(CreateCommentCommand(
            bug_id=bug_id, content=content, parent_id=parent_id,
            create_user=create_user, reply_user=reply_user, notifier=notifier,
        ))

    def update_comment(self, comment_id: str, content: str) -> Optional[dict]:
        """更新缺陷评论，不存在返回 None（委托 DDD 门面）。"""
        from app.domain.defects.application.defect_app_service import (
            defect_app_service,
        )
        from app.domain.defects.application.dto import UpdateCommentCommand

        return defect_app_service.update_comment(
            UpdateCommentCommand(comment_id=comment_id, content=content))

    def delete_comment(self, comment_id: str) -> bool:
        """删除缺陷评论（软删除并级联删除子评论，委托 DDD 门面）。"""
        from app.domain.defects.application.defect_app_service import (
            defect_app_service,
        )
        from app.domain.defects.application.dto import DeleteCommentCommand

        return defect_app_service.delete_comment(
            DeleteCommentCommand(comment_id=comment_id))

    def list_trashed(self, limit: int = 9999, offset: int = 0) -> List[dict]:
        """列出回收站全部缺陷（委托 DDD，schema 与 DefectRepo 行对齐）。"""
        items, _ = self.list_trash(limit=limit, offset=offset)
        return items

    def count_trashed(self) -> int:
        """统计回收站缺陷数量（委托 DDD）。"""
        from app.domain.defects.application.defect_app_service import (
            defect_app_service,
        )

        result = defect_app_service.list_trash(limit=1, offset=0)
        return int(result.get("total", 0))


    def auto_create_from_result(self, file_path: str, test_result: dict,
                                test_case_id: str = "") -> Optional[dict]:
        """测试失败时自动创建缺陷（委托 DDD `defect_app_service`）。"""
        from app.domain.defects.application.defect_app_service import (
            defect_app_service,
        )
        from app.domain.defects.application.dto import AutoCreateFromResultCommand

        return defect_app_service.auto_create_from_result(
            AutoCreateFromResultCommand(
                file_path=file_path, test_result=test_result,
                test_case_id=test_case_id,
            ))


defect_service = DefectService()
