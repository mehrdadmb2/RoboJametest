import os
import logging
import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# تنظیمات لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# دریافت توکن از متغیر محیطی
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN is not set. Please set the TOKEN environment variable with your bot token.")

# اتصال به دیتابیس SQLite و ایجاد جدول در صورت عدم وجود
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

# ساخت ربات
bot = Application.builder().token(TOKEN).build()

# یک آی‌دی برای ادمین (برای مثال: آی‌دی خودتان)
ADMIN_ID = 381200756  # مقدار این متغیر را به آی‌دی تلگرام خود تغییر دهید

async def start(update: Update, context: CallbackContext) -> None:
    """دستور /start برای خوش‌آمدگویی"""
    await update.message.reply_text("سلام! من ربات جامع هستم. پیام‌ها ثبت می‌شوند.\nبرای دیدن آخرین 10 پیام دستور /show_data را وارد کنید.")

async def handle_message(update: Update, context: CallbackContext) -> None:
    """ذخیره پیام‌ها در دیتابیس و پاسخ به کاربر"""
    user = update.message.from_user
    chat_id = update.message.chat_id
    message = update.message.text
    date = update.message.date.strftime("%Y-%m-%d %H:%M:%S")

    # ذخیره اطلاعات پیام در دیتابیس
    cursor.execute("""
        INSERT INTO messages (user_id, username, chat_id, message, date)
        VALUES (?, ?, ?, ?, ?)
    """, (user.id, user.username, chat_id, message, date))
    conn.commit()

    # پاسخ ساده به کاربر
    await update.message.reply_text("پیام شما ثبت شد.")

async def show_data(update: Update, context: CallbackContext) -> None:
    """نمایش آخرین 10 پیام ثبت شده - فقط برای ادمین"""
    user = update.message.from_user
    # بررسی ادمین بودن (اینجا فقط یک آی‌دی بررسی می‌شود، در صورت نیاز می‌توانید لیست ادمین‌ها داشته باشید)
    if user.id != ADMIN_ID:
        await update.message.reply_text("شما اجازه دسترسی به این دستور را ندارید.")
        return

    cursor.execute("""
        SELECT user_id, username, chat_id, message, date 
        FROM messages
        ORDER BY id DESC LIMIT 10
    """)
    rows = cursor.fetchall()
    if not rows:
        await update.message.reply_text("هیچ پیامی ثبت نشده است.")
        return

    text = "آخرین 10 پیام ثبت‌شده:\n\n"
    for row in rows:
        text += f"UserID: {row[0]}, Username: {row[1]}, ChatID: {row[2]}\nMessage: {row[3]}\nDate: {row[4]}\n\n"
    await update.message.reply_text(text)

# ثبت هندلرها
bot.add_handler(CommandHandler("start", start))
bot.add_handler(CommandHandler("show_data", show_data))
bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# اجرای ربات
if __name__ == "__main__":
    logging.info("ربات در حال اجراست...")
    bot.run_polling()
