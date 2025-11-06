import logging
import random
from datetime import datetime, timezone
from telegram import Update, constants
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
from datetime import timedelta

from config import (
    supabase, 
    ADMIN_USER_ID_EU,
    POINTS_FOR_COMMENT_EARLY,
    POINTS_FOR_COMMENT_LATE,
    POINTS_FOR_REACTION_EARLY,
    POINTS_FOR_REACTION_LATE,
    GROUP_CHAT_ID
)
from utils.helpers import get_leaderboard

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - welcome message for admin"""
    user_id = update.message.from_user.id
    logger.info(f"🚀 /start command received from user {user_id}")
    
    if user_id == ADMIN_USER_ID_EU:
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
            "/contest \\- Post leaderboard for contest\n"
            "/pickwinner \\- Pick random winner from top 10\n"
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


async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the leaderboard with user's position and date range"""
    user_id = update.message.from_user.id
    logger.info(f"🏆 /leaderboard command received from user {user_id}")
    
    time_periods = [
        ('Last 7 Days', 7),
        ('Last 14 Days', 14),
    ]

    full_leaderboard = ""
    
    for title, days in time_periods:
        logger.info(f"📊 Generating leaderboard for: {title}")
        
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        if days:
            start_date = end_date - timedelta(days=days)
            date_range = f"{start_date.strftime('%d %b')} dan {end_date.strftime('%d %b')} gacha hisoblangan"
        else:
            date_range = "Barcha vaqt"
        
        # Get ALL users to find requesting user's position
        all_users = get_leaderboard(days=days, limit=None)  # Get all users
        top_users = all_users[:20]  # Top 20 for display

        if not all_users:
            logger.warning(f"⚠️  No activity for period: {title}")
            continue

        # Find requesting user's position and data
        user_position = None
        user_score = 0
        user_last_activity = None
        
        for idx, user_data in enumerate(all_users):
            if user_data.get('user_id') == user_id:
                user_position = idx + 1
                user_score = user_data.get('total_score', 0)
                # Get last activity date for this user
                try:
                    query = supabase.table('activity_log').select('timestamp').eq('user_id', user_id)
                    if days:
                        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
                        query = query.gte('timestamp', cutoff_date)
                    result = query.order('timestamp', desc=True).limit(1).execute()
                    if result.data:
                        timestamp_str = result.data[0]['timestamp']
                        user_last_activity = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except Exception as e:
                    logger.error(f"Error getting user's last activity: {e}")
                break

        title_escaped = escape_markdown(title, version=2)
        date_range_escaped = escape_markdown(date_range, version=2)
        
        leaderboard_text = f"📊 *Eng faol foydalanuvchilar \\({title_escaped}\\)*\n"
        leaderboard_text += f"_{date_range_escaped}_\n\n"

        # Display top 20
        for i, user_data in enumerate(top_users):
            username = user_data.get('username')
            first_name = user_data.get('first_name')
            user_id_display = user_data.get('user_id')
            score = user_data.get('total_score')
            
            display_name_raw = f"@{username}" if username else (first_name or f"User {user_id_display}")
            display_name_escaped = escape_markdown(display_name_raw, version=2)
            
            # Add medals for top 3
            if i == 0:
                rank = "🥇"
            elif i == 1:
                rank = "🥈"
            elif i == 2:
                rank = "🥉"
            else:
                rank = f"{i + 1}\\."
            
            leaderboard_text += f"{rank} {display_name_escaped} \\- {score} pts\n"
        
        # Show user's position if they're in the list
        if user_position:
            leaderboard_text += f"\n🎯 *Sizning pozitsiyangiz:* \\#{user_position} \\- {user_score} ball"
            if user_last_activity:
                last_activity_str = user_last_activity.strftime("%d\\.%m %H:%M")
                leaderboard_text += f" \\({last_activity_str}\\)"
        else:
            leaderboard_text += f"\n💡 _Siz hali faollik ko'rsatmagansiz\\._"
        
        full_leaderboard += leaderboard_text + "\n\n"

    if not full_leaderboard:
        logger.warning(f"⚠️  No activity recorded at all")
        await update.message.reply_text("Hali hech qanday faollik qayd etilmagan!")
        return

    try:
        await update.message.reply_text(full_leaderboard.strip(), parse_mode=constants.ParseMode.MARKDOWN_V2)
        logger.info(f"✅ Leaderboard sent successfully")
    except Exception as e:
        logger.error(f"❌ Failed to send leaderboard: {e}")
        await update.message.reply_text(full_leaderboard.replace('\\', ''))

async def post_contest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Post contest leaderboard to the group (admin only)"""
    user_id = update.message.from_user.id
    logger.info(f"🎯 /contest command received from user {user_id}")
    
    if user_id != ADMIN_USER_ID:
        logger.warning(f"🚫 Unauthorized contest post attempt by user {user_id}")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    logger.info(f"👑 Admin authorized, posting contest leaderboard")
    
    try:
        # Get top 10 users
        top_users = get_leaderboard(days=None, limit=10)
        
        if not top_users:
            await update.message.reply_text("No activity recorded yet!")
            return
        
        # Create contest message
        contest_msg = "🎉 *CONTEST FINISHED\\!* 🎉\n\n"
        contest_msg += "🏆 *Top 10 Users:*\n\n"
        
        for i, user_data in enumerate(top_users):
            username = user_data.get('username')
            first_name = user_data.get('first_name')
            user_id = user_data.get('user_id')
            score = user_data.get('total_score')
            
            display_name_raw = f"@{username}" if username else (first_name or f"User {user_id}")
            display_name_escaped = escape_markdown(display_name_raw, version=2)
            
            if i == 0:
                medal = "🥇"
            elif i == 1:
                medal = "🥈"
            elif i == 2:
                medal = "🥉"
            else:
                medal = f"{i + 1}\\."
            
            contest_msg += f"{medal} {display_name_escaped} \\- {score} pts\n"
        
        contest_msg += "Random winner will be picked from Top 10\\.\n\n"
        contest_msg += "🎁 *Bonus Points for Comments:*\n"
        contest_msg += "• 1st comment: 15 points\n"
        contest_msg += "• 2nd comment: 14 points\n"
        contest_msg += "• 3rd comment: 13 points\n"
        contest_msg += "• All other comments: 10 points"
        
        # Send to group
        sent_message = await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=contest_msg,
            parse_mode=constants.ParseMode.MARKDOWN_V2
        )
        
        # Store contest post ID in context for tracking
        if 'contest_post_id' not in context.bot_data:
            context.bot_data['contest_post_id'] = []
        context.bot_data['contest_post_id'].append(sent_message.message_id)
        
        logger.info(f"✅ Contest posted successfully with message_id: {sent_message.message_id}")
        await update.message.reply_text(f"✅ Contest posted to group! Message ID: {sent_message.message_id}")
        
    except Exception as e:
        logger.error(f"❌ Error posting contest: {e}")
        await update.message.reply_text(f"❌ Error posting contest: {e}")


async def pick_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pick a random winner from top 10 users (admin only)"""
    user_id = update.message.from_user.id
    logger.info(f"🎲 /pickwinner command received from user {user_id}")
    
    if user_id != ADMIN_USER_ID:
        logger.warning(f"🚫 Unauthorized winner pick attempt by user {user_id}")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    logger.info(f"👑 Admin authorized, picking winner")
    
    try:
        # Get top 10 users
        top_users = get_leaderboard(days=None, limit=10)
        
        if not top_users:
            await update.message.reply_text("No users to pick from!")
            return
        
        # Pick random winner
        winner = random.choice(top_users)
        username = winner.get('username')
        first_name = winner.get('first_name')
        winner_id = winner.get('user_id')
        score = winner.get('total_score')
        
        display_name_raw = f"@{username}" if username else (first_name or f"User {winner_id}")
        display_name_escaped = escape_markdown(display_name_raw, version=2)
        
        # Create winner announcement
        winner_msg = "🎊 *WINNER ANNOUNCEMENT\\!* 🎊\n\n"
        winner_msg += f"🎉 Congratulations {display_name_escaped}\\!\n\n"
        winner_msg += f"🏆 Score: {score} points\n\n"
        winner_msg += "You've been randomly selected from our Top 10\\!"
        
        # Send to group
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=winner_msg,
            parse_mode=constants.ParseMode.MARKDOWN_V2
        )
        
        logger.info(f"✅ Winner announced: {display_name_raw}")
        await update.message.reply_text(f"✅ Winner announced: {display_name_raw}")
        
    except Exception as e:
        logger.error(f"❌ Error picking winner: {e}")
        await update.message.reply_text(f"❌ Error picking winner: {e}")


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
            
            # Clear contest post IDs
            if 'contest_post_id' in context.bot_data:
                context.bot_data['contest_post_id'] = []
            
            await update.message.reply_text(f"✅ Activity log archived and reset! {record_count} records archived.")
            logger.info(f"🎉 Reset completed successfully")
        else:
            logger.info(f"⚠️  No records found to archive")
            await update.message.reply_text("No records to archive.")
            
    except Exception as e:
        logger.error(f"❌ Error resetting scores: {e}")
        await update.message.reply_text(f"❌ An error occurred while resetting the log: {e}")