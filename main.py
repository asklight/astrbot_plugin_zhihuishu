"""智慧树作业提醒 AstrBot 插件入口。"""

from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image, Plain
from astrbot.api.star import Context, Star, register

import auth
import cache as cache_module
import config
import crawler


@register("astrbot_plugin_zhihuishu", "asklight", "智慧树作业提醒", "1.0.0")
class ZhihuishuPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.config = config
        self._schedule_task: asyncio.Task | None = None
        self._schedule_data: dict = {}
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        os.makedirs(self.data_dir, exist_ok=True)

    async def initialize(self):
        """插件初始化：读取配置、加载定时设置、启动后台任务。"""
        plugin_config = self._get_plugin_config()
        config.update_config(plugin_config, self.data_dir)

        self._load_schedule()
        self._schedule_task = asyncio.create_task(self._schedule_loop())
        logger.info("[智慧树] 插件已初始化")

    async def terminate(self):
        """插件销毁时取消后台任务。"""
        if self._schedule_task:
            self._schedule_task.cancel()
            try:
                await self._schedule_task
            except asyncio.CancelledError:
                pass
        logger.info("[智慧树] 插件已停止")

    def _get_plugin_config(self) -> dict:
        """读取插件配置。优先 AstrBotConfig，其次 context.config，最后本地 JSON。"""
        # 方式1: AstrBotConfig（AstrBot v4 原生，管理面板写入）
        if self.config is not None and len(self.config) > 0:
            return dict(self.config)

        # 方式2: context.config（旧版兼容）
        try:
            if hasattr(self.context, "config"):
                cfg = self.context.config
                if isinstance(cfg, dict):
                    plugin_cfg = cfg.get("astrbot_plugin_zhihuishu", {})
                    if plugin_cfg:
                        return plugin_cfg
        except Exception:
            pass

        # 方式3: 本地 JSON 文件
        config_path = os.path.join(self.data_dir, "plugin_config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass

        # 方式4: 默认配置
        default_cfg = {
            "headless": True,
            "cookie_file": "cookie.json",
            "cache_file": "homework_cache.json",
            "qrcode_timeout": 120,
        }
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return default_cfg

    def _save_plugin_config(self, cfg: dict):
        """保存插件配置。优先使用 AstrBotConfig，回退到本地 JSON。"""
        if self.config is not None:
            for k, v in cfg.items():
                self.config[k] = v
            try:
                self.config.save_config()
                return
            except Exception as e:
                logger.error(f"[智慧树] AstrBotConfig.save_config() 失败，回退到 JSON: {e}")

        config_path = os.path.join(self.data_dir, "plugin_config.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[智慧树] 保存配置失败: {e}")

    def _schedule_path(self) -> str:
        return os.path.join(self.data_dir, "push_schedule.json")

    def _load_schedule(self):
        path = self._schedule_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._schedule_data = json.load(f)
            except Exception:
                self._schedule_data = {}
        else:
            self._schedule_data = {}

    def _save_schedule(self):
        with open(self._schedule_path(), "w", encoding="utf-8") as f:
            json.dump(self._schedule_data, f, ensure_ascii=False, indent=2)

    def _get_event_umo(self, event: AstrMessageEvent) -> str | None:
        """防御性获取消息来源标识。"""
        # 优先尝试 unified_msg_origin 属性
        umo = getattr(event, "unified_msg_origin", None)
        if umo:
            return umo

        # fallback: 手动构造
        platform = getattr(event, "platform", "unknown")

        sender_id = getattr(event, "sender_id", None)
        if sender_id is None and hasattr(event, "get_sender_id"):
            try:
                sender_id = event.get_sender_id()
            except Exception:
                pass
        if sender_id is None:
            sender_id = getattr(event, "sender", None)
            if sender_id is not None:
                sender_id = getattr(sender_id, "user_id", None)

        group_id = getattr(event, "group_id", None)
        if group_id is None and hasattr(event, "get_group_id"):
            try:
                group_id = event.get_group_id()
            except Exception:
                pass

        if group_id:
            return f"{platform}:GroupMessage:{group_id}"
        if sender_id:
            return f"{platform}:FriendMessage:{sender_id}"
        return None

    async def _send_to_umo(self, umo: str, text: str) -> bool:
        """防御性发送消息到指定 UMO，尝试多种 API。"""
        try:
            from astrbot.api.message_components import Plain
            chain = [Plain(text)]
        except Exception:
            chain = text

        # 方式1: context.send_message
        try:
            if hasattr(self.context, "send_message"):
                await self.context.send_message(umo, chain)
                return True
        except Exception:
            pass

        # 方式2: platform_manager.send_message
        try:
            pm = getattr(self.context, "platform_manager", None)
            if pm and hasattr(pm, "send_message"):
                await pm.send_message(umo, chain)
                return True
        except Exception:
            pass

        # 方式3: bot.send_message
        try:
            bot = getattr(self.context, "bot", None)
            if bot and hasattr(bot, "send_message"):
                await bot.send_message(umo, chain)
                return True
        except Exception:
            pass

        logger.error(f"[智慧树] 无法发送消息，AstrBot API 不兼容，UMO={umo}")
        return False

    async def _schedule_loop(self):
        """后台定时任务：每分钟检查是否到达推送时间。"""
        while True:
            try:
                # 对齐到下一分钟开始，提高精度
                now = datetime.now()
                sleep_seconds = 60 - now.second - now.microsecond / 1_000_000
                if sleep_seconds < 0:
                    sleep_seconds = 60
                await asyncio.sleep(sleep_seconds)

                if not self._schedule_data.get("enabled"):
                    continue

                push_time = self._schedule_data.get("push_time")
                if not push_time:
                    continue

                now = datetime.now()
                current_time = now.strftime("%H:%M")
                today = now.strftime("%Y-%m-%d")

                last_push = self._schedule_data.get("last_push_date")
                if current_time == push_time and last_push != today:
                    umo = self._schedule_data.get("target_umo")
                    if umo:
                        await self._do_push(umo)
                        self._schedule_data["last_push_date"] = today
                        self._save_schedule()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[智慧树] 定时任务异常: {e}")

    async def _do_push(self, unified_msg_origin: str):
        """执行定时推送。"""
        try:
            text = await self._check_homeworks()
            if text:
                await self._send_to_umo(unified_msg_origin, text)
        except Exception as e:
            logger.error(f"[智慧树] 定时推送失败: {e}")

    async def _check_homeworks(self) -> str:
        """执行检查并返回格式化文本。"""
        try:
            session = requests.Session()
            session.headers.update(config.DEFAULT_HEADERS)

            cookie_loaded = auth.load_cookie(session, config.COOKIE_FILE)
            if not cookie_loaded or not auth.verify_login(session):
                return "❌ Cookie 无效或不存在，请先完成登录并确保 cookie.json 已放入插件数据目录。\n路径: " + config.COOKIE_FILE

            uuid = auth.get_uuid(session)
            if not uuid:
                return "❌ 无法获取用户 uuid，请检查登录状态。"

            homeworks = crawler.get_all_homeworks(session, uuid)
            cache = cache_module.load_cache(config.CACHE_FILE)
            to_notify = cache_module.filter_new(homeworks, cache)
            unfinished = [hw for hw in homeworks if not bool(hw.get("is_submitted"))]

            text = self._build_message(unfinished, to_notify)

            updated = cache_module.update_cache(cache, homeworks)
            cache_module.save_cache(updated, config.CACHE_FILE)

            return text

        except Exception as e:
            logger.error(f"[智慧树] 检查作业异常: {e}")
            return f"❌ 检查作业时出错: {str(e)[:200]}"

    def _build_message(self, homeworks: list, to_notify: list | None = None) -> str:
        """构建作业列表消息文本。"""
        if not homeworks:
            return "✅ 当前暂无待提交作业"

        now = datetime.now()
        sorted_items = sorted(homeworks, key=lambda x: x.get("end_time") or datetime.fromtimestamp(0))

        if to_notify:
            lines = [
                "📚 智慧树作业提醒",
                f"本次新增 {len(to_notify)} 项；当前未完成共 {len(sorted_items)} 项。",
                "",
            ]
        else:
            lines = [
                "📚 智慧树作业提醒",
                f"当前未完成共 {len(sorted_items)} 项：",
                "",
            ]

        for hw in sorted_items:
            end_time = hw.get("end_time")
            if not isinstance(end_time, datetime):
                continue

            days = (end_time - now).total_seconds() / 86400
            if days <= 3:
                icon = "🔴"
            elif days <= 7:
                icon = "🟡"
            else:
                icon = "🟢"

            title = str(hw.get("title") or "").strip()
            course_name = str(hw.get("course_name") or "").strip()
            end_text = end_time.strftime("%Y/%m/%d %H:%M")
            days_left = max(0, int(days))
            type_label = str(hw.get("type_label") or "作业")

            lines.append(f"{icon} **{title}** [{type_label}]")
            lines.append(f"  📖 {course_name}")
            lines.append(f"  ⏰ 截止：{end_text}（还剩 {days_left} 天）")

            if int(hw.get("type") or 1) == 1:
                content = str(hw.get("content") or "").strip()
                if content:
                    lines.append(f"  📝 {content[:100]}")

            lines.append("")

        return "\n".join(lines)

    @filter.command("zhihuishu")
    async def zhihuishu(self, event: AstrMessageEvent):
        """智慧树作业提醒主指令。
        /zhihuishu              - 立即检查并返回作业列表
        /zhihuishu login        - 微信扫码登录，保存 Cookie
        /zhihuishu set <HH:MM>  - 设置每天定时推送时间
        /zhihuishu cancel       - 取消定时推送
        /zhihuishu status       - 查看当前状态
        """
        msg = event.message_str.strip()
        parts = msg.split()

        if len(parts) == 1:
            text = await self._check_homeworks()
            yield event.plain_result(text)
            return

        subcmd = parts[1].lower()

        if subcmd == "set":
            if len(parts) < 3:
                yield event.plain_result("用法：/zhihuishu set <HH:MM>，例如 /zhihuishu set 08:00")
                return

            time_str = parts[2].strip()
            if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", time_str):
                yield event.plain_result("时间格式错误，请使用 HH:MM 格式，例如 08:00")
                return

            umo = self._get_event_umo(event)
            if not umo:
                yield event.plain_result("❌ 无法获取消息来源标识，定时推送设置失败。")
                return

            self._schedule_data = {
                "enabled": True,
                "push_time": time_str,
                "target_umo": umo,
                "last_push_date": "",
            }
            self._save_schedule()

            yield event.plain_result(f"✅ 已设置每天 {time_str} 自动推送智慧树作业提醒。")

        elif subcmd == "cancel":
            self._schedule_data = {"enabled": False}
            self._save_schedule()
            yield event.plain_result("✅ 已取消定时推送。")

        elif subcmd == "status":
            status_lines = ["📊 智慧树插件状态", ""]

            try:
                session = requests.Session()
                session.headers.update(config.DEFAULT_HEADERS)
                cookie_ok = auth.load_cookie(session, config.COOKIE_FILE) and auth.verify_login(session)
                status_lines.append(f"登录状态：{'✅ 已登录' if cookie_ok else '❌ 未登录/Cookie失效'}")
            except Exception as e:
                status_lines.append(f"登录状态：❌ 检查失败 ({str(e)[:50]})")

            if self._schedule_data.get("enabled"):
                status_lines.append(f"定时推送：✅ 已启用（每天 {self._schedule_data.get('push_time', '?')}）")
            else:
                status_lines.append("定时推送：❌ 未启用")

            status_lines.append(f"Cookie 文件：{config.COOKIE_FILE}")
            status_lines.append(f"缓存文件：{config.CACHE_FILE}")

            yield event.plain_result("\n".join(status_lines))

        elif subcmd == "login":
            yield event.plain_result("🔑 正在打开智慧树登录页面，请稍候...")

            loop = asyncio.get_event_loop()

            page, qrcode_path = await loop.run_in_executor(
                None,
                auth.prepare_qrcode,
                config.HEADLESS,
                self.data_dir,
            )

            if page is None:
                yield event.plain_result("❌ 无法打开登录页面，请检查服务器是否安装了 Chrome/Chromium 浏览器。")
                return

            try:
                yield event.chain_result([
                    Image(file=qrcode_path),
                    Plain(f"请使用微信扫描二维码登录（{config.QRCODE_TIMEOUT_SECONDS} 秒内）"),
                ])
            except Exception:
                yield event.plain_result(
                    f"请使用微信扫描二维码登录（{config.QRCODE_TIMEOUT_SECONDS} 秒内）。\n"
                    f"二维码已保存到：{qrcode_path}"
                )

            session = await loop.run_in_executor(
                None,
                auth.complete_login,
                page,
                config.COOKIE_FILE,
                config.QRCODE_TIMEOUT_SECONDS,
            )

            if session:
                yield event.plain_result("✅ 登录成功！Cookie 已保存，现在可以 /zhihuishu 检查作业了。")
            else:
                yield event.plain_result("❌ 登录超时或失败，请重新 /zhihuishu login")

        elif subcmd == "config":
            cfg_path = os.path.join(self.data_dir, "plugin_config.json")
            if len(parts) == 2:
                # 显示当前配置
                lines = ["⚙️ 插件配置（编辑路径见下方）", ""]
                lines.append(f"headless: {config.HEADLESS}")
                lines.append(f"cookie_file: {config.COOKIE_FILE}")
                lines.append(f"cache_file: {config.CACHE_FILE}")
                lines.append(f"qrcode_timeout: {config.QRCODE_TIMEOUT_SECONDS}")
                lines.append("")
                lines.append(f"配置文件：{cfg_path}")
                lines.append("用法：/zhihuishu config <key> <value>")
                lines.append("可修改的 key：headless, qrcode_timeout")
                yield event.plain_result("\n".join(lines))
                return

            if len(parts) < 4:
                yield event.plain_result("用法：/zhihuishu config <key> <value>")
                return

            key = parts[2]
            value = " ".join(parts[3:])

            # 读取当前配置
            cfg = self._get_plugin_config()

            if key == "headless":
                cfg[key] = value.lower() in ("true", "1", "yes", "on")
            elif key == "qrcode_timeout":
                try:
                    cfg[key] = int(value)
                except ValueError:
                    yield event.plain_result("qrcode_timeout 必须是整数")
                    return
            else:
                cfg[key] = value

            self._save_plugin_config(cfg)
            config.update_config(cfg, self.data_dir)
            yield event.plain_result(f"✅ 配置已更新：{key} = {cfg[key]}")

        else:
            yield event.plain_result(
                "未知子命令。\n用法：\n"
                "  /zhihuishu              立即检查作业\n"
                "  /zhihuishu login        微信扫码登录\n"
                "  /zhihuishu set <HH:MM>  设置每天推送时间\n"
                "  /zhihuishu cancel       取消定时推送\n"
                "  /zhihuishu status       查看状态\n"
                "  /zhihuishu config       查看/修改插件配置"
            )
