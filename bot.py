import os
import logging
import sqlite3
import shutil
from datetime import datetime
from telegram import Update
from telegram.constants import ParseMode
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


DB_PATH = "bot_data.db"

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

# تعیین ادمین اصلی (که قابل حذف نیست) و لیست ادمین‌ها
MAIN_ADMIN_ID = 381200758
admins = {MAIN_ADMIN_ID}

async def start(update: Update, context: CallbackContext) -> None:
    """دستور /start برای خوش‌آمدگویی"""
    await update.message.reply_text(
        "سلام! 🤖 من ربات جامع هستم.\n"
        "✅ تمامی پیام‌ها ثبت می‌شوند.\n"
        "برای دریافت داده‌ها، دستور /show_data را ارسال کنید.\n"
        "برای مشاهده راهنما، دستور /help را وارد کنید.\n\n"
        "همچنین برای فعال کردن حالت ریپلای در این چت:\n"
        "🔹 /reply : تنظیم متن ریپلای (تنها ادمین)\n"
        "🔹 /endreply : پایان حالت ریپلای\n\n"
        "برای مدیریت ادمین‌ها:\n"
        "🔸 /add_admin [user_id یا @username]\n"
        "🔸 /remove_admin [user_id یا @username] (ادمین اصلی قابل حذف نیست)\n"
        "🔸 /list_admins : نمایش ادمین‌های فعلی"
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """نمایش راهنما و لیست دستورات ربات"""
    help_text = (
        "📚 <b>راهنمای ربات جامع</b>\n\n"
        "➖ <b>/start</b>: خوش‌آمدگویی و معرفی ربات.\n"
        "➖ <b>/help</b>: نمایش راهنمای کامل دستورات.\n"
        "➖ <b>/show_data</b>: نمایش تمامی پیام‌های ثبت‌شده (فقط برای ادمین).\n"
        "➖ <b>/reply</b>: فعال‌سازی حالت ریپلای (تنها ادمین)؛ پیام بعدی ادمین، متن ریپلای خواهد شد.\n"
        "➖ <b>/endreply</b>: پایان حالت ریپلای (تنها ادمین).\n"
        "➖ <b>/add_admin [user_id یا @username]</b>: اضافه کردن یک ادمین جدید (فقط توسط ادمین‌ها).\n"
        "➖ <b>/remove_admin [user_id یا @username]</b>: حذف یک ادمین (فقط توسط ادمین‌ها؛ ادمین اصلی قابل حذف نیست).\n"
        "➖ <b>/list_admins</b>: نمایش لیست ادمین‌های ثبت‌شده.\n\n"
        "🔧 <b>امکانات جدید:</b>\n"
        "➖ <b>/backup</b>: بکاپ‌گیری از دیتابیس؛ یک فایل بکاپ ایجاد شده و برای شما ارسال می‌شود.\n"
        "➖ <b>/restore</b>: ریستور دیتابیس؛ فایل بکاپ را به عنوان داکیومنت ارسال کنید. (داده‌های موجود حفظ شده و داده‌های جدید به آنها اضافه می‌شود.)\n"
        "➖ <b>/stats</b>: نمایش آمار کلی ربات شامل تعداد کل پیام‌ها، تعداد کاربران منحصربه‌فرد، ۵ کاربر برتر و زمان فعال بودن ربات.\n\n"
        "💡 <b>نکته:</b> دسترسی به دستورات مدیریت و امکانات جدید فقط برای ادمین‌ها می‌باشد."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def handle_message(update: Update, context: CallbackContext) -> None:
    """
    ذخیره پیام‌ها در دیتابیس و در صورت فعال بودن حالت ریپلای،
    ارسال ریپلای دقیق به پیام‌ها.
    اگر در حالت تنظیم ریپلای (awaiting_reply_text) هستیم و پیام از ادمین است،
    آن پیام به عنوان متن ریپلای ذخیره می‌شود.
    """
    # چک کردن حالت تنظیم ریپلای
    if context.chat_data.get("awaiting_reply_text") and update.message.from_user.id in admins:
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

    # در صورتی که حالت ریپلای فعال باشد، به پیام‌ها به صورت ریپلای دقیق پاسخ داده می‌شود
    if "reply_text" in context.chat_data:
        await update.message.reply_text(
            context.chat_data["reply_text"],
            reply_to_message_id=update.message.message_id
        )

async def show_data(update: Update, context: CallbackContext) -> None:
    """
    نمایش تمامی پیام‌های ثبت شده - فقط برای ادمین.
    اگر دستور از چت گروه یا کانال ارسال شود، خروجی به صورت خصوصی به ادمین ارسال می‌شود.
    """
    user = update.message.from_user
    if user.id not in admins:
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
                f"💡 <b>ChatID:</b> {row[2]}\n"
                f"🕒 <b>Date:</b> {row[4]}\n"
                "-----------------------------------\n"
            )

    if update.message.chat.type != "private":
        await context.bot.send_message(chat_id=user.id, text=response, parse_mode=ParseMode.HTML)
        await update.message.reply_text("✅ داده‌ها به پیام خصوصی ارسال شدند.")
    else:
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)

async def reply_command(update: Update, context: CallbackContext) -> None:
    """شروع تنظیم حالت ریپلای: فقط ادمین می‌تواند این دستور را اجرا کند"""
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ شما اجازه ندارید.")
        return
    context.chat_data["awaiting_reply_text"] = True
    await update.message.reply_text("📝 لطفاً متن یا ایموجی ریپلای را ارسال کنید.")

async def endreply_command(update: Update, context: CallbackContext) -> None:
    """پایان حالت ریپلای: فقط ادمین می‌تواند این دستور را اجرا کند"""
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ شما اجازه ندارید.")
        return
    if "reply_text" in context.chat_data:
        context.chat_data.pop("reply_text")
        await update.message.reply_text("✅ حالت ریپلای خاموش شد.")
    else:
        await update.message.reply_text("ℹ️ حالت ریپلای فعال نیست.")

async def add_admin(update: Update, context: CallbackContext) -> None:
    """اضافه کردن ادمین جدید (تنها توسط ادمین‌های فعلی مجاز)"""
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ شما اجازه ندارید.")
        return

    if not context.args:
        await update.message.reply_text("❌ لطفاً آی‌دی یا یوزرنیم کاربر را به عنوان آرگومان وارد کنید.")
        return

    admin_input = context.args[0].strip()
    
    # اگر ورودی با @ شروع شود، از get_chat برای دریافت آیدی عددی استفاده می‌کنیم
    if admin_input.startswith('@'):
        try:
            chat = await context.bot.get_chat(admin_input)
            new_admin = chat.id
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در دریافت آیدی کاربر: {e}")
            return
    else:
        try:
            new_admin = int(admin_input)
        except ValueError:
            await update.message.reply_text("❌ مقدار ورودی نامعتبر است.")
            return

    if new_admin == MAIN_ADMIN_ID:
        await update.message.reply_text("❌ ادمین اصلی نمی‌تواند تغییر کند.")
        return

    if new_admin in admins:
        await update.message.reply_text("ℹ️ این کاربر قبلاً به عنوان ادمین اضافه شده است.")
    else:
        admins.add(new_admin)
        await update.message.reply_text(f"✅ کاربر {new_admin} به عنوان ادمین اضافه شد.")


async def remove_admin(update: Update, context: CallbackContext) -> None:
    """حذف یک ادمین (تنها توسط ادمین‌های فعلی مجاز)"""
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ شما اجازه ندارید.")
        return

    if not context.args:
        await update.message.reply_text("❌ لطفاً آی‌دی یا یوزرنیم کاربر را به عنوان آرگومان وارد کنید.")
        return

    admin_input = context.args[0].strip()
    
    if admin_input.startswith('@'):
        try:
            chat = await context.bot.get_chat(admin_input)
            rem_admin = chat.id
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در دریافت آیدی کاربر: {e}")
            return
    else:
        try:
            rem_admin = int(admin_input)
        except ValueError:
            await update.message.reply_text("❌ مقدار ورودی نامعتبر است.")
            return

    if rem_admin == MAIN_ADMIN_ID:
        await update.message.reply_text("❌ ادمین اصلی قابل حذف نیست.")
        return

    if rem_admin in admins:
        admins.remove(rem_admin)
        await update.message.reply_text(f"✅ کاربر {rem_admin} از لیست ادمین‌ها حذف شد.")
    else:
        await update.message.reply_text("ℹ️ این کاربر در لیست ادمین‌ها موجود نیست.")


async def list_admins(update: Update, context: CallbackContext) -> None:
    if not admins:
        await update.message.reply_text("ℹ️ هیچ ادمینی ثبت نشده است.")
        return
    response = "👥 <b>لیست ادمین‌ها:</b>\n\n"
    for admin in admins:
        response += f"• {admin}\n"
    await update.message.reply_text(response, parse_mode=ParseMode.HTML)


async def backup_db(update: Update, context: CallbackContext) -> None:
    """ بکاپ‌گیری از دیتابیس """
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ شما اجازه این کار را ندارید.")
        return
    backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy(DB_PATH, backup_filename)
    await update.message.reply_document(document=open(backup_filename, "rb"))
    os.remove(backup_filename)

async def restore_db(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ شما اجازه این کار را ندارید.")
        return
    if not update.message.document:
        await update.message.reply_text("❌ لطفاً فایل بکاپ را به عنوان داکیومنت ارسال کنید.")
        return
    file = await context.bot.get_file(update.message.document.file_id)
    file_path = "restore_temp.db"
    await file.download_to_drive(file_path)
    # ادامه کد


    restore_conn = sqlite3.connect(file_path)
    restore_cursor = restore_conn.cursor()
    restore_cursor.execute("SELECT * FROM messages")
    rows = restore_cursor.fetchall()
    restore_conn.close()

    for row in rows:
        cursor.execute("""
            INSERT INTO messages (user_id, username, chat_id, message, date)
            VALUES (?, ?, ?, ?, ?)
        """, row[1:])
    conn.commit()
    os.remove(file_path)
    await update.message.reply_text("✅ داده‌ها با موفقیت بازیابی شدند.")

async def stats(update: Update, context: CallbackContext) -> None:
    """ نمایش آمار کلی ربات """
    cursor.execute("SELECT COUNT(*) FROM messages")
    total_messages = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM messages")
    unique_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT user_id, username, COUNT(*) as msg_count FROM messages GROUP BY user_id ORDER BY msg_count DESC LIMIT 5")
    top_users = cursor.fetchall()
    
    bot_start_time = os.path.getctime(DB_PATH)
    uptime = datetime.now() - datetime.fromtimestamp(bot_start_time)
    
    stats_text = (
        f"📊 <b>آمار کلی ربات</b>\n\n"
        f"📝 <b>تعداد کل پیام‌ها:</b> {total_messages}\n"
        f"👥 <b>تعداد کاربران منحصربه‌فرد:</b> {unique_users}\n"
        f"⏳ <b>مدت زمان فعال بودن ربات:</b> {uptime.days} روز، {uptime.seconds // 3600} ساعت"
    )
    if top_users:
        stats_text += "\n🏆 <b>۵ کاربر برتر:</b>\n"
        for user in top_users:
            stats_text += f"{user[1] if user[1] else user[0]} - {user[2]} پیام\n"
    
    await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)
    
    response = "👥 <b>لیست ادمین‌ها:</b>\n\n"
    for admin in admins:
        response += f"• {admin}\n"
    await update.message.reply_text(response, parse_mode=ParseMode.HTML)

# ثبت هندلرها
bot.add_handler(CommandHandler("start", start))
bot.add_handler(CommandHandler("help", help_command))
bot.add_handler(CommandHandler("show_data", show_data))
bot.add_handler(CommandHandler("reply", reply_command))
bot.add_handler(CommandHandler("endreply", endreply_command))
bot.add_handler(CommandHandler("add_admin", add_admin))
bot.add_handler(CommandHandler("remove_admin", remove_admin))
bot.add_handler(CommandHandler("list_admins", list_admins))
bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
bot.add_handler(CommandHandler("backup", backup_db))
bot.add_handler(CommandHandler("restore", restore_db))
bot.add_handler(CommandHandler("stats", stats))

# اجرای ربات
if __name__ == "__main__":
    logging.info("ربات در حال اجراست...")
    bot.run_polling()
