"""项目配置模块。"""

import os

# 动态配置（由 main.py 初始化时更新）
ZHS_USERNAME = ""
ZHS_PASSWORD = ""
HEADLESS = True
COOKIE_FILE = "data/cookie.json"
CACHE_FILE = "data/homework_cache.json"
QRCODE_TIMEOUT_SECONDS = 120
DATA_DIR = "data"

# 保留空值兼容 auth.py 中的 notifier 调用（不再实际使用）
WXPUSHER_APP_TOKEN = ""
WXPUSHER_UID = ""
CHECK_INTERVAL_HOURS = 6

# 智慧树接口（不要修改）
LOGIN_URL = "https://passport.zhihuishu.com/login"
VERIFY_URL = "https://hike-examstu.zhihuishu.com/zhsathome/getLoginUserInfo"
ONLINE_HOME_URL = "https://onlineweb.zhihuishu.com/onlinestuh5"
HOMEWORK_LIST_URL = "https://hike-examstu.zhihuishu.com/zhsathome/homework/findImportantReminderList"
HOMEWORK_DETAIL_URL = "https://onlineservice.zhihuishu.com/gateway/f/v1/student/homework/homeworkDirGet2"
HOMEWORK_STATUS_URL = "https://onlineservice.zhihuishu.com/gateway/f/v1/student/homework/Info"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def update_config(plugin_config: dict, data_dir: str = "") -> None:
    """从 AstrBot 配置更新本模块配置。"""
    global HEADLESS, COOKIE_FILE, CACHE_FILE, QRCODE_TIMEOUT_SECONDS, DATA_DIR

    HEADLESS = plugin_config.get("headless", HEADLESS)
    QRCODE_TIMEOUT_SECONDS = plugin_config.get("qrcode_timeout", QRCODE_TIMEOUT_SECONDS)

    if data_dir:
        DATA_DIR = data_dir
        os.makedirs(DATA_DIR, exist_ok=True)

    if plugin_config.get("cookie_file"):
        cookie = plugin_config["cookie_file"]
        COOKIE_FILE = os.path.join(DATA_DIR, cookie) if not os.path.isabs(cookie) else cookie
    elif data_dir:
        COOKIE_FILE = os.path.join(DATA_DIR, "cookie.json")

    if plugin_config.get("cache_file"):
        cache = plugin_config["cache_file"]
        CACHE_FILE = os.path.join(DATA_DIR, cache) if not os.path.isabs(cache) else cache
    elif data_dir:
        CACHE_FILE = os.path.join(DATA_DIR, "homework_cache.json")
