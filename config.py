import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "8775952063:AAGj7OxT_7D2sfUrPUVf5PUO_5pRH09LvIU")

# Telegram ID được dùng bot. Để [] = ai cũng dùng được.
ADMIN_IDS: list[int] = []

# Check mỗi X giây (60 = 1 phút)
CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL", "60"))

DB_PATH: str = "ig_monitor.db"
