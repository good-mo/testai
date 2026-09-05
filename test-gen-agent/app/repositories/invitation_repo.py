# app/repositories/invitation_repo.py
"""邀请注册数据访问层。

支撑「邀请注册」全流程（/invite 页面）：
  - 管理员通过系统/组织/项目三个邀请接口创建邀请记录
  - 被邀请人打开 /#/invite?inviteId=xxx 邀请链接后：
      GET  /system/user/check-invite/{inviteId}    校验邀请是否有效
      POST /system/user/register-by-invite          完成注册并加入目标组织/项目

邀请记录存于统一 tga.db（auth.db 路由到同一库），与 users 同库便于事务一致。
"""
import json
import time
import uuid
from typing import List, Optional

from app.core.database import Database
from app.logging_config import get_logger
from app.repositories.base import BaseRepo

logger = get_logger(__name__)


class InvitationRepo(BaseRepo):
    """邀请注册数据访问层。"""

    db_name = "auth.db"
    table_name = "invitations"

    # 邀请有效期（秒）：7 天
    DEFAULT_TTL = 7 * 24 * 3600

    @classmethod
    def _init_table(cls) -> None:
        """幂等建表。"""
        try:
            conn = Database.get_conn(cls.db_name)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS invitations (
                    id TEXT PRIMARY KEY,
                    invite_id TEXT NOT NULL UNIQUE,
                    email TEXT DEFAULT '',
                    scope TEXT DEFAULT 'SYSTEM',      -- SYSTEM / ORGANIZATION / PROJECT
                    organization_id TEXT DEFAULT '',
                    project_id TEXT DEFAULT '',
                    role_ids TEXT DEFAULT '[]',        -- JSON 数组（user_group id）
                    expire_time REAL,
                    used INTEGER DEFAULT 0,
                    create_time REAL,
                    create_user TEXT DEFAULT 'admin'
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_invitations_invite_id ON invitations(invite_id)"
            )
            conn.commit()
        except Exception as exc:  # pragma: no cover
            logger.error("初始化邀请表失败: %s", exc)

    # ── 创建 ────────────────────────────────────────────
    @classmethod
    def create_invite(cls, emails: List[str], scope: str = "SYSTEM",
                      organization_id: str = "", project_id: str = "",
                      role_ids: Optional[List[str]] = None,
                      create_user: str = "admin",
                      ttl: Optional[float] = None) -> Optional[dict]:
        """为一批邮箱创建邀请记录，返回第一条（含 invite_id）。

        同一条邀请统一一个 invite_id，被邀请邮箱可从 records 列表查看。
        这里为简化，每个邮箱各生成一条独立邀请，便于后续按邮箱核对。
        但 /invite 注册接口仅凭 inviteId 定位，为兼容"一个邮箱一个链接"，
        我们为第一个邮箱创建记录并返回 inviteId。
        """
        cls._init_table()
        if not emails:
            return None
        email = str(emails[0] or "")
        now = time.time()
        expire = now + (ttl if ttl is not None else cls.DEFAULT_TTL)
        role_ids = role_ids or []
        conn = Database.get_conn(cls.db_name)
        rid = str(uuid.uuid4())
        invite_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO invitations
               (id, invite_id, email, scope, organization_id, project_id,
                role_ids, expire_time, used, create_time, create_user)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (rid, invite_id, email, scope, organization_id, project_id,
             json.dumps(role_ids), expire, 0, now, create_user),
        )
        conn.commit()
        return cls.get_by_invite_id(invite_id)

    @classmethod
    def get_by_invite_id(cls, invite_id: str) -> Optional[dict]:
        """按 invite_id 查找邀请。"""
        cls._init_table()
        conn = Database.get_conn(cls.db_name)
        row = conn.execute(
            "SELECT * FROM invitations WHERE invite_id = ?", (invite_id,)
        ).fetchone()
        return dict(row) if row else None

    @classmethod
    def is_valid(cls, invite_id: str) -> bool:
        """邀请是否有效（存在、未过期、未使用）。"""
        inv = cls.get_by_invite_id(invite_id)
        if not inv:
            return False
        if inv.get("used"):
            return False
        expire = inv.get("expire_time") or 0
        if expire and time.time() > expire:
            return False
        return True

    @classmethod
    def mark_used(cls, invite_id: str) -> bool:
        """标记邀请已使用。"""
        cls._init_table()
        conn = Database.get_conn(cls.db_name)
        cur = conn.execute(
            "UPDATE invitations SET used = 1 WHERE invite_id = ?",
            (invite_id,),
        )
        conn.commit()
        return cur.rowcount > 0


# 便捷单例（与其它 repo 风格一致）
invitation_repo = InvitationRepo()
