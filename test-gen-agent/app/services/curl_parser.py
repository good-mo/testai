# -*- coding: utf-8 -*-
"""Curl 命令解析器。

将终端里常见的 `curl` 命令行解析为前端 `CurlParseResult` 期望的结构：
{
    method: str,            # 大写 HTTP 方法
    url: str,
    headers: {key: value},  # 键值对（不含 Cookie 之外需忽略的伪头）
    body: str | dict,       # 请求体
    bodyType: str,          # NONE / FORM_DATA / WWW_FORM / JSON / XML / RAW / BINARY
    queryParams: {key: value},
}

说明：
- 该解析基于 curl 命令行各参数（-X/-d/-H/-F/--data-raw 等）完成，
  不依赖外部 curl 可执行文件，方便在受限沙箱内运行。
- Content-Type 决定 bodyType；未显式提供时按参数类型做最佳推断。
"""
from __future__ import annotations

import json
import re
import shlex
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlsplit, urlunsplit

# curl 常见参数无需额外取值（布尔开关）
_NO_VALUE_FLAGS = {
    "--compressed", "--silent", "-s", "-i", "-I", "--head", "-L", "--location",
    "-k", "--insecure", "-v", "--verbose", "--no-keepalive", "-0", "--http1.1",
    "--http2", "--http3", "-g", "--globoff", "--raw", "--ssl-no-revoke",
}

# 带值参数与 curl 长参数对照
_VALUE_FLAGS = {
    "-X", "--request",
    "-H", "--header",
    "-d", "--data", "--data-raw", "--data-binary", "--data-urlencode",
    "-F", "--form", "--form-string",
    "-u", "--user", "--user-agent", "-A",
    "-b", "--cookie", "-c", "--cookie-jar",
    "-e", "--referer",
    "--connect-timeout", "-m", "--max-time",
    "--url", "-G", "--get",
    "-o", "--output", "-O", "--remote-name",
}

# 携带数据体 / 表单的参数子集（用于方法推断）
_DATA_FLAGS = {
    "-d", "--data", "--data-raw", "--data-binary", "--data-urlencode",
    "-F", "--form", "--form-string",
}
_GET_FLAG = {"-G", "--get"}

# 伪头（curl 内部选项，不应作为业务请求头透传）
_PSEUDO_HEADERS = {"Content-Length", "Connection", "Expect", "Proxy-Connection", "Transfer-Encoding"}


def _detect_content_type(headers: Dict[str, str]) -> str:
    """从请求头中提取小写 content-type（去掉 charset 等附加信息）。"""
    for k, v in headers.items():
        if k.lower() == "content-type":
            return v.split(";")[0].strip().lower()
    return ""


def _split_data_arg(value: str) -> Tuple[str, str]:
    """拆分 --data-urlencode 的参数为 (key, value)。"""
    # 支持 name=content / name@filename / @filename 三种形态
    if value.startswith("@"):
        return "", value
    if "=" in value:
        k, v = value.split("=", 1)
        return k, v
    return "", value


def _parse_data_args(
    data_args: List[Tuple[str, str]],
    headers: Dict[str, str],
) -> Tuple[str, Any]:
    """根据请求头 Content-Type 与数据参数形态，推断 bodyType 并返回 (bodyType, body)。"""
    joined = "&".join(v for _, v in data_args)
    content_type = _detect_content_type(headers)

    is_multipart = any(flag in ("-F", "--form", "--form-string") for flag, _ in data_args)
    if is_multipart:
        body: Dict[str, str] = {}
        for _flag, v in data_args:
            # multipart 字段 name=content 或 name=@file;type=...
            name = v.split("=", 1)[0] if "=" in v else v
            content = v.split("=", 1)[1] if "=" in v else ""
            # 文件形态 name=@path;type=xxx
            if content.startswith("@"):
                content = ""
            body[name] = content
        return "FORM_DATA", body

    if content_type in ("application/json", "application/problem+json", "text/json") or joined.lstrip().startswith(("{", "[")):
        try:
            body = json.loads(joined)
            return "JSON", body
        except Exception:
            return "JSON", joined

    if content_type in ("application/xml", "text/xml") or joined.lstrip().startswith("<"):
        return "XML", joined

    if content_type in ("application/x-www-form-urlencoded",) or any(
        flag in ("-d", "--data", "--data-binary", "--data-urlencode") for flag, _ in data_args
    ):
        # 表单形态：解析为键值对象
        params: Dict[str, str] = {}
        raw_texts: List[str] = []
        for flag, v in data_args:
            if flag == "--data-urlencode":
                k, val = _split_data_arg(v)
                if k:
                    params[k] = val
                else:
                    for pk, pv in parse_qsl(v, keep_blank_values=True):
                        params[pk] = pv
            elif "=" in v:
                # 处理含多个字段的 k1=v1&k2=v2 形态
                matched = False
                for pk, pv in parse_qsl(v, keep_blank_values=True):
                    if pk or pv:
                        params[pk] = pv
                        matched = True
                if not matched:
                    k, val = v.split("=", 1)
                    params[k] = val
            else:
                raw_texts.append(v)
        if params:
            return "WWW_FORM", params
        return "RAW", joined

    # 兜底：原始字符串
    return "RAW", joined


def _strip_quotes(value: str) -> str:
    """去除首尾配对引号。"""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def _tokenize(curl_cmd: str) -> List[str]:
    """将 curl 命令行拆分为 token。

    优先使用 shlex（可正确处理带引号/转义），失败时退化到简单正则切分。
    """
    curl_cmd = curl_cmd.strip()
    # 去掉换行续行符 '\\\n' 方便多行粘贴的 curl 命令解析
    curl_cmd = re.sub(r"\\\s*\n", " ", curl_cmd)
    try:
        tokens = shlex.split(curl_cmd, posix=True)
    except ValueError:
        tokens = re.findall(r'(?:[^\s"\']+|"[^"]*"|\'[^\']*\')+', curl_cmd)
        tokens = [_strip_quotes(t) for t in tokens]
    return tokens


def parse_curl(curl_cmd: str) -> Dict[str, Any]:
    """解析 curl 命令行，返回 CurlParseResult 结构。

    Args:
        curl_cmd: 原始 curl 命令行字符串。

    Returns:
        结构化字典，字段与前端 `CurlParseResult` 对齐。
    """
    result: Dict[str, Any] = {
        "method": "GET",
        "url": "",
        "headers": {},
        "body": None,
        "bodyType": "NONE",
        "queryParams": {},
    }

    tokens = _tokenize(curl_cmd)
    # 定位 curl 命令本身（可能带绝对/相对路径）
    start = 0
    for i, tok in enumerate(tokens):
        if tok == "curl" or (tok.split("/")[-1] == "curl"):
            start = i + 1
            break

    url: Optional[str] = None
    explicit_method: Optional[str] = None
    headers: Dict[str, str] = {}
    data_args: List[Tuple[str, str]] = []
    positionals: List[str] = []

    i = start
    while i < len(tokens):
        tok = tokens[i]
        if tok in _NO_VALUE_FLAGS:
            # --head 等价于 -X HEAD
            if tok in ("-I", "--head"):
                explicit_method = "HEAD"
            i += 1
            continue
        if tok == "--url" or tok == "--get":
            if tok == "--get":
                explicit_method = explicit_method or "GET"
            if i + 1 < len(tokens):
                url = _strip_quotes(tokens[i + 1])
                i += 2
            else:
                i += 1
            continue
        if tok in _VALUE_FLAGS or tok == "-G":
            if tok == "-G":
                explicit_method = "GET"
                i += 1
                continue
            if i + 1 >= len(tokens):
                break
            raw_val = tokens[i + 1]
            val = _strip_quotes(raw_val)
            i += 2
            if tok in ("-X", "--request"):
                explicit_method = val.upper()
            elif tok in ("-H", "--header"):
                header_val = val
                # 处理 -H "Name: value"（可能含多余空格与引号内冒号）
                if ":" in header_val:
                    name, value = header_val.split(":", 1)
                    headers[name.strip()] = value.strip()
                else:
                    # 伪头 / 空头
                    headers[header_val.strip()] = ""
            elif tok in ("-A", "--user-agent"):
                headers["User-Agent"] = val
            elif tok == "-u":
                # Authorization Basic 简易支持：仅作请求头透传提示
                headers["User"] = val
            elif tok == "--url":
                url = val
            elif tok in _DATA_FLAGS:
                data_args.append((tok, val))
            else:
                # 其余带值参数忽略
                pass
            continue
        # 无连字符的普通 token：可能是 URL 或方法
        if tok.startswith("-"):
            # 未知短参数，尝试消费一个值
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                i += 2
            else:
                i += 1
            continue
        positionals.append(_strip_quotes(tok))
        i += 1

    # URL 确定
    if url is None:
        # 第一个非 "-" 且像 URL 的 positional
        for p in positionals:
            if p.startswith("http") or p.startswith("/") or "://" in p:
                url = p
                break
    url = url or ""
    result["url"] = url

    # 从 URL 中拆出 queryParams（仅保留 URL 前缀）
    parsed_url = urlsplit(url)
    query_params: Dict[str, str] = {}
    if parsed_url.query:
        try:
            query_params = dict(parse_qsl(parsed_url.query, keep_blank_values=True))
        except Exception:
            query_params = {}
    # 清理 URL 上的 query 部分，path 保持原样
    clean_url = urlunsplit((parsed_url.scheme, parsed_url.netloc, parsed_url.path, "", parsed_url.fragment))
    if parsed_url.query:
        # 保留原始 url（含 query），但前端需要干净 url + queryParams
        result["url"] = clean_url
    result["queryParams"] = query_params

    # 去除伪头
    filtered_headers = {k: v for k, v in headers.items() if k not in _PSEUDO_HEADERS and k != "User"}
    result["headers"] = filtered_headers

    # 方法推断
    if explicit_method:
        result["method"] = explicit_method
    elif data_args:
        # 根据参数推断
        inferred = None
        for flag, _ in data_args:
            if flag in ("-F", "--form", "--form-string"):
                inferred = "POST"
                break
            inferred = "POST"
        result["method"] = inferred or "POST"
    else:
        result["method"] = "GET"

    # body 解析
    if data_args:
        body_type, body = _parse_data_args(data_args, filtered_headers)
        result["bodyType"] = body_type
        result["body"] = body
    else:
        result["bodyType"] = "NONE"
        result["body"] = None

    # 去除以冒号结尾的伪头处理：确保返回不包含空 content-length 等
    return result


__all__ = ["parse_curl"]
