import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from telegram.constants import ParseMode
from config import BOT_TOKEN, CHECK_INTERVAL, ADMIN_IDS, ANTHROPIC_API_KEY
from database import Database
from checker import InstagramChecker
from ui import (
    format_account_card, account_keyboard, list_keyboard,
    main_menu_keyboard, status_emoji, verified_badge
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("ig_monitor.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

db = Database()
checker = InstagramChecker(anthropic_api_key=ANTHROPIC_API_KEY)

WAITING_ADD    = "waiting_add"
WAITING_UPDATE = "waiting_update"


def is_allowed(user_id: int) -> bool:
    return not ADMIN_IDS or user_id in ADMIN_IDS


async def send_card(bot, chat_id: int, acc: dict, photo_url: str | None = None):
    text     = format_account_card(acc)
    keyboard = account_keyboard(acc["id"], bool(acc.get("monitoring", True)))
    if photo_url:
        try:
            await bot.send_photo(
                chat_id=chat_id, photo=photo_url,
                caption=text, parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            return
        except Exception:
            pass
    await bot.send_message(
        chat_id=chat_id, text=text,
        parse_mode=ParseMode.HTML, reply_markup=keyboard
    )


async def do_check_and_notify(bot, acc: dict):
    """Check 1 account, gửi thông báo nếu thay đổi."""
    username = acc["username"]
    info = await checker.check(username)
    now  = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    old_status   = acc["status"]
    old_verified = bool(acc.get("verified", False))
    new_status   = info["status"]
    new_verified = bool(info.get("verified", False))

    # Cập nhật DB
    updates = {"last_check": now}
    if new_status != "unknown":
        updates["status"] = new_status
    if new_status == "live":
        updates["verified"]  = int(new_verified)
        updates["full_name"] = info.get("full_name") or acc.get("full_name", "")

    db.update_account(acc["id"], **updates)
    acc_updated = db.get_account_by_id(acc["id"])

    # Kiểm tra thay đổi
    status_changed   = new_status != "unknown" and new_status != old_status
    verified_changed = (new_status == "live" and old_status == "live"
                        and new_verified != old_verified)

    async def send_notify(text: str, pic: str | None):
        try:
            if pic:
                await bot.send_photo(
                    chat_id=acc["user_id"], photo=pic,
                    caption=text, parse_mode=ParseMode.HTML
                )
            else:
                await bot.send_message(
                    chat_id=acc["user_id"], text=text, parse_mode=ParseMode.HTML
                )
        except Exception as e:
            logger.error(f"Notify error @{username}: {e}")

    if status_changed:
        db.log_change(username, acc["user_id"], "status", old_status, new_status)
        old_e = status_emoji(old_status, old_verified)
        new_e = status_emoji(new_status, new_verified)
        old_l = "LIVE" if old_status == "live" else "DIE" if old_status == "die" else "?"
        new_l = "LIVE" if new_status == "live" else "DIE"
        text = (
            f"🔔 <b>Thay đổi trạng thái!</b>\n\n"
            f"📸 <a href=\"https://instagram.com/{username}\">@{username}</a>\n"
            f"👤 {info.get('full_name') or acc.get('full_name') or '—'}\n"
            f"📝 {acc.get('note') or '—'}\n\n"
            f"{old_e} <b>{old_l}</b> → {new_e} <b>{new_l}</b>\n\n"
            f"🕐 {now}"
        )
        await send_notify(text, info.get("profile_pic_url"))

    elif verified_changed:
        db.log_change(username, acc["user_id"], "verified",
                      str(old_verified), str(new_verified))
        if new_verified:
            v_text = "🔵 Vừa được <b>TÍCH XANH</b>! ✨"
        else:
            v_text = "⚪ Vừa <b>MẤT tích xanh</b>!"
        text = (
            f"🔔 <b>Thay đổi tích xanh!</b>\n\n"
            f"📸 <a href=\"https://instagram.com/{username}\">@{username}</a>\n"
            f"👤 {info.get('full_name') or acc.get('full_name') or '—'}\n"
            f"📝 {acc.get('note') or '—'}\n\n"
            f"{v_text}\n\n"
            f"🕐 {now}"
        )
        await send_notify(text, info.get("profile_pic_url"))

    return acc_updated, info


# ─── COMMANDS ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("❌ Không có quyền.")
        return
    context.user_data.clear()
    await update.message.reply_text(
        "📸 <b>Instagram Monitor Bot</b>\n\n"
        "Theo dõi tài khoản Instagram 24/7.\n"
        "🔔 Tự động thông báo khi:\n"
        "  • 🔴🟢 Tài khoản bị xóa / khôi phục\n"
        "  • 🔵⚪ Tích xanh xuất hiện / mất đi",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard()
    )


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    if context.args:
        await process_add(update, context, " ".join(context.args))
        return
    context.user_data[WAITING_ADD] = True
    await update.message.reply_text(
        "👤 <b>Thêm tài khoản Instagram</b>\n\n"
        "Nhập username hoặc URL:\n"
        "<code>@yunbray110</code>\n"
        "<code>yunbray110</code>\n"
        "<code>https://instagram.com/yunbray110</code>\n\n"
        "Thêm ghi chú:\n"
        "<code>yunbray110 | Ghi chú của bạn</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Hủy", callback_data="cancel_add")
        ]])
    )


async def process_add(update: Update, context: ContextTypes.DEFAULT_TYPE, raw: str):
    parts    = [p.strip() for p in raw.split("|")]
    username = checker.extract_username(parts[0])
    note     = parts[1] if len(parts) > 1 else ""

    if not username:
        await update.message.reply_text(
            "❌ Username không hợp lệ.\nVí dụ: <code>@yunbray110</code>",
            parse_mode=ParseMode.HTML
        )
        return

    user_id = update.effective_user.id
    msg = await update.message.reply_text(
        f"🔍 Đang kiểm tra <code>@{username}</code>...", parse_mode=ParseMode.HTML
    )

    info = await checker.check(username)

    added = db.add_account(
        username, user_id, note,
        info["status"],
        bool(info.get("verified")),
        info.get("full_name") or ""
    )

    if not added:
        await msg.edit_text(
            f"⚠️ <code>@{username}</code> đã có trong danh sách rồi.",
            parse_mode=ParseMode.HTML
        )
        return

    acc = db.get_account(username, user_id)
    await msg.delete()
    await send_card(context.bot, update.effective_chat.id, acc,
                    photo_url=info.get("profile_pic_url"))


# ─── MESSAGE HANDLER ──────────────────────────────────────────────────────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    if context.user_data.get(WAITING_ADD):
        context.user_data.pop(WAITING_ADD)
        await process_add(update, context, update.message.text.strip())
        return

    if context.user_data.get(WAITING_UPDATE):
        account_id = context.user_data.pop(WAITING_UPDATE)
        acc = db.get_account_by_id(account_id)
        if not acc:
            await update.message.reply_text("❌ Không tìm thấy.")
            return
        db.update_account(account_id, note=update.message.text.strip())
        acc = db.get_account_by_id(account_id)
        await update.message.reply_text("✅ Đã cập nhật ghi chú!")
        await send_card(context.bot, update.effective_chat.id, acc)


# ─── CALLBACK QUERIES ─────────────────────────────────────────────────────────

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    data    = query.data
    user_id = update.effective_user.id

    if data == "menu":
        context.user_data.clear()
        await query.message.reply_text(
            "📸 <b>Instagram Monitor Bot</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard()
        )

    elif data == "cancel_add":
        context.user_data.clear()
        try:
            await query.edit_message_text("❌ Đã hủy.", reply_markup=main_menu_keyboard())
        except Exception:
            await query.message.reply_text("❌ Đã hủy.", reply_markup=main_menu_keyboard())

    elif data == "list":
        accounts = db.get_accounts(user_id)
        if not accounts:
            await query.message.reply_text(
                "📭 Danh sách trống. Dùng /add để thêm.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Thêm username", callback_data="add_new")
                ]])
            )
            return
        await query.message.reply_text(
            f"📋 <b>Danh sách theo dõi</b> ({len(accounts)})",
            parse_mode=ParseMode.HTML,
            reply_markup=list_keyboard(accounts)
        )

    elif data == "add_new":
        context.user_data[WAITING_ADD] = True
        await query.message.reply_text(
            "👤 Nhập username Instagram:\n<code>@username</code> hoặc <code>username | Ghi chú</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Hủy", callback_data="cancel_add")
            ]])
        )

    elif data.startswith("view:"):
        account_id = int(data.split(":")[1])
        acc = db.get_account_by_id(account_id)
        if not acc or acc["user_id"] != user_id:
            return
        await send_card(context.bot, update.effective_chat.id, acc)

    elif data.startswith("check_now:"):
        account_id = int(data.split(":")[1])
        acc = db.get_account_by_id(account_id)
        if not acc or acc["user_id"] != user_id:
            return
        msg = await query.message.reply_text("🔍 Đang kiểm tra...")
        acc_updated, info = await do_check_and_notify(context.bot, acc)
        await msg.delete()
        await send_card(context.bot, update.effective_chat.id, acc_updated,
                        photo_url=info.get("profile_pic_url"))

    elif data.startswith("toggle_mon:"):
        account_id = int(data.split(":")[1])
        acc = db.get_account_by_id(account_id)
        if not acc or acc["user_id"] != user_id:
            return
        new_state = db.toggle_monitoring(account_id)
        acc = db.get_account_by_id(account_id)
        await query.answer("▶️ Đã BẬT theo dõi" if new_state else "⏸ Đã TẮT theo dõi", show_alert=True)
        try:
            await query.edit_message_caption(
                caption=format_account_card(acc), parse_mode=ParseMode.HTML,
                reply_markup=account_keyboard(acc["id"], bool(acc["monitoring"]))
            )
        except Exception:
            try:
                await query.edit_message_text(
                    text=format_account_card(acc), parse_mode=ParseMode.HTML,
                    reply_markup=account_keyboard(acc["id"], bool(acc["monitoring"]))
                )
            except Exception:
                pass

    elif data.startswith("update:"):
        account_id = int(data.split(":")[1])
        acc = db.get_account_by_id(account_id)
        if not acc or acc["user_id"] != user_id:
            return
        context.user_data[WAITING_UPDATE] = account_id
        await query.message.reply_text(
            f"✏️ Nhập ghi chú mới cho <code>@{acc['username']}</code>:\n"
            f"Hiện tại: <code>{acc.get('note') or '(trống)'}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Hủy", callback_data=f"view:{account_id}")
            ]])
        )

    elif data.startswith("remove:"):
        account_id = int(data.split(":")[1])
        acc = db.get_account_by_id(account_id)
        if not acc or acc["user_id"] != user_id:
            return
        await query.message.reply_text(
            f"⚠️ Xác nhận xóa <code>@{acc['username']}</code>?",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Xóa", callback_data=f"confirm_remove:{account_id}"),
                InlineKeyboardButton("❌ Hủy", callback_data=f"view:{account_id}"),
            ]])
        )

    elif data.startswith("confirm_remove:"):
        account_id = int(data.split(":")[1])
        acc = db.get_account_by_id(account_id)
        if not acc or acc["user_id"] != user_id:
            return
        db.remove_account(acc["username"], user_id)
        await query.message.reply_text(
            f"🗑 Đã xóa <code>@{acc['username']}</code>",
            parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard()
        )

    elif data == "stats":
        s = db.get_stats(user_id)
        await query.message.reply_text(
            f"📊 <b>Thống kê</b>\n\n"
            f"📋 Tổng theo dõi: <b>{s['total']}</b>\n"
            f"🟢 Live: <b>{s['live']}</b>\n"
            f"🔴 Die: <b>{s['die']}</b>\n"
            f"🔵 Có tích xanh: <b>{s['verified']}</b>\n"
            f"📡 Đang theo dõi: <b>{s['monitoring']}</b>\n\n"
            f"⏱ Check mỗi: <b>{CHECK_INTERVAL // 60} phút</b>",
            parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard()
        )

    elif data == "checkall":
        accounts = db.get_accounts(user_id)
        if not accounts:
            await query.message.reply_text("📭 Danh sách trống.")
            return
        msg = await query.message.reply_text(f"🔄 Đang check {len(accounts)} tài khoản...")
        lines = ["📊 <b>Kết quả:</b>\n"]
        for acc in accounts:
            acc_updated, info = await do_check_and_notify(context.bot, acc)
            s = status_emoji(acc_updated["status"], bool(acc_updated.get("verified")))
            v = " 🔵" if acc_updated.get("verified") and acc_updated.get("status") == "live" else ""
            lines.append(f"{s} <code>@{acc['username']}</code> {acc.get('note','')}{v}")
            await asyncio.sleep(1)
        lines.append(f"\n<i>{datetime.now().strftime('%H:%M %d/%m/%Y')}</i>")
        await msg.edit_text("\n".join(lines), parse_mode=ParseMode.HTML,
                            reply_markup=main_menu_keyboard())


# ─── MONITOR LOOP ─────────────────────────────────────────────────────────────

async def monitor_loop(app: Application):
    logger.info("Monitor loop started")
    await asyncio.sleep(15)
    while True:
        try:
            accounts = db.get_all_monitoring()
            logger.info(f"Checking {len(accounts)} accounts...")
            for acc in accounts:
                try:
                    await do_check_and_notify(app.bot, acc)
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"Error @{acc['username']}: {e}")
                    await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"Monitor loop error: {e}")
        await asyncio.sleep(CHECK_INTERVAL)


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    db.init()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu",  cmd_start))
    app.add_handler(CommandHandler("add",   cmd_add))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    async def post_init(application):
        asyncio.create_task(monitor_loop(application))

    app.post_init = post_init

    logger.info("🤖 Bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
