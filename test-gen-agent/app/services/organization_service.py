# app/services/organization_service.py
"""组织（租户）业务逻辑层（Phase 4 · DDD A→B→C 渐进迁移 — 阶段 C 收敛）。

本层是 routers 的组织域业务入口，同时也是组织-项目关联 / 租户种子初始化
跨域编排的**兼容门面**。按 §五「渐进式、可回滚」方案推进，本 Service 的
**核心生命周期与成员管理**（create / get / list / rename / enable / disable /
add_member / update_member / remove_member）已收敛为对 DDD 应用门面
`identity_app_service` 的薄委托：

    Router → organization_service(薄门面) → IdentityAppService → RepoAdapter → Repo

写操作经 DDD 聚合守护业务不变量（组织名称非空、owner 越权守卫、账号状态机），
返回经既有 OrganizationRepo 读回归一化，保证旁路 / compat router 的对外
schema 与迁移前零变化。

> 仍保留直连 OrganizationRepo 的**兼容方法**（双轨过渡，逐域收敛后再移除）：
>   - `list_members` / `get_member` / `count_members`：成员列表/详情/计数查询。
>   - `list_orgs_by_user` / `list_orgs_by_users`：组织反查（DDD 聚合未覆盖）。
>   - `list_projects` / `bind_project`：组织-项目关联（跨域，非本域核心聚合）。
>   - `seed_tenant_data` / `tenant_summary`：租户初始化 / 摘要编排。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from app.domain.common.exceptions import (
    AggregateNotFound,
    DomainValidationError,
    InvariantViolation,
)
from app.domain.identity.application.delegation import guard_org_remove_member
from app.domain.identity.application.dto import (
    AddMemberCommand,
    ChangeMemberRoleCommand,
    CreateOrganizationCommand,
    OrganizationListQuery,
    UpdateOrganizationCommand,
)
from app.domain.identity.application.identity_app_service import (
    identity_app_service as _ddd_identity,
)
from app.domain.identity.application.web_schema import org_to_web_row
from app.logging_config import get_logger
from app.repositories.organization_repo import OrganizationRepo


class OrganizationService:
    """组织（租户）服务（核心生命周期委托 DDD 应用门面）。"""

    # ── 组织 CRUD（委托 DDD）────────────────────────────
    def create(self, name: str, description: str = "",
               create_user: str = "admin") -> dict:
        """创建组织（委托 DDD：名称非空由领域聚合守护）。"""
        try:
            created = _ddd_identity.create_organization(CreateOrganizationCommand(
                name=name, description=description,
                create_user=create_user,
            ))
        except (DomainValidationError, ValueError) as exc:
            raise ValueError(str(exc)) from exc
        # 读回归一化记录（含 memberCount 等既有字段）
        oid = created.get("id", "")
        return OrganizationRepo.get(oid) if oid else created

    def get(self, oid: str) -> Optional[dict]:
        """获取组织（委托 DDD；不存在返回 None，兼容既有语义）。"""
        try:
            org = _ddd_identity.get_organization(oid)
        except AggregateNotFound:
            return None
        if not org:
            return None
        # 读回归一化（含 memberCount）
        return OrganizationRepo.get(oid) or org_to_web_row(org)

    def get_by_name(self, name: str) -> Optional[dict]:
        """按名称获取组织（委托 DDD identity_app_service）。"""
        try:
            return _ddd_identity.get_organization_by_name(name)
        except Exception:
            return OrganizationRepo.get_by_name(name)

    def list(self, search: str = "", status: str = "",
             limit: int = 100, offset: int = 0) -> List[dict]:
        """列出组织（委托 DDD；返回既有仓库行口径列表）。"""
        try:
            result = _ddd_identity.list_organizations(OrganizationListQuery(
                search=search or "", status=status or "",
                limit=int(limit or 100), offset=int(offset or 0),
            ))
        except Exception:
            # 兜底直连 Repo（保证路由可用性）
            return OrganizationRepo.list(search=search, status=status,
                                          limit=limit, offset=offset)
        # 从 DDD 输出读回 Repo 格式（含 memberCount）
        ddd_list = result.get("list", [])
        out: List[dict] = []
        for org in ddd_list:
            oid = org.get("id", "")
            row = OrganizationRepo.get(oid) if oid else None
            if row:
                out.append(row)
            else:
                web = org_to_web_row(org)
                if web:
                    out.append(web)
        return out

    def count(self, search: str = "") -> int:
        """统计组织数（委托 DDD）。"""
        return _ddd_identity.count_organizations(search=search)

    def update(self, oid: str, data: Optional[dict] = None,
               **kwargs) -> Optional[dict]:
        """更新组织信息（委托 DDD，兼容 data dict 或 **kwargs 两种入参）。"""
        updates = dict(data) if data is not None else dict(kwargs)
        name = updates.pop("name", None)
        description = updates.pop("description", None)
        # 剩余字段（status 等）暂不走 DDD，直接落库
        if updates:
            OrganizationRepo.update(oid, updates)
        if name is not None or description is not None:
            try:
                _ddd_identity.update_organization(UpdateOrganizationCommand(
                    org_id=oid, name=name, description=description,
                ))
            except AggregateNotFound:
                return None
        return OrganizationRepo.get(oid)

    def rename(self, oid: str, name: str) -> Optional[dict]:
        """组织改名（委托 DDD：非空校验由领域聚合守护）。"""
        try:
            _ddd_identity.update_organization(UpdateOrganizationCommand(
                org_id=oid, name=name,
            ))
        except (DomainValidationError, AggregateNotFound) as exc:
            get_logger(__name__).warning("组织改名被领域规则拦截: %s", exc)
            return None
        return OrganizationRepo.get(oid)

    def delete(self, oid: str, hard: bool = False) -> bool:
        """删除组织（委托 DDD）。"""
        return _ddd_identity.delete_organization(oid, hard=hard)

    def recover(self, oid: str) -> bool:
        """恢复组织（委托 DDD）。"""
        return _ddd_identity.recover_organization(oid)

    def enable(self, oid: str) -> bool:
        """启用组织（委托 DDD 状态机）。"""
        try:
            _ddd_identity.set_organization_enabled(oid, True, operator="system")
        except (AggregateNotFound, DomainValidationError, InvariantViolation) as exc:
            get_logger(__name__).warning("启用组织被领域规则拦截: %s", exc)
            return False
        return True

    def disable(self, oid: str) -> bool:
        """停用组织（委托 DDD 状态机）。"""
        try:
            _ddd_identity.set_organization_enabled(oid, False, operator="system")
        except (AggregateNotFound, DomainValidationError, InvariantViolation) as exc:
            get_logger(__name__).warning("停用组织被领域规则拦截: %s", exc)
            return False
        return True

    # ── 组织成员管理（核心成员增删改委托 DDD）────────────
    def list_members(self, org_id: str, search: str = "",
                     limit: int = 100) -> List[dict]:
        """列出组织成员（委托 DDD）。"""
        return _ddd_identity.list_members(org_id, search=search, limit=limit)

    def get_member(self, member_id: str) -> Optional[dict]:
        """获取组织成员（委托 DDD）。"""
        return _ddd_identity.get_member(member_id)

    def add_member(self, org_id: str, user_id: str,
                   role: str = "member") -> Optional[dict]:
        """添加组织成员（委托 DDD：角色合法性 / owner 守护）。"""
        try:
            _ddd_identity.add_member(AddMemberCommand(
                org_id=org_id, user_id=user_id, role=role or "member",
            ))
        except (AggregateNotFound, DomainValidationError, InvariantViolation) as exc:
            get_logger(__name__).warning("添加组织成员失败: %s", exc)
            return None
        # 读回新成员
        members = OrganizationRepo.list_members(org_id, limit=1000)
        for m in members:
            if m.get("user_id") == user_id:
                return m
        return None

    def update_member(self, org_id: str, user_id: str,
                      role: Optional[str] = None) -> Optional[dict]:
        """更新成员角色（委托 DDD：owner 越权守卫）。"""
        if role is None:
            return OrganizationRepo.update_member(org_id, user_id, role=None)
        try:
            _ddd_identity.change_member_role(ChangeMemberRoleCommand(
                org_id=org_id, user_id=user_id, role=role,
            ))
        except (AggregateNotFound, DomainValidationError, InvariantViolation) as exc:
            get_logger(__name__).warning("组织成员改角色被领域规则拦截: %s", exc)
            return None
        return OrganizationRepo.update_member(org_id, user_id, role=role)

    def remove_member(self, org_id: str, user_id: str) -> bool:
        """移除组织成员（只读预检 + DDD 聚合权威裁决：组织至少保留一名 owner）。

        先经 guard_org_remove_member 做只读预检：违反"至少保留一名 owner"不变量
        即直接拒绝，**不触碰任何落库副作用、也不回退到既有 repo 兜底**（否则被
        聚合拒绝的操作会被 repo 静默执行成功，规则形同虚设）。预检放行后，实际
        移除仍委托 DDD 聚合裁决（真实数据抛 InvariantViolation，聚合读不到时
        退化为 False 不抛 500）。
        """
        allowed, err = guard_org_remove_member(org_id, user_id)
        if not allowed:
            get_logger(__name__).warning("移除组织成员被领域规则拦截: %s", err)
            return False
        try:
            return _ddd_identity.remove_member(org_id, user_id, operator="system")
        except (AggregateNotFound, DomainValidationError, InvariantViolation) as exc:
            get_logger(__name__).warning("移除组织成员被领域规则拦截: %s", exc)
            return False

    def count_members(self, org_id: str) -> int:
        """统计组织成员数（委托 DDD）。"""
        return _ddd_identity.count_members(org_id)

    def list_orgs_by_user(self, user_id: str) -> List[dict]:
        """反查用户所属的所有组织（委托 DDD）。"""
        return _ddd_identity.list_orgs_by_user(user_id)

    def list_orgs_by_users(self, user_ids: List[str]) -> Dict[str, List[dict]]:
        """批量反查多个用户所属的组织（委托 DDD）。"""
        return _ddd_identity.list_orgs_by_users(user_ids)

    # ── 组织-项目关联 ────────────────────────────────────
    def list_projects(self, org_id: str) -> List[dict]:
        """列出组织项目（委托 DDD）。"""
        return _ddd_identity.list_projects(org_id)

    def bind_project(self, project_id: str, org_id: str) -> bool:
        """绑定项目到组织（委托 DDD）。"""
        return _ddd_identity.bind_project(project_id, org_id)

    # ── 租户初始化 / 摘要 ────────────────────────────────
    def seed_tenant_data(self) -> dict:
        """创建一套完整租户测试数据（跨 auth/projects 的业务编排）。"""
        # 确保默认组织存在
        OrganizationRepo.ensure_default_org()

        from app.services.auth_service import auth_service
        from app.services.project_service import project_service

        result = {"organizations": [], "members": [], "projects": []}

        # 1. 创建测试组织
        org_specs = [
            {"name": "AI测试平台-默认租户",
             "description": "AI测试平台默认租户，用于系统初始化"},
            {"name": "核心研发团队",
             "description": "负责核心平台研发的团队租户"},
            {"name": "质量保障中心",
             "description": "负责平台质量保障的租户"},
        ]
        for spec in org_specs:
            existing = self.get_by_name(spec["name"])
            if existing:
                result["organizations"].append(existing)
                continue
            org = self.create(spec["name"], spec["description"])
            result["organizations"].append(org)

        # 2. 创建测试用户并加入默认组织
        user_specs = [
            {"username": "org_admin", "password": "admin123",
             "name": "组织管理员", "email": "org_admin@example.com", "role": "admin"},
            {"username": "test_leader", "password": "test123",
             "name": "测试负责人", "email": "leader@example.com", "role": "member"},
            {"username": "dev_engineer", "password": "dev123",
             "name": "开发工程师", "email": "dev@example.com", "role": "member"},
            {"username": "qa_engineer", "password": "qa123",
             "name": "质量工程师", "email": "qa@example.com", "role": "member"},
        ]
        for spec in user_specs:
            user = None
            try:
                user = auth_service.get_user_by_username(spec["username"])
            except Exception:
                pass
            if not user:
                try:
                    user = auth_service.create_user(
                        username=spec["username"],
                        password=spec["password"],
                        name=spec["name"],
                        email=spec["email"],
                        role=spec["role"],
                    )
                except Exception as e:
                    get_logger(__name__).warning("创建用户 %s 失败: %s",
                                                 spec["username"], e)
                    continue
            try:
                member = self.add_member(
                    "default-org", user["id"],
                    role="admin" if spec["role"] == "admin" else "member")
                result["members"].append(member)
            except Exception as e:
                get_logger(__name__).warning("添加用户到组织失败: %s", e)

        # 3. 为组织创建项目
        project_specs = [
            {"name": "API自动化测试平台",
             "description": "核心API自动化测试平台项目", "org": "default-org"},
            {"name": "性能测试服务",
             "description": "性能测试与压测服务项目", "org": "default-org"},
            {"name": "质量报告中心",
             "description": "测试报告与质量度量中心项目", "org": "default-org"},
        ]
        for spec in project_specs:
            try:
                projects = project_service.list()
                existing = next(
                    (pr for pr in projects if pr.get("name") == spec["name"]), None)
                if existing:
                    result["projects"].append(existing)
                    continue
                proj = project_service.create({
                    "name": spec["name"],
                    "description": spec["description"],
                })
                self.bind_project(proj["id"], spec["org"])
                result["projects"].append(proj)
            except Exception as e:
                get_logger(__name__).warning("创建项目 %s 失败: %s",
                                             spec["name"], e)

        # 4. 为项目同步种子成员（幂等）
        try:
            org_members = self.list_members("default-org", limit=100)
            project_list = project_service.list()
            for proj in project_list:
                for om in org_members:
                    uid = om.get("user_id") or ""
                    if not uid:
                        continue
                    role = om.get("role", "member")
                    ug = "project-admin" if role == "admin" else "project-member"
                    try:
                        project_service.add_member(
                            project_id=proj["id"],
                            user_id=str(uid),
                            name=om.get("name", ""),
                            email=om.get("email", ""),
                            role=role,
                            user_group=ug,
                        )
                    except Exception as e:
                        get_logger(__name__).warning(
                            "同步项目 %s 成员失败: %s", proj.get("name"), e)
        except Exception as e:
            get_logger(__name__).warning("同步项目成员种子数据失败: %s", e)

        return result

    def tenant_summary(self) -> dict:
        """租户摘要（委托 DDD）。"""
        return _ddd_identity.tenant_summary()

    def get_tenant_summary(self) -> dict:
        """兼容旧命名风格的租户摘要入口（委托 DDD）。"""
        return _ddd_identity.get_tenant_summary()


organization_service = OrganizationService()
