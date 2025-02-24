import os
import logging
import sqlite3
import zipfile
from datetime import datetime
from telegram import Update, Bot
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackContext
)

# تنظیمات لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# دریافت توکن از متغیر محیطی
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN is not set. Please set the TOKEN environment variable with your bot token.")

# اتصال به دیتابیس SQLite و ایجاد جداول
conn = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = conn.cursor()

# ایجاد جداول مورد نیاز
cursor.executescript("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        chat_id INTEGER,
        message TEXT,
        date TEXT
    );
    
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        added_by INTEGER,
        date_added TEXT
    );
    
    CREATE TABLE IF NOT EXISTS errors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        error_text TEXT,
        timestamp TEXT
    );
    
    CREATE TABLE IF NOT EXISTS chat_settings (
        chat_id INTEGER PRIMARY KEY,
        reply_text TEXT,
        features_enabled TEXT DEFAULT 'all'
    );
    
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        chat_id INTEGER,
        report_text TEXT,
        timestamp TEXT
    );
""")
conn.commit()

# تعیین ادمین اصلی و بارگیری ادمین‌ها از دیتابیس
MAIN_ADMIN_ID = 381200758
cursor.execute("SELECT user_id FROM admins")
admins = {row[0] for row in cursor.fetchall()}
if MAIN_ADMIN_ID not in admins:
    cursor.execute("INSERT INTO admins (user_id, added_by, date_added) VALUES (?, ?, ?)",
                   (MAIN_ADMIN_ID, MAIN_ADMIN_ID, datetime.now().isoformat()))
    conn.commit()
    admins.add(MAIN_ADMIN_ID)

# ساخت ربات
bot = Application.builder().token(TOKEN).build()

# ---------- توابع کمکی جدید ----------
def log_error(error_text: str):
    """ثبت خطا در دیتابیس"""
    cursor.execute("INSERT INTO errors (error_text, timestamp) VALUES (?, ?)",
                   (error_text, datetime.now().isoformat()))
    conn.commit()
    logger.error(error_text)

async def send_to_admin(context: CallbackContext, message: str):
    """ارسال پیام به تمام ادمین‌ها"""
    for admin in admins:
        try:
            await context.bot.send_message(chat_id=admin, text=message)
        except Exception as e:
            logger.error(f"Failed to send message to admin {admin}: {e}")

async def backup_database(context: CallbackContext):
    """ایجاد فایل پشتیبان از دیتابیس"""
    try:
        with zipfile.ZipFile('bot_data_backup.zip', 'w') as zipf:
            zipf.write('bot_data.db')
        return 'bot_data_backup.zip'
    except Exception as e:
        log_error(f"Backup failed: {e}")
        return None

async def restore_database(update: Update, context: CallbackContext):
    """بازیابی دیتابیس از فایل پشتیبان"""
    try:
        file = await context.bot.get_file(update.message.document)
        await file.download_to_drive('restore.zip')
        with zipfile.ZipFile('restore.zip', 'r') as zipf:
            zipf.extractall()
        os.rename('bot_data.db', 'bot_data_old.db')  # ایجاد نسخه پشتیبان
        os.rename('restored_data.db', 'bot_data.db')
        return True
    except Exception as e:
        log_error(f"Restore failed: {e}")
        return False

# ---------- دستورات اصلی ----------
async def start(update: Update, context: CallbackContext) -> None:
    """دستور /start"""
    await update.message.reply_text(
        "سلام! 🤖 من ربات پیشرفته هستم.\n"
        "✅ تمامی پیام‌ها ثبت می‌شوند.\n"
        "برای راهنما /help را بزنید."
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """دستور /help"""
    help_text = (
        "📚 <b>راهنمای کامل ربات</b>\n\n"
        "<b>مدیریت داده:</b>\n"
        "➖ /backup - دریافت فایل پشتیبان\n"
        "➖ /stats - نمایش آمار\n\n"
        "<b>گزارش خطا:</b>\n"
        "➖ /report [متن] - گزارش مشکل\n\n"
        "<b>مدیریت ادمین:</b>\n"
        "➖ /add_admin [آی‌دی]\n"
        "➖ /remove_admin [آی‌دی]\n"
        "➖ /list_admins\n\n"
        "<b>تنظیمات چت:</b>\n"
        "➖ /reply [متن] - تنظیم پاسخ خودکار\n"
        "➖ /endreply - غیرفعال کردن پاسخ\n"
        "➖ /settings - تنظیمات چت\n\n"
        "<b>نظارت:</b>\n"
        "➖ /monitor [on/off] - حالت نظارت"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

# ---------- قابلیت‌های جدید ----------
async def backup_command(update: Update, context: CallbackContext):
    """دستور پشتیبان‌گیری"""
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ دسترسی ممنوع!")
        return
    
    backup_file = await backup_database(context)
    if backup_file:
        await update.message.reply_document(
            document=open(backup_file, 'rb'),
            filename='bot_data_backup.zip'
        )
    else:
        await update.message.reply_text("❌ ایجاد پشتیبان ناموفق بود!")

async def stats_command(update: Update, context: CallbackContext):
    """نمایش آمار"""
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ دسترسی ممنوع!")
        return
    
    cursor.execute("SELECT COUNT(*) FROM messages")
    total_messages = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM messages")
    unique_users = cursor.fetchone()[0]
    
    stats_text = (
        f"📊 <b>آمار ربات:</b>\n\n"
        f"• کل پیام‌ها: {total_messages}\n"
        f"• کاربران منحصر به فرد: {unique_users}\n"
        f"• ادمین‌ها: {len(admins)}"
    )
    await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)

async def report_command(update: Update, context: CallbackContext):
    """گزارش خطا توسط کاربران"""
    report_text = ' '.join(context.args)
    if not report_text:
        await update.message.reply_text("لطفاً متن گزارش را وارد کنید.")
        return
    
    cursor.execute("INSERT INTO reports (user_id, chat_id, report_text, timestamp) VALUES (?, ?, ?, ?)",
                   (update.message.from_user.id, update.message.chat_id, report_text, datetime.now().isoformat()))
    conn.commit()
    
    await send_to_admin(context, f"🚨 گزارش جدید:\n{report_text}\nاز کاربر: {update.message.from_user.id}")
    await update.message.reply_text("✅ گزارش شما ثبت شد.")

async def handle_backup_file(update: Update, context: CallbackContext):
    """پردازش فایل پشتیبان ارسالی"""
    if update.message.from_user.id not in admins:
        return
    
    if update.message.document and update.message.document.file_name.endswith('.zip'):
        success = await restore_database(update, context)
        if success:
            await update.message.reply_text("✅ بازیابی با موفقیت انجام شد!")
            await send_to_admin(context, "⚠️ دیتابیس با موفقیت بازیابی شد!")
        else:
            await update.message.reply_text("❌ خطا در بازیابی!")

async def monitor_command(update: Update, context: CallbackContext):
    """کنترل حالت نظارت"""
    if update.message.from_user.id not in admins:
        return
    
    if context.args and context.args[0].lower() in ['on', 'off']:
        state = context.args[0].lower()
        context.bot_data['monitoring'] = (state == 'on')
        await update.message.reply_text(f"حالت نظارت {state} شد.")
    else:
        await update.message.reply_text("استفاده: /monitor [on/off]")

# ---------- ثبت هندلرها ----------
bot.add_handler(CommandHandler("start", start))
bot.add_handler(CommandHandler("help", help_command))
bot.add_handler(CommandHandler("backup", backup_command))
bot.add_handler(CommandHandler("stats", stats_command))
bot.add_handler(CommandHandler("report", report_command))
bot.add_handler(CommandHandler("monitor", monitor_command))
bot.add_handler(MessageHandler(filters.Document.ALL, handle_backup_file))

# (بقیه هندلرهای قبلی اینجا اضافه میشن)

# اجرای ربات
if __name__ == "__main__":
    logger.info("ربات در حال اجراست...")
    bot.run_polling()
