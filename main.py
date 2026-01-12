import logging
import os
from telegram import Update
from telegram.ext import Application, MessageHandler, MessageReactionHandler, CommandHandler, filters, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv

from config import (
    BOT_TOKEN, GROUP_CHAT_ID, ADMIN_USER_ID_EU, 
    EARLY_WINDOW_HOURS, POINTS_FOR_COMMENT_EARLY, 
    POINTS_FOR_COMMENT_LATE, POINTS_FOR_REACTION_EARLY, 
    POINTS_FOR_REACTION_LATE
)
from handlers.commands import (
    start_command, 
    show_leaderboard, 
    reset_scores, 
    post_contest, 
    pick_winner, 
    referral_command, 
    check_subscription_callback,
    handle_menu_callback,
    handle_boost_callback,
    check_boost_status_callback
)
from handlers.messages import handle_comment
from handlers.reactions import handle_reaction

load_dotenv()


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Silence noisy libs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.ExtBot").setLevel(logging.WARNING)


def main():
    """Start the bot"""
    logger.info("=" * 60)
    logger.info("🤖 TELEGRAM ACTIVITY TRACKER BOT STARTING")
    logger.info("=" * 60)
    logger.info(f"📍 Group Chat ID: {GROUP_CHAT_ID}")
    logger.info(f"👑 Admin User ID: {ADMIN_USER_ID_EU}")
    logger.info(f"⏰ Early Window: {EARLY_WINDOW_HOURS} hours")
    logger.info(f"💬 Comment Points: {POINTS_FOR_COMMENT_EARLY} (early) / {POINTS_FOR_COMMENT_LATE} (late)")
    logger.info(f"❤️ Reaction Points: {POINTS_FOR_REACTION_EARLY} (early) / {POINTS_FOR_REACTION_LATE} (late)")
    logger.info("=" * 60)
    
    application = Application.builder().token(BOT_TOKEN).build()
    group_filter = filters.Chat(chat_id=GROUP_CHAT_ID)

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("leaderboard", show_leaderboard))
    application.add_handler(CommandHandler("resettop", reset_scores))
    application.add_handler(CommandHandler("contest", post_contest))
    application.add_handler(CommandHandler("pickwinner", pick_winner))
    application.add_handler(CommandHandler("referral", referral_command))
    
    # Callback query handlers for menu system
    application.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription_referral$"))
    application.add_handler(CallbackQueryHandler(handle_boost_callback, pattern="^boost_channel$"))
    application.add_handler(CallbackQueryHandler(check_boost_status_callback, pattern="^check_boost_status$"))
    application.add_handler(CallbackQueryHandler(handle_menu_callback, pattern="^menu_"))
    application.add_handler(CallbackQueryHandler(handle_menu_callback, pattern="^show_referral_info$"))

    # Message and reaction handlers (award points)
    application.add_handler(MessageHandler(group_filter & filters.TEXT & ~filters.COMMAND, handle_comment))
    application.add_handler(MessageReactionHandler(handle_reaction, chat_id=GROUP_CHAT_ID))

    logger.info("✅ All handlers registered")
    logger.info("🚀 Starting polling...")
    application.run_polling(allowed_updates=[Update.MESSAGE, Update.MESSAGE_REACTION, Update.CALLBACK_QUERY])


if __name__ == '__main__':
    main()