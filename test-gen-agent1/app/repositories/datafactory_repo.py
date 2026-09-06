# app/repositories/datafactory_repo.py
"""数据工厂数据访问层（Phase 3 重构 · 4 层对齐）。

本层是 datafactory 域**唯一权威**：同时持有表结构 DDL 与数据访问 SQL。
- 表结构（data_templates / data_batches）由本模块 _init_db 幂等建表，
  作为 schema_registry 单一权威来源，不再依赖旧 app.datafactory.repository。
- 旧 app.datafactory.repository 仅作兼容门面，模块顶部委托本仓库，形成
  datafactory.repository → datafactory_repo 的单向依赖，消除双向循环依赖。

纯数据访问（data_templates / data_batches 的 CRUD / 造数 / 清理 /
统计）均在仓库内直连 SQL，输出形态与旧 facade 完全一致
（schema_json / deps_json / tags / data_json 反序列化等）。
"""
import json
import logging
import random
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.database import Database
from app.core.exceptions import NotFoundError

logger = logging.getLogger(__name__)

# 数据模板类别（与旧 repository 保持一致）
CATEGORY_USER = "user"
CATEGORY_ORDER = "order"
CATEGORY_PRODUCT = "product"
CATEGORY_INVENTORY = "inventory"
CATEGORY_COUPON = "coupon"
CATEGORY_PAYMENT = "payment"
CATEGORY_CUSTOM = "custom"
VALID_CATEGORIES = {
    CATEGORY_USER, CATEGORY_ORDER, CATEGORY_PRODUCT,
    CATEGORY_INVENTORY, CATEGORY_COUPON, CATEGORY_PAYMENT,
    CATEGORY_CUSTOM,
}

# 数据生成策略
STRATEGY_SEQUENCE = "sequence"
STRATEGY_FIXED = "fixed"
STRATEGY_UUID = "uuid"
STRATEGY_RANDOM = "random"
STRATEGY_TIMESTAMP = "timestamp"
STRATEGY_REFERENCE = "reference"

DB_NAME = "datafactory.db"


def _get_conn() -> sqlite3.Connection:
    """获取 datafactory.db 连接（统一使用 Database 连接池）。"""
    return Database.get_conn(DB_NAME)


def _init_db() -> None:
    """幂等建表（权威 DDL，供 schema_registry / 迁移兜底引用）。"""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS data_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                category TEXT DEFAULT 'custom',
                schema_json TEXT DEFAULT '{}',
                deps_json TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                status TEXT DEFAULT 'active',
                created_at REAL,
                updated_at REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS data_batches (
                id TEXT PRIMARY KEY,
                template_id TEXT,
                template_name TEXT DEFAULT '',
                batch_size INTEGER DEFAULT 1,
                env_key TEXT DEFAULT 'default',
                data_json TEXT DEFAULT '[]',
                status TEXT DEFAULT 'active',
                created_at REAL,
                updated_at REAL
            )
        """)
        conn.commit()
    finally:
        pass


_init_db()


class DatafactoryRepo:
    """数据工厂数据访问仓库。

    直接以 datafactory.db（统一路由 tga.db）落库，不再委托旧
    app.datafactory.repository。对外暴露与旧模块一致的类方法签名，
    保证上层（datafactory_service）零改动。
    """

    db_name = DB_NAME

    @classmethod
    def _conn(cls) -> sqlite3.Connection:
        """获取 datafactory.db 连接（表已由模块导入时 _init_db 建好）。"""
        return _get_conn()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        """裸行 → 归一化输出（JSON 字段反序列化，与旧 repository 一致）。"""
        data = dict(row)
        schema_raw = data.get("schema_json", "")
        data["schema"] = json.loads(schema_raw) if schema_raw else {}
        data.pop("schema_json", None)
        deps_raw = data.get("deps_json", "")
        data["deps"] = json.loads(deps_raw) if deps_raw else []
        data.pop("deps_json", None)
        tags_raw = data.get("tags", "")
        data["tags"] = json.loads(tags_raw) if tags_raw else []
        return data

    # ── 数据模板 CRUD ─────────────────────────────────────
    @classmethod
    def create_template(cls, name: str, description: str = "",
                        category: str = "", schema: dict = None,
                        deps: list = None, tags: list = None) -> dict:
        """创建数据模板。"""
        template_id = uuid.uuid4().hex[:12]
        now = time.time()
        conn = cls._conn()
        conn.execute(
            """INSERT INTO data_templates
               (id, name, description, category, schema_json, deps_json,
                tags, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (template_id, name, description, category,
             json.dumps(schema or {}, ensure_ascii=False),
             json.dumps(deps or []),
             json.dumps(tags or []), "active", now, now),
        )
        return cls.get_template(template_id) or {"id": template_id}

    @classmethod
    def get_template(cls, template_id: str) -> Optional[dict]:
        conn = cls._conn()
        row = conn.execute(
            "SELECT * FROM data_templates WHERE id = ?", (template_id,)
        ).fetchone()
        return cls._row_to_dict(row) if row else None

    @classmethod
    def list_templates(cls, category: Optional[str] = None,
                       search: Optional[str] = None, limit: int = 100,
                       offset: int = 0) -> list:
        query = "SELECT * FROM data_templates WHERE status = 'active'"
        params: List = []
        if category and category in VALID_CATEGORIES:
            query += " AND category = ?"
            params.append(category)
        if search:
            query += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        conn = cls._conn()
        rows = conn.execute(query, params).fetchall()
        return [cls._row_to_dict(r) for r in rows]

    @classmethod
    def update_template(cls, template_id: str, **kwargs) -> Optional[dict]:
        existing = cls.get_template(template_id)
        if not existing:
            return None

        allowed = {"name", "description", "category", "schema", "deps", "tags", "status"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}

        if "schema" in updates and isinstance(updates["schema"], dict):
            updates["schema_json"] = json.dumps(updates["schema"], ensure_ascii=False)
            del updates["schema"]
        if "deps" in updates and isinstance(updates["deps"], list):
            updates["deps_json"] = json.dumps(updates["deps"])
            del updates["deps"]
        if "tags" in updates and isinstance(updates["tags"], list):
            updates["tags"] = json.dumps(updates["tags"])

        if not updates:
            return existing

        updates["updated_at"] = time.time()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [template_id]

        conn = cls._conn()
        conn.execute(f"UPDATE data_templates SET {set_clause} WHERE id = ?", values)
        return cls.get_template(template_id)

    @classmethod
    def delete_template(cls, template_id: str) -> bool:
        conn = cls._conn()
        cur = conn.execute("DELETE FROM data_templates WHERE id = ?", (template_id,))
        return cur.rowcount > 0

    # ── 造数 / 清理 / 批次 ─────────────────────────────────
    @classmethod
    def generate_data(cls, template_id: str = "", batch_size: int = 1,
                      env_key: str = "") -> dict:
        """一键造数：根据模板生成指定批次大小的测试数据。"""
        template = cls.get_template(template_id)
        if not template:
            raise NotFoundError(f"数据模板 {template_id} 不存在")

        schema = template.get("schema", {})
        if not isinstance(schema, dict):
            schema = {}

        # 解析依赖
        deps = template.get("deps", [])
        dep_data = {}
        for dep_id in deps:
            dep = cls.get_template(dep_id)
            if dep:
                dep_schema = dep.get("schema", {})
                if isinstance(dep_schema, dict):
                    for field, spec in dep_schema.items():
                        if isinstance(spec, dict):
                            dep_data[f"{dep['name']}.{field}"] = cls._gen_value(spec, 1, {})

        batch_id = uuid.uuid4().hex[:12]
        now = time.time()
        generated_items = []

        for i in range(batch_size):
            item = {}
            registry = {**dep_data}
            for field, spec in schema.items():
                if isinstance(spec, dict):
                    item[field] = cls._gen_value(spec, i + 1, registry)
                else:
                    item[field] = spec
            generated_items.append(item)

        conn = cls._conn()
        conn.execute(
            """INSERT INTO data_batches
               (id, template_id, template_name, batch_size, env_key,
                data_json, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (batch_id, template_id, template.get("name", ""), batch_size,
             env_key, json.dumps(generated_items, ensure_ascii=False),
             "active", now, now),
        )

        return {
            "batch_id": batch_id,
            "template_id": template_id,
            "template_name": template.get("name", ""),
            "batch_size": batch_size,
            "env_key": env_key,
            "data": generated_items,
            "created_at": now,
        }

    @staticmethod
    def _gen_value(field_spec: Dict[str, Any], seq: int, registry: Dict[str, Any]) -> Any:
        """根据字段定义生成值。"""
        strategy = field_spec.get("strategy", STRATEGY_FIXED)
        value = field_spec.get("value", "")

        if strategy == STRATEGY_FIXED:
            return value
        elif strategy == STRATEGY_SEQUENCE:
            if isinstance(value, str) and "{n}" in value:
                return value.replace("{n}", str(seq))
            return f"{value}{seq}"
        elif strategy == STRATEGY_UUID:
            return uuid.uuid4().hex
        elif strategy == STRATEGY_RANDOM:
            choices = field_spec.get("choices", [])
            if choices:
                return random.choice(choices)
            low = field_spec.get("min", 0)
            high = field_spec.get("max", 1000)
            return random.randint(int(low), int(high))
        elif strategy == STRATEGY_TIMESTAMP:
            fmt = field_spec.get("format", "%Y-%m-%d %H:%M:%S")
            return time.strftime(fmt, time.localtime(time.time() + seq))
        elif strategy == STRATEGY_REFERENCE:
            ref_key = field_spec.get("ref", "")
            if ref_key in registry:
                return registry[ref_key]
            return None
        return value

    @classmethod
    def list_batches(cls, limit: int = 50) -> list:
        conn = cls._conn()
        rows = conn.execute(
            "SELECT * FROM data_batches ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("data_json"):
                try:
                    d["data"] = json.loads(d["data_json"])
                except (json.JSONDecodeError, TypeError):
                    d["data"] = []
            d.pop("data_json", None)
            result.append(d)
        return result

    @classmethod
    def cleanup_batch(cls, batch_id: str) -> bool:
        conn = cls._conn()
        cur = conn.execute(
            "UPDATE data_batches SET status = 'cleaned', updated_at = ? WHERE id = ?",
            (time.time(), batch_id),
        )
        return cur.rowcount > 0

    @classmethod
    def cleanup_by_template(cls, template_id: str, env_key: str = "default") -> int:
        conn = cls._conn()
        cur = conn.execute(
            """UPDATE data_batches SET status = 'cleaned', updated_at = ?
               WHERE template_id = ? AND env_key = ? AND status = 'active'""",
            (time.time(), template_id, env_key),
        )
        return cur.rowcount

    @classmethod
    def cleanup_by_env(cls, env_key: str) -> int:
        conn = cls._conn()
        cur = conn.execute(
            """UPDATE data_batches SET status = 'cleaned', updated_at = ?
               WHERE env_key = ? AND status = 'active'""",
            (time.time(), env_key),
        )
        return cur.rowcount

    @classmethod
    def stats(cls) -> dict:
        conn = cls._conn()
        template_count = conn.execute(
            "SELECT COUNT(*) FROM data_templates WHERE status = 'active'"
        ).fetchone()[0]
        batch_count = conn.execute(
            "SELECT COUNT(*) FROM data_batches WHERE status = 'active'"
        ).fetchone()[0]
        cleaned_count = conn.execute(
            "SELECT COUNT(*) FROM data_batches WHERE status = 'cleaned'"
        ).fetchone()[0]
        by_category = {c: 0 for c in VALID_CATEGORIES}
        for row in conn.execute(
            "SELECT category, COUNT(*) AS cnt FROM data_templates GROUP BY category"
        ):
            if row["category"] in by_category:
                by_category[row["category"]] = row["cnt"]
        return {
            "template_count": template_count,
            "active_batches": batch_count,
            "cleaned_batches": cleaned_count,
            "total_batches": batch_count + cleaned_count,
            "by_category": by_category,
        }



    @classmethod
    def seed_default_templates(cls) -> None:
        """初始化内置数据模板（部署期种子，幂等：已有模板则跳过）。"""
        if cls.list_templates(limit=1):
            return
        now = time.time()
        templates = [
            {
                "name": "用户模板",
                "description": "创建测试用户，含手机号/邮箱/地址等字段",
                "category": CATEGORY_USER,
                "schema": {
                    "username": {"strategy": STRATEGY_SEQUENCE, "value": "test_user_{n}"},
                    "phone": {"strategy": STRATEGY_RANDOM, "choices": ["13800138000", "13900139000", "13700137000"]},
                    "email": {"strategy": STRATEGY_SEQUENCE, "value": "user{n}@test.com"},
                    "address": {"strategy": STRATEGY_FIXED, "value": "北京市朝阳区测试路1号"},
                    "is_vip": {"strategy": STRATEGY_FIXED, "value": False},
                    "created_at": {"strategy": STRATEGY_TIMESTAMP, "format": "%Y-%m-%d %H:%M:%S"},
                },
                "deps": [],
                "tags": ["用户", "基础数据"],
            },
            {
                "name": "商品模板",
                "description": "创建测试商品，含名称/价格/分类/库存",
                "category": CATEGORY_PRODUCT,
                "schema": {
                    "product_name": {"strategy": STRATEGY_SEQUENCE, "value": "测试商品_{n}"},
                    "price": {"strategy": STRATEGY_RANDOM, "min": 10, "max": 1000},
                    "category": {"strategy": STRATEGY_FIXED, "value": "电子产品"},
                    "description": {"strategy": STRATEGY_FIXED, "value": "自动化测试生成"},
                    "sku": {"strategy": STRATEGY_UUID},
                    "created_at": {"strategy": STRATEGY_TIMESTAMP, "format": "%Y-%m-%d %H:%M:%S"},
                },
                "deps": [],
                "tags": ["商品", "基础数据"],
            },
            {
                "name": "订单模板",
                "description": "创建测试订单，依赖用户/商品模板",
                "category": CATEGORY_ORDER,
                "schema": {
                    "order_no": {"strategy": STRATEGY_SEQUENCE, "value": "ORD{n:06d}"},
                    "user_id": {"strategy": STRATEGY_REFERENCE, "ref": "用户模板.user_id"},
                    "product_id": {"strategy": STRATEGY_REFERENCE, "ref": "商品模板.sku"},
                    "amount": {"strategy": STRATEGY_RANDOM, "min": 1, "max": 10000},
                    "status": {"strategy": STRATEGY_FIXED, "value": "pending"},
                    "payment_method": {"strategy": STRATEGY_FIXED, "value": "wechat"},
                    "created_at": {"strategy": STRATEGY_TIMESTAMP, "format": "%Y-%m-%d %H:%M:%S"},
                },
                "deps": [],
                "tags": ["订单", "核心数据"],
            },
            {
                "name": "库存模板",
                "description": "创建测试库存记录，关联商品",
                "category": CATEGORY_INVENTORY,
                "schema": {
                    "warehouse_id": {"strategy": STRATEGY_SEQUENCE, "value": "WH-{n}"},
                    "product_sku": {"strategy": STRATEGY_UUID},
                    "quantity": {"strategy": STRATEGY_RANDOM, "min": 1, "max": 500},
                    "reserved": {"strategy": STRATEGY_FIXED, "value": 0},
                    "created_at": {"strategy": STRATEGY_TIMESTAMP, "format": "%Y-%m-%d %H:%M:%S"},
                },
                "deps": [],
                "tags": ["库存", "基础数据"],
            },
            {
                "name": "优惠券模板",
                "description": "创建测试优惠券，支持满减/折扣类型",
                "category": CATEGORY_COUPON,
                "schema": {
                    "coupon_code": {"strategy": STRATEGY_SEQUENCE, "value": "CPN{n:08d}"},
                    "type": {"strategy": STRATEGY_FIXED, "value": "discount"},
                    "value": {"strategy": STRATEGY_RANDOM, "min": 5, "max": 50},
                    "min_amount": {"strategy": STRATEGY_FIXED, "value": 100},
                    "expire_at": {"strategy": STRATEGY_TIMESTAMP, "format": "%Y-%m-%d"},
                    "created_at": {"strategy": STRATEGY_TIMESTAMP, "format": "%Y-%m-%d"},
                },
                "deps": [],
                "tags": ["优惠券", "营销数据"],
            },
        ]
        conn = cls._conn()
        try:
            for t in templates:
                template_id = uuid.uuid4().hex[:12]
                conn.execute(
                    """INSERT INTO data_templates
                       (id, name, description, category, schema_json, deps_json,
                        tags, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (template_id, t["name"], t["description"], t["category"],
                     json.dumps(t["schema"], ensure_ascii=False),
                     json.dumps(t["deps"]),
                     json.dumps(t["tags"]), "active", now, now),
                )
            conn.commit()
            logger.info("已初始化 %d 个内置数据模板", len(templates))
        finally:
            pass

# 兼容类方法调用（部分上层代码按类使用）
datafactory_repo = DatafactoryRepo
