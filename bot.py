import os
import logging
import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# تنظیمات لاگ‌ها
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

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

# دریافت توکن از متغیر محیطی
TOKEN = os.getenv("TOKEN")
print("TOKEN:", TOKEN)  # برای دیباگ، حذفش کن بعداً

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

# اضافه کردن هندلرها به بات
bot.add_handler(CommandHandler("start", start))
bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# اجرای بات
if __name__ == "__main__":
    print("ربات در حال اجراست...")
    bot.run_polling()
