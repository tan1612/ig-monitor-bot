# 📸 Instagram Monitor Bot

Bot Telegram theo dõi tài khoản Instagram 24/7.
Tự động thông báo khi:
- ✅ Tài khoản bị xóa hoặc khôi phục (Live/Die)
- 🔵 Tích xanh xuất hiện hoặc mất đi

---

## 🚀 Cài đặt trên Windows

### Bước 1 — Cài Python
Tải tại: https://www.python.org/downloads/
> ✅ Tick vào "Add Python to PATH" khi cài

### Bước 2 — Lấy Bot Token
1. Mở Telegram → tìm @BotFather
2. Gõ /newbot → đặt tên → lấy token

### Bước 3 — Điền token
Mở file `config.py`, sửa dòng:
```python
BOT_TOKEN = "token_cua_ban_o_day"
```

### Bước 4 — Chạy bot
Double-click file `run.bat`

Hoặc mở CMD:
```
cd đường_dẫn_đến_thư_mục
pip install -r requirements.txt
python bot.py
```

---

## 📖 Sử dụng

| Lệnh | Mô tả |
|------|-------|
| `/start` | Menu chính |
| `/add @username` | Thêm tài khoản theo dõi |
| `/add username \| Ghi chú` | Thêm kèm ghi chú |

### Nút bấm inline:
- **🔍 Check ngay** — Kiểm tra ngay lập tức
- **▶️/⏸ Theo dõi** — Bật/tắt tự động check
- **✏️ Cập nhật** — Sửa ghi chú
- **❌ Xóa** — Xóa khỏi danh sách
- **📋 Danh sách** — Xem tất cả
- **📊 Thống kê** — Tổng quan

---

## ⚙️ Cấu hình (config.py)

```python
BOT_TOKEN = "YOUR_TOKEN"      # Token từ @BotFather
ADMIN_IDS = [123456789]       # Giới hạn user dùng bot (bỏ trống = ai cũng dùng)
CHECK_INTERVAL = 60           # Giây giữa mỗi lần check (60 = 1 phút)
```

---

## 💡 Lưu ý
- Bot chạy trên máy tính của bạn — cần để máy bật
- Instagram đôi khi yêu cầu đăng nhập → bot trả về "unknown", không báo sai
- Nên check interval tối thiểu 60 giây để tránh bị rate limit
