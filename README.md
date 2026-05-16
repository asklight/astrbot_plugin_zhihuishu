# astrbot_plugin_zhihuishu

智慧树（zhihuishu.com）作业/考试提醒插件 for [AstrBot](https://github.com/AstrBotDevs/AstrBot)。

自动检查智慧树平台待提交作业和考试，支持即时查询与每日定时推送。

---

## 安装

AstrBot 管理面板 → 插件市场 → 搜索 `astrbot_plugin_zhihuishu` → 安装。

---

## 使用

### 第一步：获取 Cookie

1. 电脑浏览器打开 [智慧树](https://passport.zhihuishu.com/login) 并微信扫码登录
2. 登录后按 F12 → Application → Cookies → 复制智慧树站点所有 cookie
3. 整理成 JSON 格式，例如：
   ```json
   {"token":"xxx","SESSION":"yyy","GSSESSIONID":"zzz"}
   ```

### 第二步：填入 AstrBot

管理面板 → 插件配置 → `astrbot_plugin_zhihuishu` → 粘贴到 `cookie` 字段 → 保存。

然后在聊天窗口执行：

```
/zhihuishu cookie
```

### 第三步：检查作业

```
/zhihuishu
```

---

## 指令

| 指令 | 说明 |
|------|------|
| `/zhihuishu` | 立即检查所有未完成作业 |
| `/zhihuishu cookie` | 从管理面板配置同步 Cookie 到文件 |
| `/zhihuishu set 08:00` | 每天 8:00 自动推送（仅显示最近 5 条） |
| `/zhihuishu cancel` | 取消定时推送 |
| `/zhihuishu status` | 查看登录状态和定时设置 |

---

## Cookie 过期

当 `/zhihuishu` 提示 `Cookie 无效` 时，重复第一步和第二步即可，无需重启。

---

## 许可证

MIT
