"""智慧树 Cookie 持久化与微信扫码登录模块（Playwright / Firefox）。"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from playwright.sync_api import sync_playwright

import config
import notifier


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

    try:
        for key in session.cookies.keys():
            if isinstance(key, str) and key.startswith("exitRecod_"):
                value = key.replace("exitRecod_", "", 1).strip()
                if value:
                    return value
    except Exception:
        pass

    return None


# ═══════════════════════════════════════════════════════════════════════════
#  Playwright 浏览器自动化（替代 DrissionPage）
# ═══════════════════════════════════════════════════════════════════════════

def _fill_credentials(page) -> None:
    if config.ZHS_USERNAME:
        try:
            page.locator(
                'xpath=//input[contains(@placeholder,"账号") or contains(@placeholder,"手机号") or contains(@placeholder,"用户名")]'
            ).fill(config.ZHS_USERNAME)
        except Exception:
            pass
    if config.ZHS_PASSWORD:
        try:
            page.locator(
                'xpath=//input[contains(@type,"password") or contains(@placeholder,"密码")]'
            ).fill(config.ZHS_PASSWORD)
        except Exception:
            pass


def _click_wechat_login(page) -> bool:
    selectors = [
        'xpath=//a[contains(@class,"wechat") or contains(text(),"微信")]',
        'xpath=//div[contains(@class,"wechat") or contains(text(),"微信")]',
        'xpath=//span[contains(text(),"微信")]',
    ]
    for sel in selectors:
        try:
            page.click(sel, timeout=3000)
            return True
        except Exception:
            continue
    return False


def _capture_qrcode(page, qrcode_path: str) -> None:
    try:
        el = page.wait_for_selector(
            'xpath=//div[contains(@class,"qrcode") or contains(@class,"wxLogin")]',
            timeout=10000,
        )
        if el:
            time.sleep(1)
            el.screenshot(path=qrcode_path)
            return
    except Exception:
        pass
    page.screenshot(path=qrcode_path)


def _build_session_from_context(context) -> Optional[requests.Session]:
    """从 Playwright context 收集所有 cookies 构建 requests.Session。
    Playwright context.cookies() 包含所有域 + HTTPOnly cookie，无需 CDP。"""
    try:
        raw = context.cookies()
        if not raw:
            return None

        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        for c in raw:
            session.cookies.set(
                c["name"], c["value"],
                domain=c.get("domain", ""),
                path=c.get("path", "/"),
            )
        return session
    except Exception:
        return None


def _try_valid_session(context, page, cookie_path: str,
                       app_token: str, uid: str) -> Optional[requests.Session]:
    session = _build_session_from_context(context)
    if not session:
        return None

    if verify_login(session):
        save_cookie(session, cookie_path)
        notifier.push_login_success(app_token, uid)
        return session

    if set(session.cookies.keys()).intersection({"GSSESSIONID", "SESSION", "JSESSIONID", "CASTGC"}):
        save_cookie(session, cookie_path)
        notifier.push_login_success(app_token, uid)
        return session

    return None


def _try_fallback_session(context, page, cookie_path: str,
                          app_token: str, uid: str) -> Optional[requests.Session]:
    session = _build_session_from_context(context)
    if not session:
        return None

    if session.cookies.keys():
        save_cookie(session, cookie_path)
        notifier.push_login_success(app_token, uid)
        return session

    return None


def _try_any_session(context, page, cookie_path: str,
                     app_token: str, uid: str) -> Optional[requests.Session]:
    session = _try_valid_session(context, page, cookie_path, app_token, uid)
    return session or _try_fallback_session(context, page, cookie_path, app_token, uid)


def _login_progressed(page) -> bool:
    try:
        if "passport.zhihuishu.com" not in page.url:
            return True

        for p in page.context.pages:
            try:
                if "passport.zhihuishu.com" not in p.url:
                    return True
            except Exception:
                continue

        try:
            page.wait_for_selector(
                'xpath=//div[contains(@class,"scan") or contains(@class,"success") '
                'or contains(text(),"扫码成功") or contains(text(),"已扫描") or contains(text(),"已登录")]',
                timeout=1000,
            )
            return True
        except Exception:
            return False
    except Exception:
        return False


def _goto_online_home(page) -> None:
    selectors = [
        'xpath=//a[contains(text(),"我的学堂") or contains(@href,"onlinestuh5")]',
        'xpath=//span[contains(text(),"我的学堂")]',
        'xpath=//div[contains(text(),"我的学堂")]',
    ]
    for sel in selectors:
        try:
            page.click(sel, timeout=2000)
            time.sleep(2)
            return
        except Exception:
            continue
    try:
        page.goto(config.ONLINE_HOME_URL)
        time.sleep(2)
    except Exception:
        pass


def _sync_domains(page) -> bool:
    try:
        _goto_online_home(page)
        page.goto(config.ONLINE_HOME_URL)
        time.sleep(2)
        page.goto("https://www.zhihuishu.com")
        time.sleep(1)
        page.goto("https://hike-examstu.zhihuishu.com")
        time.sleep(1)
        page.goto("https://onlineservice.zhihuishu.com")
        time.sleep(2)
        return True
    except Exception:
        return False


def _browser_verify(page) -> bool:
    try:
        ts = int(time.time() * 1000)
        page.goto(f"{config.VERIFY_URL}?dateFormate={ts}")
        time.sleep(1)
        text = page.content()
        data = json.loads(text) if text.strip().startswith("{") else None
        return isinstance(data, dict) and data.get("status") == "200"
    except Exception:
        return False


def _debug_snapshot(page, label: str, app_token: str, uid: str) -> None:
    try:
        os.makedirs(config.DATA_DIR, exist_ok=True)
        path = os.path.join(config.DATA_DIR, f"debug_{label}.png")
        page.screenshot(path=path)
        title = page.evaluate("document.title")
        url = page.url
        print(f"[DEBUG] 当前页面: title={title} url={url}")
        notifier.push_image(path, f"扫码状态截图\nTitle: {title}\nURL: {url}", app_token, uid)
    except Exception:
        pass


def _debug_cookie_state(context, page, label: str, app_token: str, uid: str) -> None:
    try:
        raw = context.cookies()
        names = [c.get("name") for c in raw if c.get("name")]
        summary = (
            f"Cookie 调试({label})\n"
            f"count: {len(raw)}\n"
            f"names: {', '.join(names[:20])}"
        )
        print("[DEBUG]", summary)
        notifier.push_text("Cookie 调试", summary, app_token, uid)
    except Exception:
        pass


def _handle_progress(context, page, cookie_path, app_token, uid,
                     synced: bool, snapshotted: bool):
    if not synced:
        synced = _sync_domains(page) or synced

    if not snapshotted:
        _debug_snapshot(page, "progress", app_token, uid)
        snapshotted = True

    _browser_verify(page)
    session = _try_any_session(context, page, cookie_path, app_token, uid)
    return session, synced, snapshotted


def _wait_for_login(context, page, cookie_path: str,
                    app_token: str, uid: str, timeout: int) -> Optional[requests.Session]:
    start = time.time()
    synced = False
    snapshotted = False
    last_sync_at = 0.0
    while time.time() - start < timeout:
        progressed = _login_progressed(page)
        if progressed or (time.time() - last_sync_at >= 8):
            session, synced, snapshotted = _handle_progress(
                context, page, cookie_path, app_token, uid, synced, snapshotted,
            )
            last_sync_at = time.time()
            if session:
                return session

        session = _try_any_session(context, page, cookie_path, app_token, uid)
        if session:
            return session

        time.sleep(3)

    _debug_snapshot(page, "timeout", app_token, uid)
    _debug_cookie_state(context, page, "timeout", app_token, uid)
    notifier.push_login_timeout(app_token, uid)
    return None


def _show_qrcode(path: str) -> None:
    try:
        if os.name == "nt" and os.path.exists(path):
            os.startfile(path)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════
#  公开 API
# ═══════════════════════════════════════════════════════════════════════════

def prepare_qrcode(headless: bool = True, data_dir: str = "data"):
    """打开 Firefox、进入登录页、点击微信登录、截图二维码。

    返回 (playwright_objects, qrcode_path) 或 (None, error_msg)。
    playwright_objects = (playwright, browser, context, page)。
    调用者负责将 qrcode_path 发给用户，然后调用 complete_login()。
    """
    try:
        p = sync_playwright().start()
        browser = p.firefox.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        page.goto(config.LOGIN_URL)
        time.sleep(2)

        _fill_credentials(page)

        if not _click_wechat_login(page):
            browser.close()
            p.stop()
            return None, "未找到微信登录入口，登录页面结构可能已变更。"

        time.sleep(2)

        os.makedirs(data_dir, exist_ok=True)
        qrcode_path = os.path.join(data_dir, "qrcode.png")
        _capture_qrcode(page, qrcode_path)
        _show_qrcode(qrcode_path)

        return (p, browser, context, page), qrcode_path
    except Exception as e:
        msg = str(e)
        if any(kw in msg.lower() for kw in ("firefox", "browser", "executable", "浏览器", "可执行")):
            msg = (
                f"未找到 Firefox 浏览器。请先执行：\n"
                f"  pip install playwright\n"
                f"  playwright install firefox\n"
                f"原始错误: {msg}"
            )
        return None, msg


def complete_login(playwright_objects, cookie_path: str, timeout: int = 120):
    """等待用户扫码，收集 Cookie 并保存。返回 requests.Session 或 None。"""
    p, browser, context, page = playwright_objects
    try:
        session = _wait_for_login(context, page, cookie_path, "", "", timeout)
        if session is not None:
            save_cookie(session, cookie_path)
        return session
    finally:
        try:
            browser.close()
        except Exception:
            pass
        try:
            p.stop()
        except Exception:
            pass
