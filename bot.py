import os
import logging
import sqlite3
from telegram import Update, ParseMode
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

# تعیین آی‌دی ادمین (تغییر به آی‌دی خودتان)
ADMIN_ID = 381200758

async def start(update: Update, context: CallbackContext) -> None:
    """دستور /start برای خوش‌آمدگویی"""
    await update.message.reply_text(
        "سلام! 🤖 من ربات جامع هستم.\n"
        "✅ تمامی پیام‌ها ثبت می‌شوند.\n"
        "برای دریافت داده‌ها، دستور /show_data را ارسال کنید.\n"
        "برای مشاهده راهنما، دستور /help را وارد کنید.\n\n"
        "همچنین برای فعال کردن حالت ریپلای در این چت:\n"
        "🔹 /reply : تنظیم متن ریپلای (تنها ادمین)\n"
        "🔹 /endreply : پایان حالت ریپلای"
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """نمایش راهنما و لیست دستورات ربات"""
    help_text = (
        "📚 <b>راهنمای ربات جامع</b>\n\n"
        "➖ <b>/start</b>: خوش‌آمدگویی و معرفی ربات.\n"
        "➖ <b>/help</b>: نمایش راهنما و لیست دستورات.\n"
        "➖ <b>/show_data</b>: نمایش تمامی پیام‌های ثبت‌شده (فقط برای ادمین).\n"
        "➖ <b>/reply</b>: فعال‌سازی حالت ریپلای (تنها ادمین)؛ پیام بعدی ادمین متن ریپلای خواهد شد.\n"
        "➖ <b>/endreply</b>: پایان حالت ریپلای (تنها ادمین).\n\n"
        "💡 در حالت ریپلای، هر پیام جدید در چت با متن ریپلای تنظیم شده پاسخ داده می‌شود."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def handle_message(update: Update, context: CallbackContext) -> None:
    """
    ذخیره پیام‌ها در دیتابیس و در صورت فعال بودن حالت ریپلای،
    ارسال ریپلای به پیام‌ها.
    اگر در حالت تنظیم ریپلای (awaiting_reply_text) هستیم و پیام از ادمین است،
    آن پیام به عنوان متن ریپلای ذخیره می‌شود.
    """
    # چک کردن حالت تنظیم ریپلای
    if context.chat_data.get("awaiting_reply_text") and update.message.from_user.id == ADMIN_ID:
        context.chat_data["reply_text"] = update.message.text
        context.chat_data.pop("awaiting_reply_text")
        await update.message.reply_text(f"✅ حالت ریپلای فعال شد.\nریپلای: {update.message.text}")
        return

    # ذخیره پیام در دیتابیس
    user = update.message.from_user
    chat_id = update.message.chat_id
    message = update.message.text
    date = update.message.date.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO messages (user_id, username, chat_id, message, date)
        VALUES (?, ?, ?, ?, ?)
    """, (user.id, user.username, chat_id, message, date))
    conn.commit()

    # در صورتی که حالت ریپلای فعال باشد، به پیام‌ها ریپلای ارسال می‌شود
    if "reply_text" in context.chat_data:
        await update.message.reply_text(context.chat_data["reply_text"])

async def show_data(update: Update, context: CallbackContext) -> None:
    """
    نمایش تمامی پیام‌های ثبت شده - فقط برای ادمین.
    اگر دستور از چت گروه یا کانال ارسال شود، خروجی به صورت خصوصی برای ADMIN_ID ارسال می‌شود.
    """
    user = update.message.from_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ شما اجازه دسترسی به این دستور را ندارید.")
        return

    cursor.execute("""
        SELECT user_id, username, chat_id, message, date 
        FROM messages
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()

    if not rows:
        response = "📭 هیچ پیامی ثبت نشده است."
    else:
        response = "📌 <b>تمامی پیام‌های ثبت‌شده:</b>\n\n"
        for row in rows:
            response += (
                f"👤 <b>UserID:</b> {row[0]}\n"
                f"🗣 <b>Username:</b> {row[1] if row[1] else 'نامشخص'}\n"
                f"💬 <b>Message:</b> {row[3]}\n"
                f"🕒 <b>Date:</b> {row[4]}\n"
                "-----------------------------------\n"
            )

    if update.message.chat.type != "private":
        await context.bot.send_message(chat_id=ADMIN_ID, text=response, parse_mode=ParseMode.HTML)
        await update.message.reply_text("✅ داده‌ها به پیام خصوصی ارسال شدند.")
    else:
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)

async def reply_command(update: Update, context: CallbackContext) -> None:
    """شروع تنظیم حالت ریپلای: فقط ادمین می‌تواند این دستور را اجرا کند"""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ شما اجازه ندارید.")
        return
    context.chat_data["awaiting_reply_text"] = True
    await update.message.reply_text("📝 لطفاً متن یا ایموجی ریپلای را ارسال کنید.")

async def endreply_command(update: Update, context: CallbackContext) -> None:
    """پایان حالت ریپلای: فقط ادمین می‌تواند این دستور را اجرا کند"""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ شما اجازه ندارید.")
        return
    if "reply_text" in context.chat_data:
        context.chat_data.pop("reply_text")
        await update.message.reply_text("✅ حالت ریپلای خاموش شد.")
    else:
        await update.message.reply_text("ℹ️ حالت ریپلای فعال نیست.")

# ثبت هندلرها
bot.add_handler(CommandHandler("start", start))
bot.add_handler(CommandHandler("help", help_command))
bot.add_handler(CommandHandler("show_data", show_data))
bot.add_handler(CommandHandler("reply", reply_command))
bot.add_handler(CommandHandler("endreply", endreply_command))
bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# اجرای ربات
if __name__ == "__main__":
    logging.info("ربات در حال اجراست...")
    bot.run_polling()
