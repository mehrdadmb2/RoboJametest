import os
import logging
import sqlite3
import shutil
import re
from datetime import datetime
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackContext
)

# ---------------- Logging Configuration ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)

# ---------------- Retrieve Bot Token ----------------
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN is not set. Please set the TOKEN environment variable with your bot token.")

DB_PATH = "bot_data.db"

# ---------------- Initialize Database ----------------
def init_db(db_path: str) -> sqlite3.Connection:
    """
    Connect to the SQLite database and create the messages table if it does not exist.
    """
    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
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
        logging.info("Database initialized successfully.")
        return conn
    except Exception as e:
        logging.error(f"Error initializing database: {e}")
        raise

conn = init_db(DB_PATH)
cursor = conn.cursor()

# ---------------- Create Bot Application ----------------
bot = Application.builder().token(TOKEN).build()

# ---------------- Admin Settings ----------------
MAIN_ADMIN_ID = 381200758
admins = {MAIN_ADMIN_ID, 1156819072}  # Add additional admin IDs here

# ---------------- Helper Functions for File Management ----------------
def is_allowed_file(filename: str) -> bool:
    """
    Returns True if the file is allowed to be sent via Telegram.
    Allowed files: 
      - Exactly "bot_data.db", "esp32_data_logger.log", "chart.png"
      - Files starting with "backup_" and ending with ".db"
      - Files starting with "data_log_" and ending with ".xlsx"
    """
    allowed_exact = {"bot_data.db", "esp32_data_logger.log", "chart.png"}
    if filename in allowed_exact:
        return True
    if filename.startswith("backup_") and filename.endswith(".db"):
        return True
    if filename.startswith("data_log_") and filename.endswith(".xlsx"):
        return True
    return False

def list_allowed_files() -> list:
    """
    Lists all allowed files in the current directory.
    """
    files = os.listdir(".")
    return [f for f in files if os.path.isfile(f) and is_allowed_file(f)]

# ---------------- Command Handlers ----------------
async def start(update: Update, context: CallbackContext) -> None:
    """
    Handles the /start command: sends a welcome message with an overview of the bot features.
    """
    if not update.message:
        return
    try:
        await update.message.reply_text(
            "سلام! 🤖 من ربات جامع هستم.\n"
            "✅ تمامی پیام‌ها ثبت می‌شوند.\n\n"
            "برای دریافت داده‌ها:\n"
            "➖ /show_data - نمایش پیام‌های ثبت‌شده (فقط برای ادمین، 50 پیام اخیر).\n"
            "➖ /stats - نمایش آمار کلی ربات.\n\n"
            "برای مدیریت ریپلای در این چت:\n"
            "➖ /reply - فعال کردن حالت ریپلای (تنها ادمین).\n"
            "➖ /endreply - پایان حالت ریپلای.\n\n"
            "برای مدیریت ادمین‌ها:\n"
            "➖ /add_admin [user_id یا @username]\n"
            "➖ /remove_admin [user_id یا @username] (ادمین اصلی قابل حذف نیست).\n"
            "➖ /list_admins - نمایش لیست ادمین‌های ثبت‌شده.\n\n"
            "🔧 امکانات جدید:\n"
            "➖ /backup - بکاپ‌گیری از دیتابیس و ارسال آن به تلگرام.\n"
            "➖ /restore - ریستور دیتابیس از فایل بکاپ ارسال‌شده.\n"
            "➖ /list_files - نمایش فایل‌های ذخیره‌شده مجاز.\n"
            "➖ /get_file <filename> - ارسال فایل مورد نظر به عنوان داکیومنت.\n"
            "➖ /get_info <username یا شماره تلفن> - دریافت اطلاعات عمومی کاربر.\n\n"
            "برای مشاهده راهنمای کامل دستورات، از /help استفاده کنید."
        )
    except Exception as e:
        logging.error(f"Error in start command: {e}")

async def help_command(update: Update, context: CallbackContext) -> None:
    """
    Sends a detailed help message with a list of all available commands.
    """
    if not update.message:
        return
    help_text = (
        "📚 <b>راهنمای کامل ربات جامع</b>\n\n"
        "1. <b>/start</b>: معرفی ربات و نمایش ویژگی‌ها.\n"
        "2. <b>/help</b>: نمایش راهنمای کامل دستورات.\n"
        "3. <b>/show_data</b>: نمایش 50 پیام ثبت‌شده (فقط برای ادمین).\n"
        "4. <b>/stats</b>: نمایش آمار کلی ربات شامل تعداد پیام‌ها، کاربران منحصربه‌فرد، 5 کاربر برتر و زمان فعال بودن.\n"
        "5. <b>/reply</b>: فعال کردن حالت ریپلای (تنها ادمین). پیام بعدی به عنوان ریپلای ارسال می‌شود.\n"
        "6. <b>/endreply</b>: پایان حالت ریپلای.\n"
        "7. <b>/add_admin [user_id یا @username]</b>: اضافه کردن ادمین جدید (فقط توسط ادمین‌ها).\n"
        "8. <b>/remove_admin [user_id یا @username]</b>: حذف یک ادمین (ادمین اصلی قابل حذف نیست).\n"
        "9. <b>/list_admins</b>: نمایش لیست ادمین‌های ثبت‌شده.\n"
        "10. <b>/backup</b>: بکاپ‌گیری از دیتابیس و ارسال فایل بکاپ.\n"
        "11. <b>/restore</b>: ریستور دیتابیس از فایل بکاپ ارسال‌شده.\n"
        "12. <b>/list_files</b>: نمایش لیست فایل‌های ذخیره‌شده مجاز (مثلاً بکاپ‌ها، اکسل، نمودار).\n"
        "13. <b>/get_file &lt;filename&gt;</b>: دریافت فایل مورد نظر (در صورت موجود بودن و مجاز بودن).\n"
        "14. <b>/get_info &lt;username یا شماره تلفن&gt;</b>: دریافت اطلاعات عمومی کاربر (فقط اطلاعات عمومی مانند نام، نام خانوادگی، یوزرنیم و شناسه).\n\n"
        "💡 توجه: دسترسی به برخی دستورات فقط برای ادمین‌ها مجاز است."
    )
    try:
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"Error in help command: {e}")

async def handle_message(update: Update, context: CallbackContext) -> None:
    """
    Save incoming messages to the database and send a reply if reply mode is active.
    """
    if not update.message:
        return
    try:
        # Check if reply mode is active (only for admins)
        if context.chat_data.get("awaiting_reply_text") and update.message.from_user.id in admins:
            context.chat_data["reply_text"] = update.message.text
            context.chat_data.pop("awaiting_reply_text")
            await update.message.reply_text(f"✅ Reply mode activated.\nReply: {update.message.text}")
            return

        # Save message to database
        user = update.message.from_user
        chat_id = update.message.chat_id
        message_text = update.message.text
        date_str = update.message.date.strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor.execute("""
                INSERT INTO messages (user_id, username, chat_id, message, date)
                VALUES (?, ?, ?, ?, ?)
            """, (user.id, user.username, chat_id, message_text, date_str))
            conn.commit()
        except Exception as db_error:
            logging.error(f"Database error while inserting message: {db_error}")

        # Send reply if reply mode is active
        if "reply_text" in context.chat_data:
            try:
                await update.message.reply_text(
                    context.chat_data["reply_text"],
                    reply_to_message_id=update.message.message_id
                )
            except Exception as e:
                logging.error(f"Error sending reply: {e}")
    except Exception as e:
        logging.error(f"Error in handle_message: {e}")

async def show_data(update: Update, context: CallbackContext) -> None:
    """
    Show the last 50 recorded messages from the database (admin only).
    """
    if not update.message:
        return
    user_id = update.message.from_user.id
    if user_id not in admins:
        await update.message.reply_text("❌ You do not have permission to access this command.")
        return

    try:
        cursor.execute("""
            SELECT user_id, username, chat_id, message, date 
            FROM messages
            ORDER BY id DESC
            LIMIT 50
        """)
        rows = cursor.fetchall()
    except Exception as e:
        logging.error(f"Database error in show_data: {e}")
        await update.message.reply_text("❌ Error retrieving data.")
        return

    if not rows:
        response = "📭 No messages have been recorded."
    else:
        response = "📌 <b>Last 50 Recorded Messages:</b>\n\n"
        for row in rows:
            response += (
                f"👤 <b>UserID:</b> {row[0]}\n"
                f"🗣 <b>Username:</b> {row[1] if row[1] else 'Unknown'}\n"
                f"💬 <b>Message:</b> {row[3]}\n"
                f"💡 <b>ChatID:</b> {row[2]}\n"
                f"🕒 <b>Date:</b> {row[4]}\n"
                "-----------------------------------\n"
            )

    try:
        if update.message.chat.type != "private":
            await context.bot.send_message(chat_id=user_id, text=response, parse_mode=ParseMode.HTML)
            await update.message.reply_text("✅ Data has been sent to your private messages.")
        else:
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"Error sending data message: {e}")

async def reply_command(update: Update, context: CallbackContext) -> None:
    """
    Activate reply mode for admins; the next message will be used as the reply text.
    """
    if not update.message:
        return
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ You do not have permission.")
        return
    context.chat_data["awaiting_reply_text"] = True
    await update.message.reply_text("📝 Please send the reply text or emoji.")

async def endreply_command(update: Update, context: CallbackContext) -> None:
    """
    Deactivate reply mode for admins.
    """
    if not update.message:
        return
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ You do not have permission.")
        return
    if "reply_text" in context.chat_data:
        context.chat_data.pop("reply_text")
        await update.message.reply_text("✅ Reply mode deactivated.")
    else:
        await update.message.reply_text("ℹ️ Reply mode is not active.")

async def add_admin(update: Update, context: CallbackContext) -> None:
    """
    Add a new admin. Only current admins can add a new admin.
    Note: If the user has not interacted with the bot, retrieving their info via /get_chat may fail.
          In such cases, please provide the numeric ID manually.
    """
    if not update.message:
        return
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ You do not have permission.")
        return

    if not context.args:
        await update.message.reply_text("❌ Please provide a user ID or @username as an argument.")
        return

    admin_input = context.args[0].strip()
    new_admin = None

    if admin_input.startswith('@'):
        try:
            chat = await context.bot.get_chat(admin_input)
            new_admin = chat.id
        except BadRequest as e:
            error_msg = str(e).lower()
            if "chat not found" in error_msg:
                await update.message.reply_text("❌ Chat not found. The user may not have started a conversation with the bot. Please provide the numeric ID instead.")
                return
            else:
                await update.message.reply_text(f"❌ Error retrieving user ID: {e}")
                return
        except Exception as e:
            await update.message.reply_text(f"❌ Error retrieving user ID: {e}")
            return
    else:
        try:
            new_admin = int(admin_input)
        except ValueError:
            await update.message.reply_text("❌ Invalid input provided. Please provide a numeric user ID or a username starting with '@'.")
            return

    if new_admin == MAIN_ADMIN_ID:
        await update.message.reply_text("❌ The main admin cannot be changed.")
        return

    if new_admin in admins:
        await update.message.reply_text("ℹ️ This user is already an admin.")
    else:
        admins.add(new_admin)
        await update.message.reply_text(f"✅ User {new_admin} has been added as an admin.")

async def remove_admin(update: Update, context: CallbackContext) -> None:
    """
    Remove an admin from the list. Only current admins can remove an admin.
    """
    if not update.message:
        return
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ You do not have permission.")
        return

    if not context.args:
        await update.message.reply_text("❌ Please provide a user ID or @username as an argument.")
        return

    admin_input = context.args[0].strip()
    rem_admin = None

    if admin_input.startswith('@'):
        try:
            chat = await context.bot.get_chat(admin_input)
            rem_admin = chat.id
        except Exception as e:
            await update.message.reply_text(f"❌ Error retrieving user ID: {e}")
            return
    else:
        try:
            rem_admin = int(admin_input)
        except ValueError:
            await update.message.reply_text("❌ Invalid input provided.")
            return

    if rem_admin == MAIN_ADMIN_ID:
        await update.message.reply_text("❌ The main admin cannot be removed.")
        return

    if rem_admin in admins:
        admins.remove(rem_admin)
        await update.message.reply_text(f"✅ User {rem_admin} has been removed from the admin list.")
    else:
        await update.message.reply_text("ℹ️ This user is not in the admin list.")

async def list_admins(update: Update, context: CallbackContext) -> None:
    """
    Show the list of registered admins.
    """
    if not update.message:
        return
    if not admins:
        await update.message.reply_text("ℹ️ No admins are registered.")
        return
    response = "👥 <b>Admin List:</b>\n\n" + "\n".join(f"• {admin}" for admin in admins)
    try:
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"Error in list_admins: {e}")

async def backup_db(update: Update, context: CallbackContext) -> None:
    """
    Create a backup of the database and send the backup file to the admin.
    """
    if not update.message:
        return
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ You do not have permission to perform this action.")
        return
    try:
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy(DB_PATH, backup_filename)
        with open(backup_filename, "rb") as backup_file:
            await update.message.reply_document(document=backup_file)
        os.remove(backup_filename)
        logging.info("Database backup completed successfully.")
    except Exception as e:
        logging.error(f"Error during database backup: {e}")
        await update.message.reply_text("❌ Error creating database backup.")

async def restore_db(update: Update, context: CallbackContext) -> None:
    """
    Restore the database from a backup file sent as a document.
    The backup file's data will be merged with the current data.
    """
    if not update.message:
        return
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ You do not have permission to perform this action.")
        return
    if not update.message.document:
        await update.message.reply_text("❌ Please send the backup file as a document.")
        return
    try:
        file = await context.bot.get_file(update.message.document.file_id)
        restore_file = "restore_temp.db"
        await file.download_to_drive(custom_path=restore_file)
    except Exception as e:
        logging.error(f"Error downloading backup file: {e}")
        await update.message.reply_text("❌ Error downloading backup file.")
        return

    try:
        restore_conn = sqlite3.connect(restore_file)
        restore_cursor = restore_conn.cursor()
        # Check if the backup file has the expected table
        restore_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        if not restore_cursor.fetchone():
            await update.message.reply_text("❌ The backup file does not contain the required table.")
            restore_conn.close()
            os.remove(restore_file)
            return

        restore_cursor.execute("SELECT * FROM messages")
        rows = restore_cursor.fetchall()
        restore_conn.close()
    except Exception as e:
        logging.error(f"Error reading backup file: {e}")
        await update.message.reply_text("❌ Error reading backup file.")
        os.remove(restore_file)
        return

    try:
        # Insert rows from the backup file into the current database.
        # Using INSERT OR IGNORE to prevent duplicates based on unique constraints if any.
        for row in rows:
            cursor.execute("""
                INSERT OR IGNORE INTO messages (user_id, username, chat_id, message, date)
                VALUES (?, ?, ?, ?, ?)
            """, row[1:])
        conn.commit()
        os.remove(restore_file)
        await update.message.reply_text("✅ Data has been successfully restored.")
    except Exception as e:
        logging.error(f"Error restoring data: {e}")
        await update.message.reply_text("❌ Error restoring data.")
        if os.path.exists(restore_file):
            os.remove(restore_file)

async def stats(update: Update, context: CallbackContext) -> None:
    """
    Show overall bot statistics including total messages, unique users, top 5 users, and uptime.
    """
    if not update.message:
        return
    try:
        cursor.execute("SELECT COUNT(*) FROM messages")
        total_messages = cursor.fetchone()[0]
    except Exception as e:
        logging.error(f"Error fetching total messages: {e}")
        total_messages = "N/A"

    try:
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM messages")
        unique_users = cursor.fetchone()[0]
    except Exception as e:
        logging.error(f"Error fetching unique users: {e}")
        unique_users = "N/A"

    try:
        cursor.execute("""
            SELECT user_id, username, COUNT(*) as msg_count 
            FROM messages 
            GROUP BY user_id 
            ORDER BY msg_count DESC 
            LIMIT 5
        """)
        top_users = cursor.fetchall()
    except Exception as e:
        logging.error(f"Error fetching top users: {e}")
        top_users = []

    try:
        db_creation_time = os.path.getctime(DB_PATH)
        uptime = datetime.now() - datetime.fromtimestamp(db_creation_time)
    except Exception as e:
        logging.error(f"Error calculating uptime: {e}")
        uptime = "N/A"

    stats_text = (
        f"📊 <b>Overall Bot Statistics</b>\n\n"
        f"📝 <b>Total Messages:</b> {total_messages}\n"
        f"👥 <b>Unique Users:</b> {unique_users}\n"
        f"⏳ <b>Uptime:</b> {uptime if isinstance(uptime, str) else f'{uptime.days} days, {uptime.seconds // 3600} hours'}\n"
    )
    if top_users:
        stats_text += "\n🏆 <b>Top 5 Users:</b>\n"
        for user in top_users:
            display_name = user[1] if user[1] else user[0]
            stats_text += f"{display_name} - {user[2]} messages\n"

    try:
        await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)
        admin_list = "👥 <b>Admin List:</b>\n\n" + "\n".join(f"• {admin}" for admin in admins)
        await update.message.reply_text(admin_list, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"Error sending stats: {e}")

async def list_files(update: Update, context: CallbackContext) -> None:
    """
    List all allowed files stored in the current directory.
    """
    if not update.message:
        return
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ You do not have permission to access this command.")
        return
    files = list_allowed_files()
    if not files:
        response = "ℹ️ No allowed files found."
    else:
        response = "📁 <b>Allowed Files:</b>\n\n" + "\n".join(f"• {f}" for f in files)
    try:
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"Error in list_files: {e}")

async def get_file_command(update: Update, context: CallbackContext) -> None:
    """
    Send the requested file as a document (only allowed files).
    """
    if not update.message:
        return
    if update.message.from_user.id not in admins:
        await update.message.reply_text("❌ You do not have permission to access this command.")
        return
    if not context.args:
        await update.message.reply_text("❌ Please provide the filename as an argument.")
        return
    filename = context.args[0].strip()
    if not is_allowed_file(filename):
        await update.message.reply_text("❌ The requested file is not allowed to be sent.")
        return
    if not os.path.exists(filename):
        await update.message.reply_text("❌ File not found.")
        return
    try:
        with open(filename, "rb") as f:
            await update.message.reply_document(document=f)
    except Exception as e:
        logging.error(f"Error sending file {filename}: {e}")
        await update.message.reply_text("❌ Error sending the file.")

async def get_info(update: Update, context: CallbackContext) -> None:
    """
    Retrieve public information about a user using /get_info <query>.
    Only public data (first_name, last_name, username, id) is returned.
    Note: Due to Telegram API restrictions, the user must have at least once started a conversation with the bot.
    """
    if not update.message:
        return
    if not context.args:
        await update.message.reply_text("❌ Please provide a Telegram username (e.g. @username).")
        return

    query = context.args[0].strip()
    # Only allow queries starting with '@'
    if not query.startswith('@'):
        await update.message.reply_text("❌ Retrieving information by phone number is not supported. Please provide a username starting with '@'.")
        return

    try:
        chat = await context.bot.get_chat(query)
        info_text = "👤 <b>User Information:</b>\n\n"
        info_text += f"👤 First Name: {chat.first_name}\n"
        if chat.last_name:
            info_text += f"👤 Last Name: {chat.last_name}\n"
        if chat.username:
            info_text += f"🔹 Username: @{chat.username}\n"
        info_text += f"💡 ID: {chat.id}\n\n"
        info_text += "ℹ️ Note: Only public information is available. If the user hasn't interacted with the bot, no additional info will be returned."
        await update.message.reply_text(info_text, parse_mode=ParseMode.HTML)
    except BadRequest as e:
        error_msg = str(e).lower()
        if "chat not found" in error_msg:
            await update.message.reply_text("❌ Chat not found. This may be because the user hasn't started a conversation with the bot or the username is incorrect.")
        else:
            await update.message.reply_text(f"❌ Error retrieving information: {e}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error retrieving information: {e}")

# ---------------- Register Handlers ----------------
bot.add_handler(CommandHandler("start", start))
bot.add_handler(CommandHandler("help", help_command))
bot.add_handler(CommandHandler("show_data", show_data))
bot.add_handler(CommandHandler("reply", reply_command))
bot.add_handler(CommandHandler("endreply", endreply_command))
bot.add_handler(CommandHandler("add_admin", add_admin))
bot.add_handler(CommandHandler("remove_admin", remove_admin))
bot.add_handler(CommandHandler("list_admins", list_admins))
bot.add_handler(CommandHandler("backup", backup_db))
bot.add_handler(CommandHandler("restore", restore_db))
bot.add_handler(CommandHandler("stats", stats))
bot.add_handler(CommandHandler("list_files", list_files))
bot.add_handler(CommandHandler("get_file", get_file_command))
bot.add_handler(CommandHandler("get_info", get_info))
bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ---------------- Run Bot ----------------
if __name__ == "__main__":
    try:
        logging.info("Bot is running...")
        bot.run_polling()
    except Exception as e:
        logging.critical(f"Critical error: {e}")
