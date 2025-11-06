import logging
import os
from datetime import datetime, timedelta
from telegram.helpers import escape_markdown
from telegram import Update, constants
from telegram.ext import Application, MessageHandler, MessageReactionHandler, CommandHandler, filters, ContextTypes
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROUP_CHAT_ID = int(os.environ.get("GROUP_CHAT_ID_EU", "0"))
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "0"))
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Bot IDs to filter out
BOT_IDS_TO_REMOVE = [7967610894]

# Scoring System with time-based multipliers
POINTS_FOR_COMMENT_EARLY = 10  # Within 48 hours
POINTS_FOR_COMMENT_LATE = 3    # After 48 hours
POINTS_FOR_REACTION_EARLY = 3  # Within 48 hours
POINTS_FOR_REACTION_LATE = 1   # After 48 hours
EARLY_WINDOW_HOURS = 48

# Logging Setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


from datetime import datetime, timedelta, timezone  # Add timezone to imports

def calculate_points(activity_type: str, post_timestamp: datetime) -> int:
    """Calculate points based on activity type and time since post"""
    logger.info(f"📊 Calculating points for activity_type='{activity_type}'")
    
    # Use timezone-aware datetime
    now = datetime.now(timezone.utc)
    time_diff = now - post_timestamp
    hours_elapsed = time_diff.total_seconds() / 3600
    is_early = hours_elapsed < EARLY_WINDOW_HOURS
    
    logger.info(f"⏱️  Time since post: {hours_elapsed:.2f} hours (Early: {is_early})")
    
    if activity_type == 'comment':
        points = POINTS_FOR_COMMENT_EARLY if is_early else POINTS_FOR_COMMENT_LATE
        logger.info(f"💬 Comment points awarded: {points}")
        return points
    elif activity_type == 'reaction':
        points = POINTS_FOR_REACTION_EARLY if is_early else POINTS_FOR_REACTION_LATE
        logger.info(f"❤️  Reaction points awarded: {points}")
        return points
    
    logger.warning(f"⚠️  Unknown activity type: {activity_type}, returning 0 points")
    return 0


def has_user_commented_on_post(user_id: int, post_id: int) -> bool:
    """Check if user has already commented on this post"""
    logger.info(f"🔍 Checking if user {user_id} already commented on post {post_id}")
    
    try:
        result = supabase.table('activity_log').select('id').eq('user_id', user_id).eq('post_id', post_id).eq('activity_type', 'comment').execute()
        has_commented = len(result.data) > 0
        
        if has_commented:
            logger.info(f"✅ User {user_id} HAS already commented on post {post_id}")
        else:
            logger.info(f"➕ User {user_id} has NOT commented on post {post_id} yet")
        
        return has_commented
    except Exception as e:
        logger.error(f"❌ Error checking comment status: {e}")
        return False


def log_activity(user_id: int, username: str, first_name: str, activity_type: str, points: int, post_id: int = None, post_timestamp: datetime = None):
    """Log user activity to Supabase"""
    display_name = f"@{username}" if username else first_name
    logger.info(f"📝 Logging activity for user: {display_name} (ID: {user_id})")
    logger.info(f"   Type: {activity_type}, Points: {points}, Post ID: {post_id}")
    
    try:
        # Use timezone-aware datetime
        timestamp = datetime.now(timezone.utc).isoformat()
        data = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'activity_type': activity_type,
            'points': points,
            'timestamp': timestamp,
            'post_id': post_id,
            'post_timestamp': post_timestamp.isoformat() if post_timestamp else None
        }
        
        logger.info(f"💾 Inserting into Supabase: {data}")
        supabase.table('activity_log').insert(data).execute()
        logger.info(f"✅ Successfully logged {activity_type} for {display_name} worth {points} points")
    except Exception as e:
        logger.error(f"❌ Error logging activity to Supabase: {e}")


def get_leaderboard(days: int = None, limit: int = 20):
    """Get leaderboard from Supabase"""
    period_desc = f"last {days} days" if days else "all time"
    logger.info(f"🏆 Fetching leaderboard for {period_desc} (limit: {limit})")
    
    try:
        query = supabase.table('activity_log').select('user_id, username, first_name, points')
        
        if days:
            # Use timezone-aware datetime
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            query = query.gte('timestamp', cutoff_date)
            logger.info(f"📅 Filtering activities since: {cutoff_date}")
        
        result = query.execute()

        # Aggregate points by user
        user_scores = {}
        for row in result.data:
            user_id = row['user_id']
            if user_id not in user_scores:
                user_scores[user_id] = {
                    'user_id': user_id,
                    'username': row['username'],
                    'first_name': row['first_name'],
                    'total_score': 0
                }
            user_scores[user_id]['total_score'] += row['points']
        
        logger.info(f"👥 Aggregated scores for {len(user_scores)} unique users")
        
        # Sort by score and limit
        sorted_users = sorted(user_scores.values(), key=lambda x: x['total_score'], reverse=True)[:limit]
        logger.info(f"📊 Top {len(sorted_users)} users selected for leaderboard")
        
        return sorted_users
    except Exception as e:
        logger.error(f"❌ Error fetching leaderboard: {e}")
        return []


# --- Telegram Bot Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - welcome message for admin"""
    user_id = update.message.from_user.id
    logger.info(f"🚀 /start command received from user {user_id}")
    
    if user_id == ADMIN_USER_ID:
        logger.info(f"👑 Admin user detected")
        welcome_msg = (
            "🎉 *Welcome, Admin!*\n\n"
            "This bot tracks group activity and awards points:\n\n"
            f"📝 *Comment Points:*\n"
            f"  • First 48h: {POINTS_FOR_COMMENT_EARLY} points\n"
            f"  • After 48h: {POINTS_FOR_COMMENT_LATE} points\n\n"
            f"❤️ *Reaction Points:*\n"
            f"  • First 48h: {POINTS_FOR_REACTION_EARLY} points\n"
            f"  • After 48h: {POINTS_FOR_REACTION_LATE} points\n\n"
            "🛠️ *Admin Commands:*\n"
            "/leaderboard \\- View all rankings\n"
            "/resettop \\- Archive and reset scores\n\n"
            "✅ Bot is active and monitoring!"
        )
    else:
        logger.info(f"👤 Regular user")
        welcome_msg = (
            "👋 Hi! I'm the Activity Tracker Bot.\n\n"
            "I track engagement in the group and award points for:\n"
            "• Comments on posts\n"
            "• Reactions to messages\n\n"
            "💡 Engage early (first 48 hours) for bonus points!\n\n"
            "Use /leaderboard to see rankings."
        )
    
    try:
        await update.message.reply_text(welcome_msg, parse_mode=constants.ParseMode.MARKDOWN_V2)
        logger.info(f"✅ Start message sent successfully")
    except Exception as e:
        logger.error(f"❌ Error sending start message: {e}")
        await update.message.reply_text(welcome_msg.replace('\\', '').replace('*', ''))


async def handle_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new comments with time-based scoring"""
    user = update.message.from_user
    logger.info(f"💬 New comment detected from user {user.id} (@{user.username})")
    
    if user.is_bot or user.id in BOT_IDS_TO_REMOVE:
        logger.info(f"🤖 Skipping bot user {user.id}")
        return

    # Must be a reply to award points
    if not update.message.reply_to_message:
        logger.info(f"⚠️  Message is not a reply, skipping point award")
        return

    post_id = update.message.reply_to_message.message_id
    post_timestamp = update.message.reply_to_message.date
    
    logger.info(f"📌 Comment is reply to post {post_id} from {post_timestamp}")

    # Check if user has already commented on this post
    if has_user_commented_on_post(user.id, post_id):
        logger.info(f"🚫 User {user.id} already commented on post {post_id}, skipping points")
        return

    # Calculate points based on time since post
    logger.info(f"➕ Awarding points for new comment")
    points = calculate_points('comment', post_timestamp)
    log_activity(user.id, user.username, user.first_name, 'comment', points, post_id, post_timestamp)


async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new reactions with time-based scoring"""
    reaction_update = update.message_reaction
    user = reaction_update.user
    
    # Skip if user is None (anonymous reactions) or is a bot
    if not user:
        logger.info(f"⚠️  Anonymous reaction, skipping")
        return
    
    logger.info(f"❤️  New reaction detected from user {user.id} (@{user.username})")
    
    if user.is_bot or user.id in BOT_IDS_TO_REMOVE:
        logger.info(f"🤖 Skipping bot user {user.id}")
        return

    post_id = reaction_update.message_id
    chat_id = reaction_update.chat.id
    
    logger.info(f"📌 Reaction to message {post_id} in chat {chat_id}")
    
    try:
        # Try to find the original post timestamp from activity_log
        result = supabase.table('activity_log').select('post_timestamp').eq('post_id', post_id).limit(1).execute()
        
        if result.data and result.data[0].get('post_timestamp'):
            # Use stored timestamp from when someone commented
            post_timestamp_str = result.data[0]['post_timestamp']
            post_timestamp = datetime.fromisoformat(post_timestamp_str.replace('Z', '+00:00'))
            logger.info(f"📌 Found original post timestamp: {post_timestamp}")
        else:
            # Fallback: assume this is a recent post (within 48 hours for max points)
            # Or use a conservative estimate
            post_timestamp = reaction_update.date
            logger.info(f"⚠️  No post timestamp found, using reaction date: {post_timestamp}")

        # Calculate points based on time since post
        logger.info(f"➕ Awarding points for reaction")
        points = calculate_points('reaction', post_timestamp)
        log_activity(user.id, user.username, user.first_name, 'reaction', points, post_id, post_timestamp)
        
    except Exception as e:
        logger.error(f"❌ Error processing reaction: {e}")

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the leaderboard for all time periods"""
    logger.info(f"🏆 /leaderboard command received from user {update.message.from_user.id}")
    
    time_periods = [
        ('Last 7 Days', 7),
        ('Last 14 Days', 14),
        ('Last 30 Days', 30),
        ('All Time', None)
    ]

    full_leaderboard = ""
    
    for title, days in time_periods:
        logger.info(f"📊 Generating leaderboard for: {title}")
        top_users = get_leaderboard(days=days, limit=20)

        if not top_users:
            logger.warning(f"⚠️  No activity for period: {title}")
            continue

        title_escaped = escape_markdown(title, version=2)
        leaderboard_text = f"🏆 *Top 20 \\({title_escaped}\\)* 🏆\n\n"

        for i, user_data in enumerate(top_users):
            username = user_data.get('username')
            first_name = user_data.get('first_name')
            user_id = user_data.get('user_id')
            score = user_data.get('total_score')
            
            display_name_raw = f"@{username}" if username else (first_name or f"User {user_id}")
            display_name_escaped = escape_markdown(display_name_raw, version=2)
            leaderboard_text += f"{i + 1}\\. {display_name_escaped} \\- {score} pts\n"
        
        full_leaderboard += leaderboard_text + "\n"

    if not full_leaderboard:
        logger.warning(f"⚠️  No activity recorded at all")
        await update.message.reply_text("No activity has been recorded yet!")
        return

    try:
        await update.message.reply_text(full_leaderboard.strip(), parse_mode=constants.ParseMode.MARKDOWN_V2)
        logger.info(f"✅ Leaderboard sent successfully")
    except Exception as e:
        logger.error(f"❌ Failed to send leaderboard: {e}")
        await update.message.reply_text(full_leaderboard.replace('\\', ''))


async def reset_scores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset scores (admin only) - archives to a separate table"""
    user_id = update.message.from_user.id
    logger.info(f"🔄 /resettop command received from user {user_id}")
    
    if user_id != ADMIN_USER_ID:
        logger.warning(f"🚫 Unauthorized reset attempt by user {user_id}")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    logger.info(f"👑 Admin authorized, proceeding with reset")
    
    try:
        # Get all current data
        logger.info(f"📥 Fetching all activity records")
        result = supabase.table('activity_log').select('*').execute()
        
        if result.data:
            record_count = len(result.data)
            logger.info(f"📦 Found {record_count} records to archive")
            
            # Archive to activity_log_archive with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            logger.info(f"🕐 Archive timestamp: {timestamp}")
            
            for idx, row in enumerate(result.data):
                row['archive_timestamp'] = timestamp
                supabase.table('activity_log_archive').insert(row).execute()
                if (idx + 1) % 100 == 0:
                    logger.info(f"📤 Archived {idx + 1}/{record_count} records")
            
            logger.info(f"✅ All {record_count} records archived successfully")
            
            # Delete all records from main table
            logger.info(f"🗑️  Deleting records from main table")
            supabase.table('activity_log').delete().neq('id', 0).execute()
            logger.info(f"✅ Main table cleared")
            
            await update.message.reply_text(f"✅ Activity log archived and reset! {record_count} records archived.")
            logger.info(f"🎉 Reset completed successfully")
        else:
            logger.info(f"⚠️  No records found to archive")
            await update.message.reply_text("No records to archive.")
            
    except Exception as e:
        logger.error(f"❌ Error resetting scores: {e}")
        await update.message.reply_text(f"❌ An error occurred while resetting the log: {e}")


def main():
    """Start the bot"""
    logger.info("=" * 60)
    logger.info("🤖 TELEGRAM ACTIVITY TRACKER BOT STARTING")
    logger.info("=" * 60)
    logger.info(f"📍 Group Chat ID: {GROUP_CHAT_ID}")
    logger.info(f"👑 Admin User ID: {ADMIN_USER_ID}")
    logger.info(f"⏰ Early Window: {EARLY_WINDOW_HOURS} hours")
    logger.info(f"💬 Comment Points: {POINTS_FOR_COMMENT_EARLY} (early) / {POINTS_FOR_COMMENT_LATE} (late)")
    logger.info(f"❤️  Reaction Points: {POINTS_FOR_REACTION_EARLY} (early) / {POINTS_FOR_REACTION_LATE} (late)")
    logger.info("=" * 60)
    
    application = Application.builder().token(BOT_TOKEN).build()
    group_filter = filters.Chat(chat_id=GROUP_CHAT_ID)

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("leaderboard", show_leaderboard))
    application.add_handler(CommandHandler("resettop", reset_scores))

    # Message and reaction handlers (award points)
    application.add_handler(MessageHandler(group_filter & filters.TEXT & ~filters.COMMAND, handle_comment))
    application.add_handler(MessageReactionHandler(handle_reaction, chat_id=GROUP_CHAT_ID))

    logger.info("✅ All handlers registered")
    logger.info("🚀 Starting polling...")
    application.run_polling(allowed_updates=[Update.MESSAGE, Update.MESSAGE_REACTION])


if __name__ == '__main__':
    main()