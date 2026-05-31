import os

BOT_TOKEN         = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Giới hạn user dùng bot. Để [] = ai cũng dùng được.
ADMIN_IDS: list[int] = []

# Check mỗi X giây (60 = 1 phút)
CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL", "60"))

DB_PATH: str = os.getenv("DB_PATH", "ig_monitor.db")
