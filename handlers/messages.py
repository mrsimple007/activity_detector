import logging
from telegram import Update
from telegram.ext import ContextTypes

from config import (
    BOT_IDS_TO_REMOVE, 
    FIRST_COMMENT_POINTS, 
    SECOND_COMMENT_POINTS, 
    THIRD_COMMENT_POINTS, 
    OTHER_COMMENT_POINTS, 
    supabase
)
from utils.helpers import log_activity

logger = logging.getLogger(__name__)


def get_comment_position(post_id: int) -> int:
    """Get the position of this comment on the post (1st, 2nd, 3rd, etc.)"""
    try:
        # Count how many comments already exist on this post
        result = supabase.table('activity_log')\
            .select('id')\
            .eq('post_id', post_id)\
            .eq('activity_type', 'comment')\
            .execute()
        
        current_position = len(result.data) + 1
        logger.info(f"📊 Found {len(result.data)} existing comments on post {post_id}, this will be comment #{current_position}")
        return current_position
    except Exception as e:
        logger.error(f"❌ Error getting comment position: {e}")
        return 999  # Return high number to give default points


def has_user_commented_on_post(user_id: int, post_id: int) -> bool:
    """Check if user has already commented on this specific post"""
    try:
        logger.info(f"🔍 Checking if user {user_id} already commented on post {post_id}")
        result = supabase.table('activity_log')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('post_id', post_id)\
            .eq('activity_type', 'comment')\
            .execute()
        
        has_commented = len(result.data) > 0
        if has_commented:
            logger.info(f"🚫 User {user_id} has ALREADY commented on post {post_id}")
        else:
            logger.info(f"➕ User {user_id} has NOT commented on post {post_id} yet")
        return has_commented
    except Exception as e:
        logger.error(f"❌ Error checking user comment: {e}")
        return False


async def handle_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new comments with position-based scoring"""
    user = update.message.from_user
    chat_id = update.message.chat_id
    
    logger.info(f"💬 New comment detected from user {user.id} (@{user.username}) in chat {chat_id}")
    
    if user.is_bot or user.id in BOT_IDS_TO_REMOVE:
        logger.info(f"🤖 Skipping bot user {user.id}")
        return

    # Determine which channel this is for
    from config import GROUP_CHAT_ID, GROUP_CHAT_ID_2, CHANNEL_ID_UZBEK_EUROPE, CHANNEL_ID_MUSLIMBEK
    
    if chat_id == GROUP_CHAT_ID:
        channel_id = CHANNEL_ID_UZBEK_EUROPE
    elif chat_id == GROUP_CHAT_ID_2:
        channel_id = CHANNEL_ID_MUSLIMBEK
    else:
        logger.warning(f"⚠️ Unknown chat_id: {chat_id}, skipping")
        return
    
    logger.info(f"📺 Channel identified: {channel_id}")

    # Must be a reply to award points
    if not update.message.reply_to_message:
        logger.info(f"⚠️ Message is not a reply, skipping point award")
        return

    post_id = update.message.reply_to_message.message_id
    post_timestamp = update.message.reply_to_message.date
    
    logger.info(f"📌 Comment is reply to post {post_id} from {post_timestamp}")

    # Check if user has already commented on this post
    if has_user_commented_on_post(user.id, post_id):
        logger.info(f"🚫 User {user.id} already commented on post {post_id}, skipping points")
        return

    # Get comment position for this post
    position = get_comment_position(post_id)
    logger.info(f"📍 Comment position on post {post_id}: #{position}")
    
    # Award points based on position
    if position == 1:
        points = FIRST_COMMENT_POINTS
        logger.info(f"🥇 FIRST COMMENT! Awarding {points} points")
    elif position == 2:
        points = SECOND_COMMENT_POINTS
        logger.info(f"🥈 SECOND COMMENT! Awarding {points} points")
    elif position == 3:
        points = THIRD_COMMENT_POINTS
        logger.info(f"🥉 THIRD COMMENT! Awarding {points} points")
    else:
        points = OTHER_COMMENT_POINTS
        logger.info(f"💬 Comment #{position}. Awarding {points} points")
    
    # Log the activity with channel_id
    log_activity(user.id, user.username, user.first_name, 'comment', points, 
                 post_id, post_timestamp, channel_id=channel_id)