import os
import logging
import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# تنظیمات لاگ‌ها
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# چاپ متغیرهای محیطی برای دیباگ (توجه: این خط را در محیط تولید می‌توانید حذف کنید)
print("All ENV variables:", os.environ)

# دریافت توکن از متغیر محیطی
TOKEN = os.getenv("TOKEN")
print("TOKEN:", TOKEN)  # بررسی مقدار توکن

# بررسی مقدار TOKEN
if not TOKEN:
    raise ValueError("TOKEN is not set. Please set the TOKEN environment variable with your bot token.")

# اتصال به دیتابیس و ایجاد جدول
conn = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        chat_id INTEGER,
        message TEXT,
        date TEXT
    )
""")
conn.commit()

# ساخت ربات با استفاده از توکن دریافتی
bot = Application.builder().token(TOKEN).build()

async def start(update: Update, context: CallbackContext) -> None:
    """دستور /start برای خوش‌آمدگویی"""
    await update.message.reply_text("سلام! من یک ربات همه‌کاره هستم. چطور میتونم کمک کنم؟")

async def handle_message(update: Update, context: CallbackContext) -> None:
    """ذخیره پیام‌ها و ارسال پاسخ"""
    user = update.message.from_user
    chat_id = update.message.chat_id
    message = update.message.text
    date = update.message.date.strftime("%Y-%m-%d %H:%M:%S")

    # ذخیره پیام در دیتابیس
    cursor.execute("INSERT INTO messages (user_id, username, chat_id, message, date) VALUES (?, ?, ?, ?, ?)", 
                   (user.id, user.username, chat_id, message, date))
    conn.commit()

    await update.message.reply_text(f"پیام شما ذخیره شد: {message}")

# اضافه کردن هندلرها به ربات
bot.add_handler(CommandHandler("start", start))
bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# اجرای ربات
if __name__ == "__main__":
    print("ربات در حال اجراست...")
    bot.run_polling()
