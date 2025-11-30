import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
from config import *

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# Check if user is member of the channel
async def check_channel_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is member of the channel"""
    try:
        channel_id = f"@{CHANNEL_USERNAME}"
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        is_member = member.status in ['member', 'administrator', 'creator']
        logger.info(f"Channel membership check for user {user_id}: {is_member}")
        return is_member
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
        return False


# Start command handler
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id
    
    logger.info(f"User {user_id} ({user.first_name}) started the bot")
    
    # Check channel membership
    is_member = await check_channel_membership(user_id, context)
    
    if not is_member:
        # User is not a member, ask to join
        keyboard = [
            [InlineKeyboardButton("✅ Kanalga a'zo bo'lish", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton("🔄 Tekshirish", callback_data="check_membership")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Assalomu alaykum, {user.first_name}! 👋\n\n"
            "Xush kelibsiz!\n\n"
            "Work and Travel bo'yicha barcha ma'lumotlar jamlangan kanal linkini olish uchun avval bizning kanalimizga a'zo bo'lishingiz kerak.\n\n"
            "👇 Quyidagi tugmani bosib kanalga qo'shiling va keyin 'Tekshirish' tugmasini bosing.",
            reply_markup=reply_markup
        )
    else:
        # User is a member, send private channel link
        await update.message.reply_text(
            f"✅ Rahmat!\n\n"
            f"Work and Travel bo'yicha ma'lumotlar uchun quyidagi kanalga kiring:\n\n"
            f"👉 {PRIVATE_CHANNEL_LINK}"
        )


# Check membership callback
async def check_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle membership check callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    is_member = await check_channel_membership(user_id, context)
    
    if is_member:
        # User is now a member, send private channel link
        await query.message.edit_text(
            f"✅ Rahmat!\n\n"
            f"Barcha ma'lumotlar uchun quyidagi kanalga kiring:\n\n"
            f"👉 {PRIVATE_CHANNEL_LINK}"
        )
    else:
        await query.answer(
            "❌ Siz hali kanalga a'zo bo'lmadingiz. Iltimos, avval kanalga qo'shiling!",
            show_alert=True
        )


# Callback query handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    data = query.data
    
    if data == "check_membership":
        await check_membership_callback(update, context)


# Main function
def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start the bot
    logger.info("🚀 Bot started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()