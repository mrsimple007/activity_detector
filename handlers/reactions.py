import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from config import BOT_IDS_TO_REMOVE, supabase
from utils.helpers import calculate_points, log_activity

logger = logging.getLogger(__name__)


async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new reactions with time-based scoring"""
    reaction_update = update.message_reaction
    user = reaction_update.user
    chat_id = reaction_update.chat.id
    
    if not user:
        logger.info(f"⚠️  Anonymous reaction, skipping")
        return
    
    logger.info(f"❤️  New reaction detected from user {user.id} (@{user.username}) in chat {chat_id}")
    
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

    post_id = reaction_update.message_id
    
    logger.info(f"📌 Reaction to message {post_id} in chat {chat_id}")
    
    try:
        # Try to find the original post timestamp from activity_log
        result = supabase.table('activity_log').select('post_timestamp').eq('post_id', post_id).limit(1).execute()
        
        if result.data and result.data[0].get('post_timestamp'):
            post_timestamp_str = result.data[0]['post_timestamp']
            post_timestamp = datetime.fromisoformat(post_timestamp_str.replace('Z', '+00:00'))
            logger.info(f"📌 Found original post timestamp: {post_timestamp}")
        else:
            post_timestamp = reaction_update.date
            logger.info(f"⚠️  No post timestamp found, using reaction date: {post_timestamp}")

        # Calculate points based on time since post
        logger.info(f"➕ Awarding points for reaction")
        points = calculate_points('reaction', post_timestamp)
        log_activity(user.id, user.username, user.first_name, 'reaction', points, 
                     post_id, post_timestamp, channel_id=channel_id)
        
    except Exception as e:
        logger.error(f"❌ Error processing reaction: {e}")