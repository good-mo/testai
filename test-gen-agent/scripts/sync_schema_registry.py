#!/usr/bin/env python3
"""Schema Registry 采集脚本（Phase D · 单一来源收敛）。

自动扫描 app/ 下所有模块内联的 CREATE TABLE IF NOT EXISTS 声明，
据此**重新生成** app/core/schema_registry.py —— 让「模块内联 DDL」成为
唯一权威来源，消除「模块 + registry 双份手工维护」导致的漂移。

用法：
    python3 scripts/sync_schema_registry.py --update  # 重新生成 schema_registry.py
    python3 scripts/sync_schema_registry.py --check   # 内容级漂移检查（CI 用）

说明：
  - 所有表 DDL 一律取自模块源码，registry 不再另存副本。
  - 跨模块共享表（api_definitions 等）已收敛为单一权威 DDL（两模块 CREATE TABLE 一致），
    由 sync 脚本直接从模块源码提取，无需手工维护 override。
"""
import argparse
import difflib
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 排除自身，避免递归扫描
_EXCLUDE_FILES = {"schema_registry.py"}

_REGISTRY_PATH = PROJECT_ROOT / "app" / "core" / "schema_registry.py"

# ── 手工权威覆盖 ───────────────────────────────────────────
# 所有表 DDL 均由模块内联 CREATE TABLE 直接提取，无手工覆盖。
# 若模块间同名表再次出现 DDL 冲突，说明需要先收敛模块代码再清理此节。
_OVERRIDE_DDL: dict = {
}

def extract_ddl(content: str, table_name: str) -> str:
    """从源码提取指定表的完整 CREATE TABLE 声明。"""
    pattern = re.compile(
        rf'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{table_name}\s*\(',
        re.IGNORECASE
    )
    m = pattern.search(content)
    if not m:
        return ""
    start = m.start()
    i = content.index('(', start)
    depth = 0
    j = i
    in_triple = False
    in_single = False
    in_double = False
    while j < len(content):
        if in_triple:
            if content[j:j+3] == '"""':
                in_triple = False
                j += 3
                continue
            j += 1
            continue
        if not in_single and not in_double and content.startswith('"""', j):
            in_triple = True
            j += 3
            continue
        if in_single:
            if content[j] == "'" and (j == 0 or content[j-1] != '\\'):
                in_single = False
            j += 1
            continue
        if in_double:
            if content[j] == '"' and (j == 0 or content[j-1] != '\\'):
                in_double = False
            j += 1
            continue
        c = content[j]
        if c == "'":
            in_single = True
        elif c == '"':
            in_double = True
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                break
        j += 1
    return content[start:j+1].strip()


def clean_ddl(ddl: str) -> str:
    """去除 DDL 各行的过度缩进。"""
    lines = ddl.split('\n')
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    indent_levels = []
    for line in lines[1:]:
        if line.strip():
            indent = len(line) - len(line.lstrip())
            indent_levels.append(indent)
    min_indent = min(indent_levels) if indent_levels else 0
    cleaned = [lines[0]]
    for line in lines[1:]:
        if line.strip():
            if len(line) >= min_indent:
                cleaned.append(line[min_indent:])
            else:
                cleaned.append(line.lstrip())
        else:
            cleaned.append('')
    return '\n'.join(cleaned).strip()


def _strip_sql_comments(ddl: str) -> str:
    """去除 SQL 注释（-- 至行尾），保留字符串内字面量。"""
    lines = ddl.split('\n')
    out = []
    for line in lines:
        # 逐字符扫描，遇到 --（不在引号内）截断行
        result = []
        i = 0
        in_str = None
        while i < len(line):
            c = line[i]
            if in_str:
                result.append(c)
                if c == in_str:
                    in_str = None
                i += 1
            elif c in ('"', "'"):
                in_str = c
                result.append(c)
                i += 1
            elif c == '-' and i + 1 < len(line) and line[i+1] == '-':
                break  # SQL 注释
            else:
                result.append(c)
                i += 1
        out.append(''.join(result))
    return '\n'.join(out)


def _parse_columns(ddl: str) -> list:
    """从单张表 CREATE 声明中解析出 (列名, 完整定义) 列表。"""
    ddl = _strip_sql_comments(clean_ddl(ddl))
    inner = ddl[ddl.index('(')+1:ddl.rindex(')')]
    depth = 0
    cur = ''
    cols = []
    for ch in inner:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            cur = cur.strip()
            tok = cur.split()[0].strip('`"') if cur.split() else ''
            if tok and tok.upper() not in ('PRIMARY', 'UNIQUE', 'FOREIGN',
                                           'CHECK', 'CONSTRAINT', 'KEY', ')'):
                cols.append((tok, cur))
            cur = ''
        else:
            cur += ch
    cur = cur.strip()
    if cur:
        tok = cur.split()[0].strip('`"') if cur.split() else ''
        if tok and tok.upper() not in ('PRIMARY', 'UNIQUE', 'FOREIGN',
                                       'CHECK', 'CONSTRAINT', 'KEY', ')'):
            cols.append((tok, cur))
    return cols


def check_field_conventions(all_tables: dict) -> list:
    """按项目字段规范审计时间戳 / 软删除 / JSON 列，返回偏离清单。

    统一规范（以现代业务表为准）：
      - 时间戳列统一使用 `created_at` / `updated_at`（REAL，epoch 秒），
        不使用遗留的 `create_time` / `update_time`；
      - 软删除统一为 `deleted`(0/1) + `deleted_at`(删除时刻)，
        不允许只有 `deleted` 而无 `deleted_at` 删除时间戳；
      - 承载结构化数据的 JSON 列必须声明为 TEXT（避免被误存为 blob）。
    """
    findings = []
    for table, info in sorted(all_tables.items()):
        ddls = list(dict.fromkeys(info['ddls']))
        if not ddls:
            continue
        ddl = ddls[0]
        cols = _parse_columns(ddl)
        names = [n for n, _ in cols]
        has_new_ts = ('created_at' in names) or ('updated_at' in names)
        has_old_ts = ('create_time' in names) or ('update_time' in names)
        has_deleted = 'deleted' in names
        has_deleted_at = 'deleted_at' in names
        json_text_ok = True
        for n, full in cols:
            low = n.lower()
            is_jsonish = ('json' in low) or low.endswith(('_config', '_schema'))
            if is_jsonish and 'TEXT' not in full.upper():
                json_text_ok = False
        src = info['sources'][0]
        if has_old_ts and not has_new_ts:
            findings.append(
                f"  ⚠ [{table}] 时间戳沿用遗留命名 create_time/update_time"
                f"（src={src}）")
        elif has_old_ts and has_new_ts:
            findings.append(
                f"  ⚠ [{table}] 时间戳命名混用（create_time + created_at，"
                f"src={src}）")
        if has_deleted and not has_deleted_at:
            findings.append(
                f"  ⚠ [{table}] 软删除仅 deleted，缺 deleted_at 删除时间戳"
                f"（src={src}）")
        if not json_text_ok:
            findings.append(
                f"  ⚠ [{table}] 存在非 TEXT 的 JSON 列（src={src}）")
    return findings



def check_alter_column_drift(all_tables: dict) -> list:
    """检查模块运行时 ALTER TABLE ADD COLUMN 的列是否已收敛进 CREATE TABLE DDL.

    Alembic 基线 DDL 来自 schema_registry（由模块内联 CREATE TABLE 自动生成）。
    若某模块仅通过运行时 ALTER 补列而未同步 CREATE TABLE，则新库 Alembic 初始化
    后表会缺列 —— 本函数检测此类漂移。

    返回偏离清单（表名 / 列名 / 来源文件）。
    """
    _EXCLUDE_LOCAL = {"schema_registry.py"}
    app_dir = PROJECT_ROOT / "app"

    # 权威列集：{table: {column, ...}} —— 取 all_tables 中默认 DDL（V1）的列
    authoritative_cols = {}
    for table, info in all_tables.items():
        ddls = list(dict.fromkeys(info['ddls']))
        if not ddls:
            continue
        parsed = _parse_columns(ddls[0])
        authoritative_cols[table] = {n for n, _ in parsed}

    # 收集 ALTER 添加的列: {table: {column: source_file}}
    alter_columns = {}

    def _register(table: str, col: str, source: str):
        if table not in alter_columns:
            alter_columns[table] = {}
        if col not in alter_columns[table]:
            alter_columns[table][col] = source

    for root, _dirs, files in os.walk(app_dir):
        for fname in sorted(files):
            if not fname.endswith('.py') or fname in _EXCLUDE_LOCAL:
                continue
            path = os.path.join(root, fname)
            with open(path) as f:
                src = f.read()

            rel = os.path.relpath(path, PROJECT_ROOT)

            # 1) 静态 ALTER: ALTER TABLE xxx ADD COLUMN col ...
            for m in re.finditer(
                r'ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)',
                src, re.IGNORECASE
            ):
                table, col = m.groups()
                line = src[:m.start()].count('\n') + 1
                _register(table, col, f"{rel}:{line}")

            # 2) 动态循环: for col, typ in [("col", "TYPE"), ...]:
            #            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
            for m in re.finditer(
                r'for\s+col,\s*\w+\s+in\s+\[(.*?)\]:', src, re.DOTALL
            ):
                block = m.group(1)
                cols_in_block = [
                    c.group(1) for c in re.finditer(r'\("(\w+)"', block)
                ]
                if not cols_in_block:
                    continue
                after = src[m.end():m.end() + 600]
                tm = re.search(
                    r'ALTER\s+TABLE\s+\{?\{?\s*(\w+)\s*\}?\}?\s+ADD\s+COLUMN',
                    after, re.IGNORECASE
                )
                if tm:
                    table = tm.group(1)
                    line = src[:m.start()].count('\n') + 1
                    for col in cols_in_block:
                        _register(table, col, f"{rel}:{line}")

            # 3) 动态字典: for col, definition in _all_migrations.items():
            #              conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
            for m in re.finditer(
                r'for\s+col,\s*\w+\s+in\s+\w+\.items\(\)\s*:', src, re.DOTALL
            ):
                after = src[m.end():m.end() + 600]
                tm = re.search(
                    r'ALTER\s+TABLE\s+\{?\{?\s*(\w+)\s*\}?\}?\s+ADD\s+COLUMN',
                    after, re.IGNORECASE
                )
                if tm:
                    table = tm.group(1)
                    before = src[max(0, m.start() - 2000):m.start()]
                    dm = re.search(r'(\w+)\s*=\s*\{(.*?)\}', before, re.DOTALL)
                    if dm:
                        dict_text = dm.group(2)
                        cols_in_dict = [
                            c.group(1) for c in re.finditer(r'"(\w+)"\s*:', dict_text)
                        ]
                        line = src[:m.start()].count('\n') + 1
                        for col in cols_in_dict:
                            _register(table, col, f"{rel}:{line}")

            # 4) 多表迁移循环: for table in ('a', 'b'): 补 deleted/project_id 列
            for m in re.finditer(
                r'for\s+table\s+in\s+\(([^)]*)\)\s*:', src, re.DOTALL
            ):
                tables_in_block = [
                    t.strip().strip("'\"") for t in m.group(1).split(',')
                    if t.strip()
                ]
                if not tables_in_block:
                    continue
                after = src[m.end():m.end() + 1000]
                for col_pattern in ('deleted', 'deleted_at', 'project_id'):
                    pattern = (
                        r'ALTER\s+TABLE\s+\{?\{?\s*\w+\s*\}?\}?'
                        rf'\s+ADD\s+COLUMN\s+{col_pattern}'
                    )
                    for tm in re.finditer(pattern, after, re.IGNORECASE):
                        line = src[:m.start()].count('\n') + 1
                        for table in tables_in_block:
                            _register(table, col_pattern, f"{rel}:{line}")

    # 比对：ALTER 添加的列不在权威 DDL 中 -> 报告
    findings = []
    for table, col_map in sorted(alter_columns.items()):
        auth = authoritative_cols.get(table, set())
        for col, source in sorted(col_map.items()):
            if col not in auth:
                findings.append(
                    f"  ⚠ [{table}] 运行时 ALTER 添加列 `{col}` 未收敛进"
                    f" CREATE TABLE（src={source}）\n"
                    f"    请在模块 CREATE TABLE 中补上该列，然后执行 --update 同步 registry")
    return findings


def collect_all_tables() -> dict:
    """扫描 app/ 下的所有 CREATE TABLE 声明。"""
    all_tables = {}
    app_dir = PROJECT_ROOT / "app"
    for root, _dirs, files in os.walk(app_dir):
        for fname in sorted(files):
            if not fname.endswith('.py') or fname in _EXCLUDE_FILES:
                continue
            path = os.path.join(root, fname)
            with open(path) as f:
                content = f.read()

            stmt_pattern = re.compile(
                r'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)\s*\(',
                re.IGNORECASE
            )
            for m in stmt_pattern.finditer(content):
                table_name = m.group(1)
                line_no = content[:m.start()].count('\n') + 1

                # 识别逻辑库
                db_name = "tga.db"
                conn_calls = re.findall(
                    r'Database\.get_conn\(["\'](\w+\.db)["\']\)', content)
                if conn_calls:
                    db_name = conn_calls[0]
                db_attrs = re.findall(
                    r'db_name\s*(?::\s*\w+)?\s*=\s*["\'](\w+\.db)["\']', content)
                if db_attrs:
                    db_name = db_attrs[0]

                if table_name not in all_tables:
                    all_tables[table_name] = {
                        'ddls': [], 'sources': [], 'db': db_name
                    }
                ddl = extract_ddl(content, table_name)
                if ddl and clean_ddl(ddl) not in all_tables[table_name]['ddls']:
                    all_tables[table_name]['ddls'].append(clean_ddl(ddl))
                all_tables[table_name]['sources'].append(f"{os.path.relpath(path, PROJECT_ROOT)}:{line_no}")

    # 处理 file_repo 动态表（project_files）
    fr_path = app_dir / "repositories" / "file_repo.py"
    with open(fr_path) as f:
        fr_content = f.read()
    fr_m = re.search(r'table_name\s*:\s*str\s*=\s*["\'](\w+)["\']', fr_content)
    if fr_m:
        fr_table = fr_m.group(1)
        dyn_m = re.search(r'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+\{cls\.\w+\}\s*\(',
                          fr_content)
        if dyn_m:
            start = dyn_m.start()
            i = fr_content.index('(', start)
            depth = 0
            j = i
            in_dq = False
            while j < len(fr_content):
                if fr_content[j] == '"' and (j == 0 or fr_content[j-1] != '\\'):
                    in_dq = not in_dq
                if not in_dq and fr_content[j] == '(':
                    depth += 1
                elif not in_dq and fr_content[j] == ')':
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            fr_ddl = fr_content[start:j+1].strip()
            fr_ddl = fr_ddl.replace('{cls.table_name}', fr_table)
            if fr_table not in all_tables:
                all_tables[fr_table] = {'ddls': [], 'sources': [], 'db': 'tga.db'}
            if clean_ddl(fr_ddl) not in all_tables[fr_table]['ddls']:
                all_tables[fr_table]['ddls'].append(clean_ddl(fr_ddl))
            all_tables[fr_table]['sources'].append(
                'app/repositories/file_repo.py (dynamic)')

    # 纳入 override 表（权威 DDL 单版本 + 已收集来源）
    for t in _OVERRIDE_DDL:
        if t not in all_tables:
            all_tables[t] = {'ddls': [], 'sources': [], 'db': 'tga.db'}
        # 保证 override 表只有一个权威 DDL
        all_tables[t]['ddls'] = [clean_ddl(_OVERRIDE_DDL[t])]
    # 归一化：保证输出不依赖 os.walk 的文件/目录扫描顺序（幂等关键）。
    # 每个表的 sources 显式按「相对路径:行号」排序去重，使 --update 无论
    # 在哪台机器 / 何种扫描顺序下对 TABLE_SOURCES 都产生一致顺序。
    # （同名表各来源文件对 db 的探测结果一致，故 LOGICAL_DB_MAP 亦不受影响。）
    for t in all_tables:
        info = all_tables[t]
        info['sources'] = sorted(set(info['sources']))
    return all_tables


def audit(all_tables: dict) -> dict:
    """生成审计报告。"""
    duplicates = [t for t, info in all_tables.items() if len(info['sources']) > 1]
    conflicts = []
    for t, info in sorted(all_tables.items()):
        unique_ddls = set(info['ddls'])
        if len(unique_ddls) > 1:
            conflicts.append({
                "table": t,
                "variant_count": len(unique_ddls),
                "sources": info['sources'],
            })
    return {
        "total_tables": len(all_tables),
        "duplicates": sorted(duplicates),
        "conflicts": conflicts,
    }


# ── 生成 schema_registry.py ────────────────────────────────
_HEADER = '''\
"""
Schema Registry：统一管理所有数据库表结构声明（Phase D · 地基）。

⚠ 本文件由 scripts/sync_schema_registry.py 自动生成，请勿手工编辑。

单一来源约定：
  - 所有表：唯一权威来源是「模块内联的 CREATE TABLE」，本文件据此自动生成。
    修改某模块表结构后执行 scripts/sync_schema_registry.py --update 重新生成；
    CI 以 --check 校验漂移。
  - 跨模块共享表（api_definitions）已在各模块代码中收敛为同一 DDL，此处仅记录来源。

用途：
  1. 作为表结构的唯一可查清单（审计 / 漂移检测）
  2. 供 Alembic 迁移基线生成时参考
  3. 为 Repository 层与未来 ORM 迁移提供 DDL 出处
"""

# ── 表来源映射 ───────────────────────────────────────────────
# {table_name: ["file:line", ...]}
TABLE_SOURCES: dict = {
'''

_LOGICAL_HEADER = '''\
}

# ── 逻辑库映射 ───────────────────────────────────────────────
# 大部分逻辑库（auth.db / apitest.db 等）经 app.db 统一映射到 tga.db。
LOGICAL_DB_MAP: dict = {
'''

_DDL_HEADER = '''\
}

# ── 表结构 DDL 常量 ─────────────────────────────────────────
# 命名规范：DDL_<表名大写>；同名表多个不同版本以 _V2/_V3… 后缀区分。
# ⚠ 由 sync_schema_registry.py 从各模块内联 DDL 自动提取，勿手工维护。

'''

_TABLE_DDL_HEADER = '''\
# ── 统一注册表 ────────────────────────────────────────────
# {table_name: DDL 常量}，同名冲突时默认取第一个来源的 DDL（V1）。
TABLE_DDL: dict = {
'''

_TABLE_DDL_ALL_HEADER = '''\
}

# 同名表的多版本 DDL（用于冲突检测 / Alembic 决策）
TABLE_DDL_ALL: dict = {
'''

_FUNCS = '''\
}


# ── 工具函数 ───────────────────────────────────────────────

def get_table_ddl(table_name: str) -> str:
    """返回指定表的默认 DDL 声明（空串表示未注册）。"""
    return TABLE_DDL.get(table_name, "")


def list_all_tables() -> list:
    """返回按字典序排序的全部已注册表名。"""
    return sorted(TABLE_DDL.keys())


def get_table_sources(table_name: str) -> list:
    """返回指定表在代码中的来源文件与行号列表。"""
    return TABLE_SOURCES.get(table_name, [])


def get_duplicate_tables() -> list:
    """返回代码中出现多次的同名表清单。"""
    return [t for t, s in TABLE_SOURCES.items() if len(s) > 1]


def ensure_schema_consistent() -> list:
    """检查同名表是否有冲突 schema，返回冲突清单。"""
    conflicts = []
    for t in sorted(TABLE_SOURCES.keys()):
        all_variants = TABLE_DDL_ALL.get(t, [])
        unique_ddls = set(all_variants)
        if len(unique_ddls) > 1:
            conflicts.append({
                "table": t,
                "variant_count": len(unique_ddls),
                "sources": TABLE_SOURCES.get(t, []),
            })
    return conflicts


def audit_all_schemas() -> dict:
    """汇总注册表状态：表数量 / 重复表 / 冲突表。"""
    return {
        "total_tables": len(TABLE_DDL),
        "duplicates": get_duplicate_tables(),
        "conflicts": ensure_schema_consistent(),
    }


__all__ = [
    "TABLE_DDL", "TABLE_DDL_ALL", "TABLE_SOURCES", "LOGICAL_DB_MAP",
    "get_table_ddl", "list_all_tables", "get_table_sources",
    "get_duplicate_tables", "ensure_schema_consistent", "audit_all_schemas",
]
'''


def _upper_ident(table_name: str) -> str:
    return re.sub(r'[^A-Z0-9]', '_', table_name.upper())

def _existing_const_order() -> list:
    """返回当前 schema_registry.py 中 DDL 常量的既有顺序（便于增量更新）。"""
    if not _REGISTRY_PATH.exists():
        return []
    text = _REGISTRY_PATH.read_text(encoding="utf-8")
    return re.findall(r'^(DDL_[A-Z0-9_]+)\s*=\s*"""', text, re.M)


def build_registry_source(all_tables: dict) -> str:
    """根据扫描结果生成 schema_registry.py 完整源码。"""
    tables = sorted(all_tables.keys())

    # TABLE_SOURCES
    src_lines = []
    for t in tables:
        entries = ", ".join(f'"{s}"' for s in all_tables[t]['sources'])
        src_lines.append(f'    "{t}": [{entries}],')
    sources_block = "\n".join(src_lines)

    # LOGICAL_DB_MAP
    db_lines = [f'    "{t}": "{all_tables[t]["db"]}",' for t in tables]
    logical_block = "\n".join(db_lines)

    # DDL 常量（每表每个唯一变体一个常量；首个用 DDL_<表>，其余 _V2/_V3…）
    const_defs = {}          # name -> (table, ddl_text)
    table_variant_names = {}  # table -> [const names]
    for t in tables:
        variants = list(dict.fromkeys(all_tables[t]['ddls']))
        names = []
        for i, ddl in enumerate(variants):
            name = f'DDL_{_upper_ident(t)}' if i == 0 else f'DDL_{_upper_ident(t)}_V{i+1}'
            names.append(name)
            const_defs[name] = ddl
        table_variant_names[t] = names

    # 常量顺序：优先沿用既有 registry 的声明顺序（减少无谓 diff）；
    # 新增常量按字母序追加。
    order = _existing_const_order()
    const_lines = []
    for name in order:
        if name in const_defs:
            const_lines.append(f'{name} = """\n{const_defs[name]}\n"""\n')
    for name in sorted(const_defs.keys() - set(order)):
        const_lines.append(f'{name} = """\n{const_defs[name]}\n"""\n')
    ddl_block = "\n".join(const_lines)

    # TABLE_DDL / TABLE_DDL_ALL
    tddl_lines = []
    tddla_lines = []
    for t in tables:
        names = table_variant_names[t]
        tddl_lines.append(f'    "{t}": {names[0]},')
        tddla_lines.append(f'    "{t}": [{", ".join(names)}],')
    table_ddl_block = "\n".join(tddl_lines)
    table_ddl_all_block = "\n".join(tddla_lines)

    return (
        _HEADER + sources_block + "\n" + _LOGICAL_HEADER + logical_block
        + "\n" + _DDL_HEADER + ddl_block + _TABLE_DDL_HEADER + table_ddl_block
        + "\n" + _TABLE_DDL_ALL_HEADER + table_ddl_all_block + "\n" + _FUNCS
    )


def main():
    parser = argparse.ArgumentParser(description="Schema Registry 采集脚本")
    parser.add_argument("--check", action="store_true",
                        help="内容级校验：registry 与当前模块内联 DDL 是否漂移（CI 用）")
    parser.add_argument("--update", action="store_true",
                        help="根据模块内联 DDL 重新生成 schema_registry.py")
    parser.add_argument("--check-fields", action="store_true",
                        help="审计时间戳/软删除/JSON 字段规范统一性")
    parser.add_argument("--check-alter", action="store_true",
                        help="检查运行时 ALTER 添加列是否已收敛进 CREATE TABLE DDL")
    args = parser.parse_args()

    all_tables = collect_all_tables()
    report = audit(all_tables)

    print(f"发现 {report['total_tables']} 张唯一表, "
          f"{len(report['duplicates'])} 张多来源表, "
          f"{len(report['conflicts'])} 处 schema 冲突")
    for c in report['conflicts']:
        print(f"  ⚠ 冲突: {c['table']} "
              f"({c['variant_count']} 版本): {', '.join(c['sources'])}")

    generated = build_registry_source(all_tables)

    # 检查运行时 ALTER 列漂移（对所有模式生效）
    alter_findings = check_alter_column_drift(all_tables)
    if alter_findings:
        print("\n⚠ ALTER 补列漂移检测：发现以下列未收敛进 CREATE TABLE（会导致"
              " Alembic 新库缺列）：")
        for fnd in alter_findings:
            print(fnd)

    if args.update:
        if alter_findings:
            print("\n✗ --update 已中止：请先在模块 CREATE TABLE 中补齐 ALTER"
                  " 添加的列，再重新执行 --update。")
            return 1
        _REGISTRY_PATH.write_text(generated, encoding="utf-8")
        print(f"✓ 已重新生成 {_REGISTRY_PATH}")
        # 生成后做一次一致性自检
        return 0

    if args.check:
        if alter_findings:
            print("\n✗ ALTER 补列漂移：请修复模块 CREATE TABLE 后重新执行 --update。")
            return 1
        if not _REGISTRY_PATH.exists():
            print(f"✗ 未找到 {_REGISTRY_PATH}，请先执行 --update")
            return 1
        committed = _REGISTRY_PATH.read_text(encoding="utf-8")
        if committed == generated:
            print("✓ schema_registry 与当前模块内联 DDL 一致，无漂移")
            return 0
        print("\n⚠ 检测到漂移：registry 与模块内联 DDL 不一致，请执行 "
              "`python3 scripts/sync_schema_registry.py --update` 收敛：")
        diff = difflib.unified_diff(
            committed.splitlines(), generated.splitlines(),
            fromfile="schema_registry.py (当前)", tofile="schema_registry.py (期望)",
            lineterm="")
        for line in diff:
            print("  " + line)
        return 1

    if args.check_alter:
        if not alter_findings:
            print("✓ ALTER 补列漂移检测通过：所有运行时 ALTER 添加的列均已收敛进"
                  " CREATE TABLE DDL。")
            return 0
        return 1

    if args.check_fields:
        findings = check_field_conventions(all_tables)
        if findings:
            print("\n字段规范审计 时间戳/软删除/JSON:")
            for fnd in findings:
                print(fnd)
            print(f"\n⚠ 发现 {len(findings)} 处字段规范偏离")
            print("规范：created_at/updated_at + deleted/deleted_at + JSON 存 TEXT")
            return 1
        print("✓ 时间戳 / 软删除 / JSON 字段规范一致")
        return 0

    print("未指定操作：--check 校验漂移 / --check-alter 校验 ALTER 列漂移 / "
          "--update 重新生成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
