import logging
from telegram import Update
from telegram.ext import ContextTypes

from config import (
    BOT_IDS_TO_REMOVE, 
    FIRST_COMMENT_POINTS, 
    SECOND_COMMENT_POINTS, 
    THIRD_COMMENT_POINTS, 
    OTHER_COMMENT_POINTS, 
    supabase,
    EARLY_WINDOW_HOURS,
    POINTS_FOR_COMMENT_LATE
)
from utils.helpers import calculate_points, log_activity, check_rate_limit, check_daily_limit
from telegram.constants import MessageOriginType

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
    try:
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
    user = update.message.from_user
    chat_id = update.message.chat_id
        
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

    reply_to_msg = update.message.reply_to_message
    post_id = reply_to_msg.message_id
    post_timestamp = reply_to_msg.date

    forward_origin = reply_to_msg.forward_origin

    if not forward_origin:
        logger.info("⚠️ Reply is not to a channel message, skipping points")
        return

    if forward_origin.type != MessageOriginType.CHANNEL:
        logger.info(f"⚠️ Message is not for the channel post (type={forward_origin.type}), skipping points")
        return

    channel_title = forward_origin.chat.title if forward_origin.chat else "Unknown"
    logger.info(f"✅ Reply is to CHANNEL POST from: {channel_title}")
    # Check if user has already commented on this post
    if has_user_commented_on_post(user.id, post_id):
        logger.info(f"🚫 User {user.id} already commented on post {post_id}, skipping points")
        return

    position = get_comment_position(post_id)
    
    # Calculate time since post
    from datetime import datetime, timezone, timedelta
    time_since_post = datetime.now(timezone.utc) - post_timestamp
    hours_since_post = time_since_post.total_seconds() / 3600
    is_early = hours_since_post <= EARLY_WINDOW_HOURS
    
    # Award points based on position AND time
    if is_early:
        if position == 1:
            points = FIRST_COMMENT_POINTS
            logger.info(f"🥇 FIRST COMMENT (early)! Awarding {points} points")
        elif position == 2:
            points = SECOND_COMMENT_POINTS
            logger.info(f"🥈 SECOND COMMENT (early)! Awarding {points} points")
        elif position == 3:
            points = THIRD_COMMENT_POINTS
            logger.info(f"🥉 THIRD COMMENT (early)! Awarding {points} points")
        else:
            points = OTHER_COMMENT_POINTS
            logger.info(f"💬 Comment #{position} (early). Awarding {points} points")
    else:
        points = POINTS_FOR_COMMENT_LATE
        logger.info(f"⏰ Comment #{position} (late - {hours_since_post:.1f}h after post). Awarding {points} points")
    
    # Log the activity with channel_id
    log_activity(user.id, user.username, user.first_name, 'comment', points, 
                 post_id, post_timestamp, channel_id=channel_id)