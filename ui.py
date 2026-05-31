from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def status_emoji(status: str, verified: bool = False) -> str:
    if status == "die":   return "🔴"
    if status == "live":  return "🔵" if verified else "🟢"
    return "⚪"


def verified_badge(verified) -> str:
    return "🔵 Có tích xanh" if bool(verified) else "⚪ Chưa tích xanh"


def format_account_card(acc: dict) -> str:
    status   = acc.get("status", "unknown")
    verified = bool(acc.get("verified", False))
    s_emoji  = status_emoji(status, verified)
    s_label  = "LIVE" if status == "live" else "DIE" if status == "die" else "UNKNOWN"
    mon_text = "🔄 Đang theo dõi" if acc.get("monitoring") else "⏸ Đã tắt theo dõi"

    lines = [
        f"{s_emoji} <a href=\"https://instagram.com/{acc['username']}\">@{acc['username']}</a> — <b>{s_label}</b>",
        "",
        f"✏️ Ghi chú: {acc.get('note') or '—'}",
        f"👤 Tên: {acc.get('full_name') or '—'}",
        f"{verified_badge(verified)}",
        f"📡 {mon_text}",
        f"📅 Ngày thêm: {acc.get('added_at', '—')}",
        f"🔄 Check cuối: {acc.get('last_check') or acc.get('added_at', '—')}",
    ]
    return "\n".join(lines)


def account_keyboard(account_id: int, monitoring: bool) -> InlineKeyboardMarkup:
    mon_text = "⏸ Tắt theo dõi" if monitoring else "▶️ Bật theo dõi"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Cập nhật ghi chú", callback_data=f"update:{account_id}"),
            InlineKeyboardButton(mon_text,               callback_data=f"toggle_mon:{account_id}"),
        ],
        [
            InlineKeyboardButton("🔍 Check ngay",        callback_data=f"check_now:{account_id}"),
            InlineKeyboardButton("❌ Xóa",               callback_data=f"remove:{account_id}"),
        ],
        [
            InlineKeyboardButton("◀️ Danh sách",         callback_data="list"),
            InlineKeyboardButton("🏠 Menu",              callback_data="menu"),
        ],
    ])


def list_keyboard(accounts: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for acc in accounts:
        s    = status_emoji(acc["status"], bool(acc.get("verified")))
        mon  = " ⏸" if not acc.get("monitoring") else ""
        v    = " 🔵" if acc.get("verified") and acc.get("status") == "live" else ""
        note = f" {acc.get('note')}" if acc.get("note") else ""
        label = f"{s} @{acc['username']}{note}{v}{mon}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"view:{acc['id']}")])
    buttons.append([InlineKeyboardButton("➕ Thêm username", callback_data="add_new")])
    return InlineKeyboardMarkup(buttons)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Thêm username",  callback_data="add_new"),
            InlineKeyboardButton("📋 Danh sách",      callback_data="list"),
        ],
        [
            InlineKeyboardButton("📊 Thống kê",       callback_data="stats"),
            InlineKeyboardButton("🔄 Check tất cả",   callback_data="checkall"),
        ],
    ])
