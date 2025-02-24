import os
import logging
import sqlite3
import gzip
from datetime import datetime
from telegram import Update, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackContext
)

# تنظیمات لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# دریافت توکن از متغیر محیطی
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN is not set. Please set the TOKEN environment variable with your bot token.")

# اتصال به دیتابیس SQLite و ایجاد جدول‌ها در صورت عدم وجود
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

cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS errors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        error TEXT,
        date TEXT
    )
""")
conn.commit()

# مقداردهی اولیه ادمین اصلی
MAIN_ADMIN_ID = 381200758
cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (MAIN_ADMIN_ID,))
conn.commit()

# دریافت لیست ادمین‌ها از دیتابیس
def get_admins():
    cursor.execute("SELECT user_id FROM admins")
    return {row[0] for row in cursor.fetchall()}

admins = get_admins()

# ساخت ربات
bot = Application.builder().token(TOKEN).build()

# دستورات ربات
async def backup_db(update: Update, context: CallbackContext) -> None:
    """ایجاد بکاپ از دیتابیس و ارسال آن به ادمین"""
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ شما اجازه ندارید.")
        return
    
    backup_file = "bot_data.db.gz"
    with open("bot_data.db", "rb") as db_file, gzip.open(backup_file, "wb") as compressed_file:
        compressed_file.writelines(db_file)
    
    await update.message.reply_document(document=InputFile(backup_file), caption="📂 بکاپ دیتابیس آماده شد.")

async def restore_db(update: Update, context: CallbackContext) -> None:
    """بازگردانی دیتابیس از بکاپ ارسال‌شده"""
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ شما اجازه ندارید.")
        return
    
    if not update.message.document:
        await update.message.reply_text("❌ لطفاً فایل بکاپ را ارسال کنید.")
        return
    
    file = await context.bot.get_file(update.message.document.file_id)
    await file.download_to_drive("bot_data_restored.db.gz")
    
    with gzip.open("bot_data_restored.db.gz", "rb") as restored_file, open("bot_data.db", "wb") as db_file:
        db_file.writelines(restored_file)
    
    await update.message.reply_text("✅ دیتابیس با موفقیت بازگردانی شد.")

async def stats(update: Update, context: CallbackContext) -> None:
    """نمایش آمار کاربران و پیام‌ها"""
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ شما اجازه ندارید.")
        return
    
    cursor.execute("SELECT COUNT(*) FROM messages")
    total_messages = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM messages")
    total_users = cursor.fetchone()[0]
    
    await update.message.reply_text(f"📊 آمار ربات:\n👥 کاربران: {total_users}\n💬 پیام‌ها: {total_messages}")

async def report_error(update: Update, context: CallbackContext) -> None:
    """گزارش خطاها"""
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ شما اجازه ندارید.")
        return
    
    cursor.execute("SELECT error, date FROM errors ORDER BY id DESC LIMIT 5")
    errors = cursor.fetchall()
    
    if not errors:
        await update.message.reply_text("✅ هیچ خطایی ثبت نشده است.")
        return
    
    error_report = "\n".join([f"📅 {row[1]}\n❌ {row[0]}" for row in errors])
    await update.message.reply_text(f"🚨 آخرین خطاهای ثبت‌شده:\n{error_report}")

async def log_message(update: Update, context: CallbackContext) -> None:
    """ثبت پیام‌های دریافتی"""
    user = update.message.from_user
    cursor.execute(
        "INSERT INTO messages (user_id, username, chat_id, message, date) VALUES (?, ?, ?, ?, ?)",
        (user.id, user.username, update.message.chat_id, update.message.text, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()

# ثبت دستورات در ربات
bot.add_handler(CommandHandler("backup", backup_db))
bot.add_handler(CommandHandler("stats", stats))
bot.add_handler(CommandHandler("report", report_error))
bot.add_handler(MessageHandler(filters.Document.ALL, restore_db))
bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, log_message))

# اجرای ربات
bot.run_polling()
