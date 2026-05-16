# Changelog

## [1.1.0] - 2026-05-16

### Changed
- 移除浏览器自动登录功能，改为在管理面板配置 Cookie JSON
- 管理面板只需填写 `cookie` 一个配置项
- `/zhihuishu cookie` 从配置同步 Cookie 到文件
- 定时推送仅显示截止日期最近的 5 条作业

### Fixed
- 修复 `conf_schema.json` 命名（AstrBot 要求 `_conf_schema.json`）
- 修复子目录 `auth.py` 模块冲突问题
- 修复定时推送消息发送失败问题

## [1.0.0] - 2025-12-01

### Added
- 智慧树作业即时查询 `/zhihuishu`
- 定时推送 `/zhihuishu set` / `cancel`
- 登录状态查看 `/zhihuishu status`
- 微信扫码登录 `/zhihuishu login`（已移除）
