"""通知模块简化版（移除 WxPusher，仅保留日志记录）。"""

from __future__ import annotations

from astrbot.api import logger


def _safe_send(content: str, app_token: str, uid: str, content_type: int) -> bool:
    logger.info(f"[通知] {content[:200]}...")
    return True


def push_text(title: str, content: str, app_token: str, uid: str) -> bool:
    """推送文本消息（仅记录日志）。"""
    message = f"## {title}\n\n{content}" if title else content
    logger.info(f"[通知] {message[:200]}...")
    return True


def push_image(image_path: str, caption: str, app_token: str, uid: str) -> bool:
    """推送图片（仅记录日志）。"""
    logger.info(f"[通知图片] {caption}: {image_path}")
    return True


def push_qrcode(image_path: str, app_token: str, uid: str) -> bool:
    """推送登录二维码（仅记录日志）。"""
    logger.info(f"[通知二维码] {image_path}")
    return True


def push_homework_list(
    homeworks: list[dict],
    app_token: str,
    uid: str,
    has_new: bool = True,
    new_count: int = 0,
) -> bool:
    """推送作业提醒列表（仅记录日志）。"""
    logger.info(f"[通知作业] 共 {len(homeworks)} 项, 新增 {new_count} 项")
    return True


def push_login_success(app_token: str, uid: str) -> bool:
    """推送登录成功通知（仅记录日志）。"""
    logger.info("[通知] 登录成功")
    return True


def push_login_timeout(app_token: str, uid: str) -> bool:
    """推送二维码超时通知（仅记录日志）。"""
    logger.info("[通知] 登录超时")
    return True


def push_error(message: str, app_token: str, uid: str) -> bool:
    """推送异常通知（仅记录日志）。"""
    logger.error(f"[通知错误] {message}")
    return True
