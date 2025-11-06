import sqlite3
import logging
import os
from datetime import datetime, timedelta
from telegram.helpers import escape_markdown
from telegram import Update, constants
from telegram.ext import Application, MessageHandler, MessageReactionHandler, CommandHandler, filters, ContextTypes

# --- Configuration ---
BOT_TOKEN = "7967610894:AAFuMGTxhHe0wP_F0Epijqi4gdj-qY6I6yg"
GROUP_CHAT_ID = -1002824929840
ADMIN_USER_ID = 122290051
# 8298580491,  # Admin ID2

BOT_IDS_TO_REMOVE = [
    7967610894  # activity_bot ID
]

# Scoring System
POINTS_FOR_COMMENT = 5
POINTS_FOR_REACTION = 2

# --- Logging Setup ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Database Functions ---
def setup_database():
    """Initialize the database with required tables"""
    conn = sqlite3.connect('activity.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT,
        first_name TEXT,
        activity_type TEXT NOT NULL,
        points INTEGER NOT NULL,
        timestamp DATETIME NOT NULL,
        post_id INTEGER
    )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database initialized with activity_log table.")


def clean_database():
    """Remove all activity from specified bot IDs"""
    try:
        conn = sqlite3.connect('activity.db')
        cursor = conn.cursor()

        # Using a tuple for the WHERE IN clause
        placeholders = ','.join('?' for _ in BOT_IDS_TO_REMOVE)
        query = f"DELETE FROM activity_log WHERE user_id IN ({placeholders})"

        cursor.execute(query, BOT_IDS_TO_REMOVE)

        # Get the number of rows deleted
        rows_deleted = cursor.rowcount

        conn.commit()
        conn.close()

        logger.info(f"Cleanup complete. Successfully deleted {rows_deleted} records belonging to the bots.")

    except sqlite3.Error as e:
        logger.error(f"An error occurred during database cleanup: {e}")


def has_user_commented_on_post(user_id, post_id):
    """Check if user has already commented on this post"""
    conn = sqlite3.connect('activity.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM activity_log WHERE user_id = ? AND post_id = ? AND activity_type = 'comment'",
        (user_id, post_id)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


def log_activity(user_id, username, first_name, activity_type, points, post_id=None):
    """Log user activity to the database"""
    conn = sqlite3.connect('activity.db')
    cursor = conn.cursor()
    timestamp = datetime.utcnow()
    cursor.execute(
        "INSERT INTO activity_log (user_id, username, first_name, activity_type, points, timestamp, post_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, username, first_name, activity_type, points, timestamp, post_id)
    )
    conn.commit()
    conn.close()
    display_name = f"@{username}" if username else first_name
    logger.info(f"Logged {activity_type} for {display_name} worth {points} points. Post ID: {post_id}")


# --- Telegram Bot Handlers ---
async def handle_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new comments, ignoring bots and commands"""
    user = update.message.from_user
    if user.is_bot:
        return

    # Determine post ID: if it's a reply, use the replied message ID, otherwise use current message ID
    if update.message.reply_to_message:
        post_id = update.message.reply_to_message.message_id
    else:
        logger.info(f"User {user.id} already commented on post, skipping points")
        #post_id = update.message.message_id
        return

    # Check if user has already commented on this post
    if has_user_commented_on_post(user.id, post_id):
        logger.info(f"User {user.id} already commented on post {post_id}, skipping points")
        return

    log_activity(user.id, user.username, user.first_name, 'comment', POINTS_FOR_COMMENT, post_id)


async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new reactions, ignoring bots"""
    user = update.message_reaction.user
    if user.is_bot:
        return

    # For reactions, we don't need post_id since reactions are always counted
    log_activity(user.id, user.username, user.first_name, 'reaction', POINTS_FOR_REACTION)


async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the leaderboard for different time periods"""
    args = context.args
    period = 'month' if not args else args[0].lower()
    time_periods = {
        'week': ('Last 7 Days', 7),
        '2weeks': ('Last 14 Days', 14),
        'month': ('Last 30 Days', 30),
        'all': ('All Time', None)
    }

    if period not in time_periods:
        await update.message.reply_text("Invalid time period. Use: /leaderboard [week|2weeks|month|all]")
        return

    title, days = time_periods[period]
    time_limit = datetime.utcnow() - timedelta(days=days) if days else None

    conn = sqlite3.connect('activity.db')
    cursor = conn.cursor()
    query = "SELECT user_id, username, first_name, SUM(points) as total_score FROM activity_log"
    params = []

    if time_limit:
        query += " WHERE timestamp >= ?"
        params.append(time_limit)

    query += " GROUP BY user_id ORDER BY total_score DESC LIMIT 20"
    cursor.execute(query, params)
    top_users = cursor.fetchall()
    conn.close()

    if not top_users:
        await update.message.reply_text(f"No activity has been recorded for the period: {title}!")
        return

    title_escaped = escape_markdown(title, version=2)
    leaderboard_text = f"🏆 *Top 20 Active Members \\({title_escaped}\\)* 🏆\n\n"

    for i, (user_id, username, first_name, score) in enumerate(top_users):
        display_name_raw = f"@{username}" if username else (first_name or f"User {user_id}")
        display_name_escaped = escape_markdown(display_name_raw, version=2)
        leaderboard_text += f"{i + 1}\\. {display_name_escaped} \\- {score} points\n"

    try:
        await update.message.reply_text(leaderboard_text, parse_mode=constants.ParseMode.MARKDOWN_V2)
    except Exception as e:
        logger.error(f"Failed to send leaderboard: {e}")
        await update.message.reply_text(leaderboard_text.replace('\\', ''))


async def reset_scores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset scores (admin only)"""
    user_id = update.message.from_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    try:
        timestamp = datetime.now().strftime("%Y-%m")
        archive_name = f"activity_log_{timestamp}.db"

        if os.path.exists('activity.db'):
            os.rename('activity.db', archive_name)
            logger.info(f"Database archived as {archive_name}")

        setup_database()
        await update.message.reply_text("The activity log has been archived and reset for the new period!")
    except Exception as e:
        logger.error(f"Error resetting scores: {e}")
        await update.message.reply_text(f"An error occurred while resetting the log: {e}")


def main():
    """Start the bot"""
    setup_database()
    clean_database()

    application = Application.builder().token(BOT_TOKEN).build()
    group_filter = filters.Chat(chat_id=GROUP_CHAT_ID)

    # Handler for regular messages (awards points)
    application.add_handler(MessageHandler(group_filter & filters.TEXT & ~filters.COMMAND, handle_comment))

    # Handler for reactions (awards points)
    application.add_handler(MessageReactionHandler(handle_reaction, chat_id=GROUP_CHAT_ID))

    # Handlers for specific commands (do not award points)
    application.add_handler(CommandHandler("leaderboard", show_leaderboard, filters=group_filter))
    application.add_handler(CommandHandler("resettop", reset_scores, filters=group_filter))

    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=[Update.MESSAGE, Update.MESSAGE_REACTION])


if __name__ == '__main__':
    main()