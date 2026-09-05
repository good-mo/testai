"""组织/成员/认证 限界上下文（Bounded Context）。

聚合根：`User` / `Organization`(含 Member) / `Role` / `Invitation`
内聚：ApiKey、账号状态、成员角色、权限集合等子实体/值对象。
对应现有：`auth/*` `services/auth_service.py` `services/organization_service.py`
         `repositories/auth_repo.py` `repositories/organization_repo.py`

    app/domain/identity/domain/          领域层（与存储/框架零依赖）
        entities/                      User/Organization/Role/Invitation 聚合根
        value_objects/                 账号状态 / 成员角色 / 权限 / 邀请状态
        services/                      AccessPolicy 授权策略
        events.py                      领域事件
        repository.py                  聚合仓储接口（Repository Protocol）
        exceptions.py                  领域异常
    app/domain/identity/application/     应用层（用例编排，事务边界）
        identity_app_service.py          应用服务门面
        dto.py                           命令/查询 DTO
    app/domain/identity/infrastructure/  基础设施层（对接既有 Repo 存储）
        identity_repository_impl.py      聚合仓储实现（防腐层）

依赖规则：domain 不依赖 application / infrastructure；
application 依赖 domain；infrastructure 依赖 domain 与现有存储层。
"""
from app.domain.identity.application.identity_app_service import (
    IdentityAppService,
    identity_app_service,
)
from app.domain.identity.domain.entities.invitation import Invitation
from app.domain.identity.domain.entities.organization import Organization
from app.domain.identity.domain.entities.role import Role
from app.domain.identity.domain.entities.user import User

__all__ = [
    "IdentityAppService", "identity_app_service",
    "User", "Organization", "Role", "Invitation",
]
