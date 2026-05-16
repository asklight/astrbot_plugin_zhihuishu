"""智慧树 Cookie 持久化与校验模块。"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Optional

import requests

import config


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def save_cookie(session: requests.Session, path: str) -> None:
    """保存 session cookies 到 JSON 文件。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(session.cookies.get_dict(), f, indent=2, ensure_ascii=False)


def save_cookie_from_config(cookie_json_str: str, path: str) -> bool:
    """从配置 JSON 字符串解析 cookie 并写入文件。

    先尝试标准 JSON 解析；失败则合并多行为一行再试。
    """
    if not cookie_json_str or not cookie_json_str.strip():
        return False

    candidates = [cookie_json_str]
    # 如果原始 JSON 解析失败，尝试去掉内部换行再解析
    stripped = "".join(line.strip() for line in cookie_json_str.splitlines() if line.strip())
    if stripped != cookie_json_str:
        candidates.append(stripped)

    for s in candidates:
        try:
            data = json.loads(s)
            if isinstance(data, dict) and data:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                return True
        except (json.JSONDecodeError, Exception):
            continue

    return False


def load_cookie(session: requests.Session, path: str) -> bool:
    """加载 JSON cookies 到 session，成功返回 True。"""
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict) or not data:
                return False
            session.cookies.update(data)
            return True
    except Exception:
        return False


def _utc_iso_now() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def verify_login(session: requests.Session) -> bool:
    """校验当前 session 是否有效。"""
    try:
        uuid = get_uuid(session)
        if not uuid:
            return False
        resp = session.get(
            config.HOMEWORK_LIST_URL,
            params={"uuid": uuid, "date": _utc_iso_now()},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("status") == "200" and data.get("rt") is not None
    except Exception:
        return False


def get_uuid(session: requests.Session) -> Optional[str]:
    """获取用户 uuid（rt.username）。"""
    # 方式1: 通过 API
    try:
        ts = int(time.time() * 1000)
        resp = session.get(config.VERIFY_URL, params={"dateFormate": ts}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rt = data.get("rt") or {}
        username = rt.get("username")
        if username:
            return username
    except Exception:
        pass

    # 方式2: exitRecod_ cookie（旧版）
    try:
        for key in session.cookies.keys():
            if isinstance(key, str) and key.startswith("exitRecod_"):
                value = key.replace("exitRecod_", "", 1).strip()
                if value:
                    return value
    except Exception:
        pass

    # 方式3: CASLOGC cookie（新版 CAS 登录），URL 编码的 JSON 含 uuid
    try:
        from urllib.parse import unquote
        caslogc = session.cookies.get("CASLOGC")
        if caslogc:
            decoded = unquote(caslogc)
            data = json.loads(decoded)
            uuid = data.get("uuid")
            if uuid:
                return str(uuid)
    except Exception:
        pass

    return None
