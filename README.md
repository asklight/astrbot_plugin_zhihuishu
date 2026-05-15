# astrbot_plugin_zhihuishu

智慧树（zhihuishu.com）待提交作业/考试提醒插件 for [AstrBot](https://github.com/AstrBotDevs/AstrBot)。

自动检查智慧树平台上的待提交作业和考试，支持即时查询与每日定时推送。

---

## 功能

- **即时查询**：发送 `/zhihuishu` 立即获取当前未完成作业/考试列表
- **定时推送**：通过指令设置每日固定时间自动推送提醒
- **去重缓存**：已提醒且截止时间未变的任务不会重复推送
- **Cookie 复用**：登录态持久化，减少重复登录

---

## 安装

### 方式一：通过插件市场（推荐）

在 AstrBot 管理面板的插件市场中搜索 `astrbot_plugin_zhihuishu` 并安装。

### 方式二：手动安装

1. 将本仓库克隆或下载到 AstrBot 的插件目录：
   ```
   AstrBot/data/plugins/astrbot_plugin_zhihuishu/
   ```
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 重启 AstrBot。

---

## 前置条件

### 1. 获取智慧树 Cookie

本插件需要有效的智慧树登录 Cookie。如果你已有原 `zhihuishu-notifier` 项目的 cookie：

```bash
# 复制原项目的 cookie.json 到插件数据目录
cp /path/to/zhihuishu-notifier/data/cookie.json \
   /path/to/AstrBot/data/plugins/astrbot_plugin_zhihuishu/data/cookie.json
```

如果没有，需要先用原脚本或其他方式完成微信扫码登录，获取 cookie.json。

### 2. 可选：复制缓存文件

复制原缓存可避免首次运行时全部任务被判定为"新增"：

```bash
cp /path/to/zhihuishu-notifier/data/homework_cache.json \
   /path/to/AstrBot/data/plugins/astrbot_plugin_zhihuishu/data/homework_cache.json
```

---

## 配置

插件首次加载时会自动在数据目录创建 `plugin_config.json`（路径：`data/plugins/astrbot_plugin_zhihuishu/data/plugin_config.json`），你可以：

### 方式一：通过指令修改（推荐）

```
/zhihuishu config                  # 查看当前配置
/zhihuishu config headless false   # 关闭无头模式
/zhihuishu config qrcode_timeout 150
```

### 方式二：直接编辑配置文件

手动编辑 `data/plugin_config.json`：

```json
{
  "zhs_username": "",
  "zhs_password": "",
  "headless": true,
  "cookie_file": "cookie.json",
  "cache_file": "homework_cache.json",
  "qrcode_timeout": 120
}
```

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `zhs_username` | string | `""` | 智慧树账号（可选，用于自动填充登录页） |
| `zhs_password` | string | `""` | 智慧树密码（可选） |
| `headless` | bool | `true` | 浏览器无头模式。服务器建议 `true`，本地可设 `false` |
| `cookie_file` | string | `cookie.json` | Cookie 文件相对路径（相对于插件数据目录） |
| `cache_file` | string | `homework_cache.json` | 缓存文件相对路径 |
| `qrcode_timeout` | int | `120` | 扫码超时秒数 |

---

## 指令

```
/zhihuishu                   # 立即检查并返回作业列表
/zhihuishu set <HH:MM>       # 设置每天定时推送时间，如 /zhihuishu set 08:00
/zhihuishu cancel            # 取消定时推送
/zhihuishu status            # 查看登录状态和定时设置
/zhihuishu config            # 查看当前插件配置
/zhihuishu config <key> <val> # 修改配置，如 /zhihuishu config headless false
```

**定时推送说明**：设置推送时间时，插件会自动记录当前会话来源（群/私聊），到点后向同一位置推送。

---

## 项目结构

```
astrbot_plugin_zhihuishu/
├── main.py              # 插件入口（指令注册、定时任务）
├── auth.py              # Cookie 持久化与微信扫码登录
├── crawler.py           # 智慧树作业/考试爬取
├── cache.py             # 本地缓存与去重
├── config.py            # 配置模块
├── notifier.py          # 通知模块（简化版）
├── conf_schema.json     # AstrBot 配置面板定义
├── metadata.yaml        # 插件元数据
├── requirements.txt     # Python 依赖
└── README.md            # 本文件
```

---

## 依赖

- Python 3.10+
- requests
- beautifulsoup4 + lxml
- DrissionPage（浏览器自动化）
- Pillow

---

## 注意事项

1. **Cookie 有效期**：一次扫码登录的 Cookie 通常可用数周。如果 `/zhihuishu status` 显示登录失效，需要重新获取 Cookie。
2. **Chrome/Chromium**：运行环境需有可用的 Chrome 或 Chromium 浏览器（DrissionPage 依赖）。
3. **服务器部署**：建议 `headless=true`，首次登录建议在本地完成后再上传 Cookie。
4. **检查频率**：目前仅支持每日定时推送一次。如需更频繁检查，可手动多次调用 `/zhihuishu`。

---

## 许可证

MIT License
