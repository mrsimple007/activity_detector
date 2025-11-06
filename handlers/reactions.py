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