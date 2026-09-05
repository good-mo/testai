#!/usr/bin/env python3
"""
数据库合并脚本（Phase 6）
=========================
将多个 SQLite 数据库合并为统一数据库 tga.db。

目标：
  - 14+ 个 .db 文件 → 1 个 tga.db（业务数据）+ checkpoints.db（LangGraph）
  - 合并后统一使用 app.core.database.Database 访问

用法：
    python3 scripts/merge_databases.py --dry-run    # 预览合并计划
    python3 scripts/merge_databases.py --execute    # 执行合并
    python3 scripts/merge_databases.py --backup     # 备份原数据库
    python3 scripts/merge_databases.py --check      # 检查合并冲突与结构完整性（CI 用）
"""
import argparse
import os
import shutil
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import PROJECT_ROOT, TGA_DB

# 需要合并的业务数据库
BUSINESS_DBS = {
    "auth.db": "auth",
    "apitest.db": "apitest",
    "defects.db": "defects",
    "environments.db": "environments",
    "projects.db": "projects",
    "runs.db": "runs",
    "scripthealth.db": "scripthealth",
    "test_plans.db": "test_plans",
    "testcases.db": "test_cases",
    "trace.db": "trace",
    "datafactory.db": "datafactory",
}

# 不需要合并的独立数据库
SEPARATE_DBS = ["checkpoints.db"]


def db_path(filename: str) -> str:
    return os.path.join(PROJECT_ROOT, filename)


def list_tables(db_file: str) -> list:
    """列出数据库中的所有表。"""
    if not os.path.exists(db_file):
        return []
    conn = sqlite3.connect(db_file)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows if not r[0].startswith('sqlite_')]
    finally:
        conn.close()


def get_columns(db_file: str, table: str) -> dict:
    """获取表的字段定义：{列名: (类型, 非空, 是否主键)}。"""
    conn = sqlite3.connect(db_file)
    try:
        rows = conn.execute(f"PRAGMA table_info([{table}])").fetchall()
        return {r[1]: (r[2] or "", int(r[3] or 0), int(r[5] or 0)) for r in rows}
    finally:
        conn.close()


def get_indexes(db_file: str, table: str) -> dict:
    """获取表上的索引定义：{索引名: 索引DDL}。"""
    conn = sqlite3.connect(db_file)
    try:
        rows = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name=?",
            (table,),
        ).fetchall()
        return {r[0]: (r[1] or "").strip() for r in rows if r[0]}
    finally:
        conn.close()


def get_primary_keys(db_file: str, table: str) -> list:
    """获取表的主键列列表。"""
    conn = sqlite3.connect(db_file)
    try:
        rows = conn.execute(f"PRAGMA table_info([{table}])").fetchall()
        return [r[1] for r in rows if r[5]]
    finally:
        conn.close()


def _collect_plan() -> dict:
    """收集合并计划：目标表名 -> [(源库, 源表名, 字段定义)]。"""
    plan = {}
    for db_file, prefix in BUSINESS_DBS.items():
        path = db_path(db_file)
        if not os.path.exists(path):
            continue
        for table in list_tables(path):
            target_table = f"{prefix}_{table}" if prefix else table
            plan.setdefault(target_table, []).append(
                (db_file, table, get_columns(path, table))
            )
    return plan


def _format_diff(cols_a: dict, cols_b: dict, label_a: str, label_b: str) -> list:
    """比较两个字段定义（类型级差异），返回差异描述列表。"""
    diffs = []
    for col in sorted(set(cols_a) | set(cols_b)):
        a = cols_a.get(col)
        b = cols_b.get(col)
        if a is None:
            diffs.append(f"字段 {col} 仅存在于 {label_b}")
        elif b is None:
            diffs.append(f"字段 {col} 仅存在于 {label_a}")
        elif a[0].upper() != b[0].upper():
            diffs.append(f"字段 {col} 类型不一致: {label_a}={a[0]} vs {label_b}={b[0]}")
    return diffs


def check() -> int:
    """检查数据库合并冲突与结构完整性，有问题返回 1。

    合并脚本对已存在的目标表不再建表、直接 INSERT，
    因此同名表的字段/类型不一致会导致合并后数据错列或丢失；
    SQLite 索引名为库级唯一，同名不同定义会在合并时直接报错。
    这些问题到执行阶段才发现已太晚，故在 CI 阶段提前暴露。

    检查项：
      1. 多个源库映射到同一目标表，但字段/类型不一致
      2. 目标表已存在于 tga.db，但字段/类型不一致
      3. 索引名重复但定义不一致
      4. 已合并库完整性：表数量 / 索引数 / 缺主键表（仅提示）
    """
    print("=" * 60)
    print("数据库合并冲突检查")
    print("=" * 60)

    target = db_path(TGA_DB)
    plan = _collect_plan()
    conflicts = []

    if plan:
        print(f"待合并业务数据库: {len(plan)} 张目标表")
    else:
        print("待合并业务数据库: 0（源库已全部合并）")

    # 1) 多个源库合并到同一目标表，但字段/类型不一致
    for target_table, sources in sorted(plan.items()):
        if len(sources) < 2:
            continue
        base_db, base_table, base_cols = sources[0]
        for other_db, other_table, other_cols in sources[1:]:
            diffs = _format_diff(
                base_cols, other_cols,
                f"{base_db}.{base_table}", f"{other_db}.{other_table}",
            )
            if diffs:
                conflicts.append(
                    f"目标表 {target_table} 结构冲突: "
                    f"{base_db}.{base_table} vs {other_db}.{other_table}\n"
                    + "\n".join(f"    - {d}" for d in diffs)
                )

    # 2) 目标表已存在于 tga.db，但字段/类型不一致
    existing_tables = list_tables(target) if os.path.exists(target) else []
    if existing_tables:
        existing = {t: get_columns(target, t) for t in existing_tables}
        for target_table, sources in sorted(plan.items()):
            if target_table not in existing:
                continue
            for src_db, src_table, src_cols in sources:
                diffs = _format_diff(
                    existing[target_table], src_cols,
                    f"{TGA_DB}.{target_table}", f"{src_db}.{src_table}",
                )
                if diffs:
                    conflicts.append(
                        f"目标表 {target_table} 与已合并库 {TGA_DB} 结构冲突: "
                        f"{src_db}.{src_table}\n"
                        + "\n".join(f"    - {d}" for d in diffs)
                    )

    # 3) 索引名冲突：SQLite 索引名是库级唯一的，同名不同定义会在合并时直接报错
    index_owner = {}
    for db_file, _prefix in BUSINESS_DBS.items():
        path = db_path(db_file)
        if not os.path.exists(path):
            continue
        for table in list_tables(path):
            for idx_name, idx_sql in get_indexes(path, table).items():
                if idx_name in index_owner and index_owner[idx_name][1] != idx_sql:
                    conflicts.append(
                        f"索引名冲突: {idx_name} 同时存在于 "
                        f"{index_owner[idx_name][0]} 与 {db_file}.{table}，且定义不一致"
                    )
                index_owner.setdefault(idx_name, (f"{db_file}.{table}", idx_sql))

    for t in existing_tables:
        for idx_name, idx_sql in get_indexes(target, t).items():
            if idx_name in index_owner and index_owner[idx_name][1] != idx_sql:
                conflicts.append(
                    f"索引名冲突: {idx_name} 与已合并库 {TGA_DB} 中的定义不一致"
                )

    # 4) 已合并库完整性（仅提示，不阻断）
    if existing_tables:
        no_pk = [t for t in existing_tables if not get_primary_keys(target, t)]
        index_count = sum(len(get_indexes(target, t)) for t in existing_tables)
        print(f"已合并库 {TGA_DB}: {len(existing_tables)} 张表 / {index_count} 个索引")
        if no_pk:
            print(f"[WARN] {len(no_pk)} 张表缺少主键: {', '.join(no_pk)}")

    if conflicts:
        print(f"\n[ERROR] 发现 {len(conflicts)} 处合并冲突:")
        for c in conflicts:
            print(f"  ❌ {c}")
        print("\n请统一字段/索引定义后重新执行 --execute 合并。")
        return 1

    print("[OK] 未发现数据库合并冲突")
    return 0


def get_table_info(db_file: str, table: str) -> dict:
    """获取表的创建 SQL 和行数。"""
    conn = sqlite3.connect(db_file)
    try:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        count = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
        return {"sql": row[0] if row else "", "count": count}
    finally:
        conn.close()


def merge_tables(source_db: str, target_db: str, prefix: str = "") -> int:
    """将 source_db 中的所有表合并到 target_db。

    Args:
        source_db: 源数据库文件路径
        target_db: 目标数据库文件路径
        prefix: 表名前缀，避免重名冲突

    Returns:
        合并的行数
    """
    total_rows = 0
    tables = list_tables(source_db)
    if not tables:
        return 0

    target_conn = sqlite3.connect(target_db)
    try:
        for table in tables:
            info = get_table_info(source_db, table)
            if not info["sql"]:
                continue

            # 添加前缀避免冲突
            target_table = f"{prefix}_{table}" if prefix else table

            # 检查目标表是否已存在
            exists = target_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (target_table,),
            ).fetchone()

            if not exists:
                # 创建表（替换表名为目标表名）
                sql = info["sql"]
                sql = sql.replace(f'CREATE TABLE "{table}"', f'CREATE TABLE "{target_table}"')
                sql = sql.replace(f"CREATE TABLE {table}", f"CREATE TABLE {target_table}")
                target_conn.execute(sql)

            # 复制数据
            src_conn = sqlite3.connect(source_db)
            try:
                cols = [r[1] for r in src_conn.execute(f"PRAGMA table_info([{table}])").fetchall()]
                if not cols:
                    continue
                col_names = ", ".join([f'"{c}"' for c in cols])
                placeholders = ", ".join(["?"] * len(cols))

                rows = src_conn.execute(f"SELECT {col_names} FROM [{table}]").fetchall()
                for row in rows:
                    try:
                        target_conn.execute(
                            f'INSERT OR IGNORE INTO "{target_table}" ({col_names}) VALUES ({placeholders})',
                            row,
                        )
                        total_rows += 1
                    except sqlite3.Error as e:
                        print(f"  ⚠️ 跳过行: {e}")
            finally:
                src_conn.close()

        target_conn.commit()
        return total_rows
    finally:
        target_conn.close()


def dry_run() -> None:
    """预览合并计划。"""
    print("=" * 60)
    print("数据库合并计划（Dry Run）")
    print("=" * 60)

    total_before = 0
    total_after = 0

    for db_file, prefix in BUSINESS_DBS.items():
        path = db_path(db_file)
        if not os.path.exists(path):
            continue
        size = os.path.getsize(path) / 1024
        tables = list_tables(path)
        total_before += size
        print(f"\n📦 {db_file} ({size:.0f}KB, {len(tables)} tables)")
        for t in tables:
            info = get_table_info(path, t)
            print(f"  └─ {prefix}_{t}: {info['count']} rows")
            total_after += info["count"]

    print(f"\n{'=' * 60}")
    print(f"合并前: {len(BUSINESS_DBS)} 个数据库文件")
    print(f"合并后: 1 个 {TGA_DB}")
    print(f"预计迁移 {total_after} 行数据")


def execute() -> None:
    """执行数据库合并。"""
    print("=" * 60)
    print("正在执行数据库合并...")
    print("=" * 60)

    target = db_path(TGA_DB)

    # 创建目标数据库
    if os.path.exists(target):
        print(f"目标数据库已存在: {target}")
        backup = f"{target}.bak"
        shutil.copy2(target, backup)
        print(f"已备份: {backup}")

    total_migrated = 0
    for db_file, prefix in BUSINESS_DBS.items():
        path = db_path(db_file)
        if not os.path.exists(path):
            print(f"⚠️ 跳过不存在的数据库: {db_file}")
            continue

        print(f"\n📦 合并 {db_file} → {TGA_DB} (prefix: {prefix})...")
        rows = merge_tables(path, target, prefix)
        print(f"  ✅ 迁移 {rows} 行")
        total_migrated += rows

    print(f"\n{'=' * 60}")
    print(f"✅ 合并完成！共迁移 {total_migrated} 行数据")
    print(f"   目标数据库: {target}")
    print("\n💡 下一步:")
    print(f"   1. app/core/database.py 已更新，自动路由到 {TGA_DB}")
    print("   2. 删除旧的 .db 文件")
    print("   3. 验证应用功能")


def backup() -> None:
    """备份所有数据库文件。"""
    backup_dir = os.path.join(PROJECT_ROOT, "backup_dbs")
    os.makedirs(backup_dir, exist_ok=True)

    for db_file in list(BUSINESS_DBS.keys()) + SEPARATE_DBS:
        path = db_path(db_file)
        if os.path.exists(path):
            dest = os.path.join(backup_dir, db_file)
            shutil.copy2(path, dest)
            print(f"✅ 备份 {db_file} → {dest}")
        else:
            print(f"⚠️ 跳过不存在的: {db_file}")

    print(f"\n备份完成，所有数据库已保存到 {backup_dir}")


def main():
    parser = argparse.ArgumentParser(description="数据库合并工具")
    parser.add_argument("--dry-run", action="store_true", help="预览合并计划")
    parser.add_argument("--execute", action="store_true", help="执行合并")
    parser.add_argument("--backup", action="store_true", help="备份原数据库")
    parser.add_argument("--check", action="store_true", help="检查合并冲突与结构完整性")
    args = parser.parse_args()

    if args.backup:
        backup()
    elif args.execute:
        execute()
    elif args.check:
        sys.exit(check())
    else:
        dry_run()


if __name__ == "__main__":
    main()
