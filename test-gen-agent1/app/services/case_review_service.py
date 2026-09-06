"""用例评审（case_review）域业务逻辑层（Service 层覆盖补齐 · 业务域缺口）。

承接用例评审域的数据访问与业务编排，作为 router 层唯一业务入口
（旧 app.cases.review_store / review_module_store 兼容门面已删除）。

职责：
  - 业务编排（创建/编辑/复制/删除评审、关联/取消关联用例、关注、批量评审）；
  - 前端视图格式化（_review_view_item / _review_detail / _case_review_item /
    _build_review_detail_module_tree 收敛到本 Service，router 不再持有复杂
    展示逻辑）；
  - 数据访问统一委托 app.repositories.case_review_repo.CaseReviewRepo，
    评审模块经由 app.apitest.module_store（scope=case_review）。

Router → Service → Repository → DB 四层架构。
"""
import json
import time
from typing import Any, Dict, List, Optional

# 迁移三步 · 阶段 B/C：让既有调用链真正消费 DDD 应用服务（DTO 契约桥翻译，
# 对外返回 schema 与迁移前一致，实现零回归渐进式接入）。
from app.domain.case_review.application.case_review_app_service import (
    case_review_app_service,
)
from app.domain.case_review.application.dto import (
    CaseReviewListQuery,
    CopyReviewCommand,
    CreateReviewCommand,
    DeleteReviewCommand,
    LinkCasesCommand,
    ToggleFollowCommand,
    UnlinkCasesCommand,
    UpdateLinkResultCommand,
    UpdateReviewCommand,
)
from app.domain.case_review.application.web_dto import to_header_dict
from app.repositories.case_review_repo import (
    RESULT_PASS,
    RESULT_RE_REVIEWED,
    RESULT_UN_PASS,
    RESULT_UN_REVIEWED,
    RESULT_UNDER_REVIEWED,
    STATUS_COMPLETED,
    STATUS_PREPARED,
    STATUS_UNDERWAY,
    CaseReviewRepo,
)
from app.services.case_service import case_service


class CaseReviewService:
    """用例评审服务：router 层唯一业务入口。"""

    # ═══════════════════════════════════════════════════════
    # 状态常量（透传）
    # ═══════════════════════════════════════════════════════
    STATUS_PREPARED = STATUS_PREPARED
    STATUS_UNDERWAY = STATUS_UNDERWAY
    STATUS_COMPLETED = STATUS_COMPLETED
    RESULT_UN_REVIEWED = RESULT_UN_REVIEWED
    RESULT_UNDER_REVIEWED = RESULT_UNDER_REVIEWED
    RESULT_PASS = RESULT_PASS
    RESULT_UN_PASS = RESULT_UN_PASS
    RESULT_RE_REVIEWED = RESULT_RE_REVIEWED

    # ═══════════════════════════════════════════════════════
    # 内部辅助：评审人提取 / 用例模块提取 / 模块名查找
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _reviewers_of(header: dict) -> list:
        """从评审头提取前端 reviewers 数组。"""
        raw = header.get("reviewers_json") or []
        result = []
        for r in raw:
            if isinstance(r, dict):
                uid = r.get("userId", "")
                uname = r.get("userName", "") or uid
                result.append({"userId": uid, "userName": uname})
            else:
                result.append({"userId": str(r), "userName": str(r)})
        if not result:
            result = [{"userId": "admin", "userName": "admin"}]
        return result

    @staticmethod
    def _case_module_id(c: dict) -> str:
        """从用例记录中提取 module_id。"""
        meta = c.get("metadata", {}) or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except (json.JSONDecodeError, TypeError):
                meta = {}
        return meta.get("module_id", "") or c.get("module_id", "") or "root"

    @staticmethod
    def _module_name_of(module_id: str) -> str:
        """根据模块 ID 查找模块名称。"""
        if not module_id or module_id == "root":
            return ""
        try:
            from app.apitest import module_store as ms
            m = ms.get_module(module_id)
            if m:
                return m.get("name", "")
        except Exception:
            pass
        return ""

    # ═══════════════════════════════════════════════════════
    # 前端视图格式化
    # ═══════════════════════════════════════════════════════

    def _review_view_item(self, h: dict) -> dict:
        """评审头 -> 前端 ReviewItem 列表项。"""
        status = h.get("status", STATUS_UNDERWAY)
        counts = case_review_app_service.get_status_counts(h.get("id", ""))
        case_count = len(case_review_app_service.list_links(h.get("id", "")))
        create_time = int((h.get("create_time") or time.time()) * 1000)
        update_time = int((h.get("update_time") or time.time()) * 1000)
        return {
            "id": h.get("id", ""),
            "name": h.get("name", ""),
            "num": h.get("num", 1),
            "moduleId": h.get("module_id", "root"),
            "projectId": h.get("project_id", ""),
            "status": status,
            "reviewPassRule": h.get("review_pass_rule", "SINGLE"),
            "pos": h.get("pos", 0),
            "startTime": int((h.get("start_time") or 0) * 1000),
            "endTime": int((h.get("end_time") or 0) * 1000) if h.get("end_time") else None,
            "createUser": h.get("create_user", "admin"),
            "createUserName": h.get("create_user", "admin"),
            "createTime": create_time,
            "updateTime": update_time,
            "updateUser": h.get("update_user", "admin"),
            "description": h.get("description", ""),
            "tags": h.get("tags", []),
            "caseCount": case_count,
            "passRate": round(counts["passCount"] / case_count * 100, 1) if case_count else 0,
            "reviewers": self._reviewers_of(h),
            "passCount": counts["passCount"],
            "unPassCount": counts["unPassCount"],
            "reReviewedCount": counts["reReviewedCount"],
            "underReviewedCount": counts["underReviewedCount"],
            "unReviewCount": counts["unReviewCount"],
            "reviewedCount": counts["reviewedCount"],
            "followFlag": False,
        }

    def review_detail(self, h: dict) -> dict:
        """评审头 -> 前端 ReviewItem 完整详情。"""
        return self._review_view_item(h)

    def _case_review_item(self, link: dict, review_id: str,
                          current_user_id: str = "") -> dict:
        """将评审-用例关联记录转为前端 ReviewCaseItem。"""
        c = case_service.get(link.get("case_id", "")) or {}
        if not c:
            # 用例已被彻底删除，仅返回基础信息
            return {
                "id": link.get("case_id", ""),
                "caseId": link.get("case_id", ""),
                "reviewId": review_id,
                "name": "",
                "num": "",
                "versionId": "",
                "versionName": "",
                "reviewers": [],
                "reviewNames": [],
                "status": link.get("status", RESULT_UN_REVIEWED),
                "myStatus": link.get("status", RESULT_UN_REVIEWED),
                "moduleId": "root",
                "moduleName": "",
                "customFields": [],
                "caseLevel": "P2",
                "createUser": "admin",
                "createUserName": "admin",
                "createTime": int((link.get("create_time") or 0) * 1000),
                "deleted": True,
                "caseEditType": "",
                "steps": "",
                "priority": "P2",
            }
        # 先复用 case_service.to_functional_case 获取完整功能用例字段
        fc = case_service.to_functional_case(c)
        reviewer = link.get("reviewer", "") or ""
        reviewers_list = [reviewer] if reviewer else []
        review_names = reviewers_list
        if reviewer:
            # 尝试将 userId 解析为用户名
            try:
                users = self.list_review_users()
                for u in users:
                    if str(u.get("id", "")) == reviewer:
                        review_names = [u.get("name", reviewer)]
                        break
            except Exception:
                pass
        mod_id = self._case_module_id(c)
        mod_name = self._module_name_of(mod_id)
        return {
            **fc,
            "id": link.get("case_id", ""),
            "caseId": link.get("case_id", ""),
            "reviewId": review_id,
            "versionId": fc.get("versionId", "") or "",
            "versionName": fc.get("versionName", "") or "",
            "reviewers": reviewers_list,
            "reviewNames": review_names,
            "status": link.get("status", RESULT_UN_REVIEWED),
            "myStatus": (link.get("status", RESULT_UN_REVIEWED)
                         if not current_user_id or reviewer == current_user_id
                         else RESULT_UN_REVIEWED),
            "moduleId": mod_id,
            "moduleName": mod_name or "全部用例",
            "caseLevel": fc.get("priority", "P2"),
            "priority": fc.get("priority", "P2"),
        }

    # ═══════════════════════════════════════════════════════
    # 评审头 CRUD
    # ═══════════════════════════════════════════════════════

    def list_reviews(self, keyword: str = "", project_id: str = "",
                     page_size: int = 10, current: int = 1) -> dict:
        """分页获取评审列表（含前端格式化，经 DDD 门面）。"""
        result = case_review_app_service.list_reviews(CaseReviewListQuery(
            keyword=keyword, project_id=project_id,
            limit=page_size, offset=(current - 1) * page_size,
        ))
        headers = [to_header_dict(v) for v in result.get("list", [])]
        return {
            "list": [self._review_view_item(h) for h in headers],
            "total": result.get("total", 0),
            "pageSize": page_size,
            "current": current,
        }

    def get_review(self, review_id: str) -> Optional[Dict[str, Any]]:
        """获取评审头原始记录（经 DDD 门面 → 契约桥）。"""
        if not review_id:
            return None
        agg = case_review_app_service.get(review_id)
        return to_header_dict(agg) if agg else None

    def get_review_detail(self, review_id: str) -> Optional[Dict[str, Any]]:
        """获取评审头（已格式化为前端详情，经 DDD 门面）。"""
        if not review_id:
            return None
        agg = case_review_app_service.get_detail(review_id)
        header = to_header_dict(agg) if agg else None
        return self._review_view_item(header) if header else None

    def create_review(self, name: str, description: str = "",
                      project_id: str = "", module_id: str = "root",
                      status: str = STATUS_UNDERWAY,
                      review_pass_rule: str = "SINGLE",
                      reviewers: list = None, create_user: str = "admin",
                      tags: list = None, start_time: float = 0,
                      end_time: float = 0) -> Dict[str, Any]:
        """创建评审头。

        迁移三步 · 阶段 B/C：经 DDD 应用服务创建（聚合守护名称/状态不变量），
        通过 DTO 桥翻译回 Repo header 契约，对外行为与迁移前一致。
        """
        agg = case_review_app_service.create(CreateReviewCommand(
            name=name, description=description, project_id=project_id,
            module_id=module_id, status=status,
            review_pass_rule=review_pass_rule,
            reviewers=reviewers or [], tags=tags or [],
            start_time=float(start_time or 0), end_time=float(end_time or 0),
            operator=create_user or "admin",
        ))
        return to_header_dict(agg)

    def update_review(self, review_id: str,
                      fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新评审头。

        迁移三步 · 阶段 B/C：名称/描述/模块/项目/状态/通过规则/评审人/标签/时间等
        归属 DDD 聚合不变量管控的字段经应用服务更新（守护状态机）；`pos`（纯排序
        字段，不在聚合不变量内）仍走 Repo 直更，避免回归。
        """
        if not review_id:
            return None
        pos = fields.get("pos")
        # 过滤掉 pos 后交由 DDD 聚合更新
        ddd_fields = {k: v for k, v in fields.items() if k != "pos"}
        if ddd_fields:
            cmd = UpdateReviewCommand(review_id=review_id)
            if ddd_fields.get("name") is not None:
                cmd.name = ddd_fields["name"]
            if ddd_fields.get("description") is not None:
                cmd.description = ddd_fields["description"]
            if ddd_fields.get("module_id") is not None:
                cmd.module_id = ddd_fields["module_id"]
            if ddd_fields.get("project_id") is not None:
                cmd.project_id = ddd_fields["project_id"]
            if ddd_fields.get("status") is not None:
                cmd.status = ddd_fields["status"]
            if ddd_fields.get("review_pass_rule") is not None:
                cmd.review_pass_rule = ddd_fields["review_pass_rule"]
            if ddd_fields.get("reviewers") is not None:
                cmd.reviewers = ddd_fields["reviewers"]
            if ddd_fields.get("tags") is not None:
                cmd.tags = ddd_fields["tags"]
            if ddd_fields.get("start_time") is not None or ddd_fields.get("end_time") is not None:
                cmd.start_time = ddd_fields.get("start_time")
                cmd.end_time = ddd_fields.get("end_time")
            agg = case_review_app_service.update(cmd)
            if agg is None:
                return None
            header = to_header_dict(agg)
        else:
            header = CaseReviewRepo.get_review(review_id)
            if header is None:
                return None
        if pos is not None:
            CaseReviewRepo.update_review(review_id, {"pos": int(pos)})
            header = CaseReviewRepo.get_review(review_id) or header
        return header

    def delete_review(self, review_id: str) -> bool:
        """软删除评审。

        迁移三步 · 阶段 B/C：经 DDD 聚合软删（守护"重复删除拒绝"不变量）。
        """
        if not review_id:
            return False
        return case_review_app_service.soft_delete(
            DeleteReviewCommand(review_id=review_id))

    def copy_review(self, source_id: str, new_name: str = "") -> Optional[Dict[str, Any]]:
        """复制评审。

        迁移三步 · 阶段 B/C：经 DDD 应用服务复制（含关联用例与评审人）。
        """
        if not source_id:
            return None
        agg = case_review_app_service.copy(
            CopyReviewCommand(source_id=source_id, new_name=new_name or ""))
        return to_header_dict(agg) if agg else None

    # ═══════════════════════════════════════════════════════
    # 评审-用例关联
    # ═══════════════════════════════════════════════════════

    def list_links(self, review_id: str) -> List[Dict[str, Any]]:
        """列出评审关联的用例记录（原始 link，经 DDD 门面）。"""
        return case_review_app_service.list_links(review_id)

    def list_link_case_ids(self, review_id: str) -> set:
        """列出评审已关联用例 id 集合（经 DDD 门面）。"""
        return case_review_app_service.list_link_case_ids(review_id)

    def link_cases(self, review_id: str, case_ids: list) -> int:
        """批量关联用例到评审。

        迁移三步 · 阶段 B/C：经 DDD 聚合关联（守护去重与"已删除不可关联"）。
        返回实际新增数量。
        """
        if not review_id or not case_ids:
            return 0
        before = case_review_app_service.list_link_case_ids(review_id)
        case_review_app_service.link_cases(LinkCasesCommand(
            review_id=review_id, case_ids=list(case_ids)))
        after = case_review_app_service.list_link_case_ids(review_id)
        return len(after - before)

    def unlink_cases(self, review_id: str, case_ids: list) -> int:
        """批量解除用例关联。

        迁移三步 · 阶段 B/C：经 DDD 聚合解除关联。返回实际移除数量。
        """
        if not review_id or not case_ids:
            return 0
        before = case_review_app_service.list_link_case_ids(review_id)
        case_review_app_service.unlink_cases(UnlinkCasesCommand(
            review_id=review_id, case_ids=list(case_ids)))
        after = case_review_app_service.list_link_case_ids(review_id)
        return len(before - after)

    def get_case_status_counts(self, review_id: str) -> Dict[str, int]:
        """评审下用例状态汇总计数（经 DDD 门面）。"""
        return case_review_app_service.get_status_counts(review_id)

    def update_link_status(self, review_id: str, case_ids: list, status: str,
                           reviewer: str = "", comment: str = "") -> int:
        """批量更新评审-用例状态。

        迁移三步 · 阶段 B/C：经 DDD 聚合批量更新评审结论（守护"未关联用例不可
        评审"与结论值合法性）。
        """
        if not review_id or not case_ids:
            return 0
        res = case_review_app_service.update_link_result(UpdateLinkResultCommand(
            review_id=review_id, case_ids=list(case_ids), status=status or "UNDER_REVIEWED",
            reviewer=reviewer or "", comment=comment or "",
        ))
        return int(res.get("updated", 0))


    def _save_reviewers(self, review_id: str, reviewers: list) -> None:
        """将评审人数组写入 reviewers_json 列。"""
        CaseReviewRepo._save_reviewers(review_id, reviewers)

    def count_reviews(self, keyword: str = "", project_id: str = "",
                      status: str = "") -> int:
        """统计评审数量（经 DDD 门面 total）。"""
        result = case_review_app_service.list_reviews(CaseReviewListQuery(
            keyword=keyword, project_id=project_id, status=status, limit=1,
        ))
        return int(result.get("total", 0))

    def get_review_case_status(self, review_id: str) -> Dict[str, int]:
        """评审下用例状态汇总计数（经 DDD 门面）。"""
        return case_review_app_service.get_status_counts(review_id)


    # ═══════════════════════════════════════════════════════
    # 关注
    # ═══════════════════════════════════════════════════════

    def toggle_follow(self, review_id: str, user_id: str) -> bool:
        """关注/取消关注评审（经 DDD 门面）。"""
        return case_review_app_service.toggle_follow(
            ToggleFollowCommand(review_id=review_id, user_id=user_id))

    def is_following(self, review_id: str, user_id: str) -> bool:
        """是否已关注（经 DDD 门面）。"""
        return case_review_app_service.is_following(review_id, user_id)

    # ═══════════════════════════════════════════════════════
    # 评审人下拉
    # ═══════════════════════════════════════════════════════

    def list_review_users(self, project_id: str = "", keyword: str = "") -> List[Dict[str, Any]]:
        """获取评审人员选项列表（组织成员 + 项目成员，其次全部用户）。

        评审人选项：项目成员优先，其次组织成员，再全部用户。
        """
        from app.services.organization_service import organization_service
        from app.services.project_service import project_service

        users: Dict[str, Dict[str, Any]] = {}
        try:
            if project_id:
                members = project_service.list_members(project_id, keyword)
                for m in members:
                    uid = str(m.get("user_id", "") or "")
                    if not uid:
                        continue
                    users.setdefault(uid, {
                        "id": uid,
                        "name": m.get("name") or m.get("username") or uid,
                        "email": m.get("email", ""),
                    })
        except Exception:
            pass
        try:
            org_members = organization_service.list_members(
                "default-org", search=keyword, limit=500)
            for m in org_members:
                uid = str(m.get("user_id", "") or "")
                if not uid:
                    continue
                users.setdefault(uid, {
                    "id": uid,
                    "name": m.get("name") or m.get("username") or uid,
                    "email": m.get("email", ""),
                })
        except Exception:
            pass
        if not users:
            try:
                from app.auth.store import AuthStore
                for u in AuthStore().list_users():
                    if keyword and keyword.lower() not in (
                        u.get("username", "") + u.get("name", "")).lower():
                        continue
                    users.setdefault(str(u.get("id", "")), {
                        "id": str(u.get("id", "")),
                        "name": u.get("name") or u.get("username", ""),
                        "email": u.get("email", ""),
                    })
            except Exception:
                pass
        result = []
        for u in users.values():
            result.append({
                "id": u["id"],
                "name": u["name"],
                "email": u.get("email", ""),
            })
        return result

    # ═══════════════════════════════════════════════════════
    # 评审详情辅助
    # ═══════════════════════════════════════════════════════

    def build_review_detail_module_tree(self, review_id: str) -> list:
        """构建评审详情已关联用例的模块树。"""
        if not review_id:
            return []
        links = case_review_app_service.list_links(review_id)
        case_mods: dict = {}
        module_counts: dict = {"root": 0}
        for link in links:
            c = case_service.get(link.get("case_id", "")) or {}
            if not c:
                continue
            mod_id = self._case_module_id(c)
            case_mods[link.get("case_id", "")] = mod_id
            module_counts[mod_id] = module_counts.get(mod_id, 0) + 1

        # 加载 functional scope 模块结构
        try:
            from app.apitest import module_store as ms
            modules = ms.list_modules("functional", "")
        except Exception:
            modules = []

        module_map: dict = {}
        for m in modules:
            mid = m["id"]
            module_map[mid] = {
                "id": mid,
                "name": m.get("name", ""),
                "type": "MODULE",
                "parentId": m.get("parent_id", "root"),
                "children": [],
                "count": module_counts.get(mid, 0),
                "pos": m.get("pos", 0),
            }

        # 组装层级
        children_map: dict = {}
        for _mid, node in module_map.items():
            parent = node["parentId"]
            if parent in module_map:
                children_map.setdefault(parent, []).append(node)
            elif parent == "root":
                children_map.setdefault("root", []).append(node)

        # 递归累计子模块用例数到父模块
        def _accumulate(node: dict) -> int:
            total = node.get("count", 0)
            for child in children_map.get(node["id"], []):
                total += _accumulate(child)
            node["count"] = total
            return total

        top_children = []
        for node in children_map.get("root", []):
            if _accumulate(node) > 0:
                top_children.append(node)

        root = {
            "id": "root",
            "name": "全部用例",
            "type": "MODULE",
            "parentId": "",
            "children": top_children,
            "count": len(links),
            "pos": 0,
        }
        return [root]

    # ═══════════════════════════════════════════════════════
    # 评审模块管理（经 app.apitest.module_store，scope=case_review）
    # ═══════════════════════════════════════════════════════

    REVIEW_MODULE_SCOPE = "case_review"

    @staticmethod
    def _module_node(mod: dict) -> dict:
        """模块行 -> 前端 Module 树节点。"""
        return {
            "id": mod.get("id", ""),
            "name": mod.get("name", ""),
            "type": "MODULE",
            "parentId": mod.get("parent_id", "root"),
            "children": [],
            "count": 0,
        }

    def _review_count_by_module(self, project_id: str = "") -> dict:
        """每个评审模块下（直接归属）非删除评审数量（经 DDD 门面）。"""
        return case_review_app_service.count_by_module(project_id)

    def build_review_module_tree(self, project_id: str = "") -> list:
        """构建评审模块树（root「全部评审」+ 已持久化的子模块）。

        文件夹 count 为其自身 + 所有子孙模块下的评审数量合计。
        """
        from app.apitest import module_store as ms
        modules = ms.list_modules(self.REVIEW_MODULE_SCOPE, project_id)
        direct = self._review_count_by_module(project_id)  # 每 module 直接归属评审数

        nodes: dict = {}
        for m in modules:
            mid = m["id"]
            nodes[mid] = {
                "id": mid,
                "name": m["name"],
                "type": "MODULE",
                "parentId": m.get("parent_id", "root"),
                "children": [],
                "count": 0,
            }

        # 组装层级（按 parent_id），孤立节点（父已被删除）提升为 root 顶级模块
        for _mid, node in nodes.items():
            parent = node["parentId"]
            if parent in nodes:
                nodes[parent]["children"].append(node)
            elif parent != "root":
                node["parentId"] = "root"

        # 深度优先后序遍历累计 count（含子孙）
        def _accumulate(node_id: str) -> int:
            node = nodes.get(node_id)
            if node is None:
                return direct.get(node_id, 0)
            total = direct.get(node_id, 0)
            for child in node["children"]:
                total += _accumulate(child["id"])
            node["count"] = total
            return total

        children = [n for n in nodes.values() if n["parentId"] == "root"]
        for node in children:
            _accumulate(node["id"])

        total = case_review_app_service.list_reviews(CaseReviewListQuery(
            project_id=project_id, limit=1)).get("total", 0)
        root = {
            "id": "root",
            "name": "全部评审",
            "type": "MODULE",
            "parentId": "",
            "children": children,
            "count": total,
        }
        return [root]

    def add_review_module(self, name: str, project_id: str = "",
                          parent_id: str = "root") -> dict:
        """新增评审模块并落库。"""
        from app.apitest import module_store as ms
        mod = ms.add_module(self.REVIEW_MODULE_SCOPE, name,
                            parent_id or "root", project_id)
        return self._module_node(mod)

    def update_review_module(self, module_id: str, name: str) -> bool:
        """更新评审模块名称。"""
        from app.apitest import module_store as ms
        return ms.update_module(module_id, name)

    def delete_review_module(self, module_id: str) -> bool:
        """删除评审模块（含其下子模块）。"""
        from app.apitest import module_store as ms
        return ms.delete_module(module_id)

    def move_review_module(self, drag_id: str, drop_id: str,
                           drop_position: int = 0) -> bool:
        """移动评审模块。"""
        from app.apitest import module_store as ms
        return ms.move_module(drag_id, drop_id, int(drop_position or 0))

    def review_count_by_module(self, project_id: str = "") -> dict:
        """模块下评审数量统计。"""
        return self._review_count_by_module(project_id)


# 模块级单例
case_review_service = CaseReviewService()


__all__ = ["case_review_service", "CaseReviewService"]
