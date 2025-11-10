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
    GROUP_CHAT_ID,
    POINTS_FOR_REFERRAL,
    POINTS_FOR_JOINING,
    CHANNEL_USERNAME
)
from utils.helpers import get_leaderboard, log_activity

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - welcome message and referral tracking"""
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    first_name = update.message.from_user.first_name
    
    # Get referral payload if exists
    referral_payload = context.args[0] if context.args else None
    
    logger.info(f"🚀 /start command received from user {user_id}")
    if referral_payload:
        logger.info(f"🔗 Referral payload: {referral_payload}")
    
    # Handle referral
    if referral_payload:
        from utils.helpers import get_referrer_from_payload, has_user_joined_before, log_referral, check_channel_membership
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        referrer_id = get_referrer_from_payload(referral_payload)
        
        if referrer_id and referrer_id != user_id:
            # Check if user already joined before
            if has_user_joined_before(user_id):
                await update.message.reply_text(
                    "👋 Xush kelibsiz\\!\n\n"
                    "Siz allaqachon botga qo'shilgansiz va ballaringiz hisobga olingan\\.\n\n"
                    "📊 /leaderboard \\- reytingni ko'rish\n"
                    "🔗 /referral \\- do'stlarni taklif qilish",
                    parse_mode=constants.ParseMode.MARKDOWN_V2
                )
                return  
            
            # Check channel membership
            is_member = await check_channel_membership(user_id, context)
            
            if is_member:
                # Award points immediately
                log_referral(referrer_id, user_id, username, first_name)
                log_activity(referrer_id, None, None, 'referral', POINTS_FOR_REFERRAL, post_id=user_id)
                log_activity(user_id, username, first_name, 'joining', POINTS_FOR_JOINING)
                
                welcome_text = (
                    f"🎉 *Xush kelibsiz, {escape_markdown(first_name, version=2)}\\!*\n\n"
                    f"✅ Siz *{POINTS_FOR_JOINING} ball* oldingiz\\!\n"
                    f"🎁 Sizni taklif qilgan foydalanuvchi *{POINTS_FOR_REFERRAL} ball* oldi\\!\n\n"
                    f"🇩🇪 *Yevropalik o'zbek* jamoasiga xush kelibsiz\\!\n\n"
                    f"📌 *Nima qilishingiz mumkin:*\n"
                    f"• Guruhdagi postlarga izoh qoldiring\n"
                    f"• Postlarga reaction bering\n"
                    f"• Do'stlaringizni taklif qiling\n"
                    f"• Ballar yig'ing va sovg'alar yutib oling\\!\n\n"
                    f"💡 *Foydali buyruqlar:*\n"
                    f"/leaderboard \\- Reytingni ko'rish\n"
                    f"/referral \\- Do'stlarni taklif qilish\n\n"
                    f"🚀 Faol bo'ling va ko'proq ball to'plang\\!"
                )
                
                await update.message.reply_text(welcome_text, parse_mode=constants.ParseMode.MARKDOWN_V2)
                
                # Notify referrer
                try:
                    referrer_name = f"@{username}" if username else first_name
                    referrer_name_escaped = escape_markdown(referrer_name, version=2)
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 *Tabriklaymiz\\!*\n\n{referrer_name_escaped} sizning havolangiz orqali qo'shildi\\!\n\n✨ \\+{POINTS_FOR_REFERRAL} ball hisobingizga qo'shildi\\!",
                        parse_mode=constants.ParseMode.MARKDOWN_V2
                    )
                except Exception as e:
                    logger.error(f"Failed to notify referrer: {e}")
                
                return  
            else:
                context.user_data['pending_referral'] = {
                    'referrer_id': referrer_id,
                    'user_id': user_id,
                    'username': username,
                    'first_name': first_name
                }
                
                # Create inline keyboard with channel link and check button
                keyboard = [
                    [InlineKeyboardButton("📢 Kanalga qo'shilish", url=f"https://t.me/{CHANNEL_USERNAME}")],
                    [InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_subscription_referral")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                join_message = (
                    f"📢 *Botdan foydalanish uchun kanalga qo'shiling\\!*\n\n"
                    f"🇩🇪 *Yevropalik o'zbek* \\- Germaniyaga kelganlar va kelmoqchi bo'lganlar uchun:\n\n"
                    f"✅ O'qish va grant imkoniyatlari\n"
                    f"✅ Ish topish yo'llari\n"
                    f"✅ Immigratsiya masalalari\n"
                    f"✅ Hayot haqida foydali ma'lumotlar\n"
                    f"✅ Hammasi oddiy va tushunarli tilda\\!\n\n"
                    f"👇 Quyidagi tugmani bosing va kanalga qo'shiling, keyin obunani tekshiring\\!\n\n"
                    f"Qo'shilganingizdan keyin *{POINTS_FOR_JOINING} ball* olasiz\\!"
                )
                await update.message.reply_text(
                    join_message, 
                    parse_mode=constants.ParseMode.MARKDOWN_V2,
                    reply_markup=reply_markup
                )
                return  
        elif referrer_id == user_id:
            await update.message.reply_text(
                "❌ O'z referal havolangizdan foydalana olmaysiz\\!",
                parse_mode=constants.ParseMode.MARKDOWN_V2
            )
            return
    
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
            f"🔗 *Referral Points:*\n"
            f"  • Per referral: {POINTS_FOR_REFERRAL} points\n"
            f"  • New user bonus: {POINTS_FOR_JOINING} points\n\n"
            "🛠️ *Admin Commands:*\n"
            "/leaderboard \\- View all rankings\n"
            "/contest \\- Post leaderboard for contest\n"
            "/pickwinner \\- Pick random winner from top 10\n"
            "/resettop \\- Archive and reset scores\n"
            "/referral \\- Your referral link\n\n"
            "✅ Bot is active and monitoring!"
        )
    else:
        logger.info(f"👤 Regular user - showing regular welcome")
        welcome_msg = (
            f"👋 Salom, {escape_markdown(first_name, version=2)}\\!\n\n"
            f"🇩🇪 *Yevropalik o'zbek* guruhi faollik botiga xush kelibsiz\\!\n\n"
            f"📊 *Ballar qanday ishlab topiladi:*\n"
            f"• 💬 Postlarga izoh \\(10/3 ball\\)\n"
            f"• ❤️ Postlarga reaction \\(3/1 ball\\)\n"
            f"• 👥 Do'stlarni taklif qilish \\({POINTS_FOR_REFERRAL} ball\\)\n\n"
            f"💡 *Birinchi 48 soatda faol bo'ling* \\- ko'proq ball\\!\n\n"
            f"🎁 *Foydali buyruqlar:*\n"
            f"/leaderboard \\- Reytingni ko'rish\n"
            f"/referral \\- Do'stlarni taklif qilish\n\n"
            f"🏆 Faol bo'ling va sovg'alar yutib oling\\!"
        )
    
    try:
        await update.message.reply_text(welcome_msg, parse_mode=constants.ParseMode.MARKDOWN_V2)
        logger.info(f"✅ Start message sent successfully")
    except Exception as e:
        logger.error(f"❌ Error sending start message: {e}")
        await update.message.reply_text(welcome_msg.replace('\\', '').replace('*', ''))


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's referral link and stats with detailed explanation"""
    user_id = update.message.from_user.id
    bot_username = (await context.bot.get_me()).username
    
    from utils.helpers import generate_referral_link

    
    # Generate referral link
    referral_link = generate_referral_link(user_id, bot_username)
    
    # Get referral count
    try:
        result = supabase.table('referrals').select('id').eq('referrer_id', user_id).execute()
        referral_count = len(result.data)
    except:
        referral_count = 0
    
    total_earned = referral_count * POINTS_FOR_REFERRAL
    
    message = (
        f"🎁 *DO'STLARINGIZNI TAKLIF QILING\\!*\n\n"
        f"🇩🇪 *Yevropalik o'zbek* jamoasiga qo'shiling va ballar yutib oling\\!\n\n"
        f"Germaniyaga kelganlar va kelmoqchi bo'lganlar uchun foydali kanalimizda:\n"
        f"• 📚 O'qish va grant imkoniyatlari\n"
        f"• 💼 Ish topish yo'llari\n"
        f"• 🛂 Immigratsiya masalalari\n"
        f"• 🏡 Hayot haqida foydali ma'lumotlar\n"
        f"• 🗣️ Hammasi oddiy va tushunarli tilda\\!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 *Sizning referal havolangiz:*\n"
        f"`{referral_link}`\n\n"
        f"📋 *Qanday ishlaydi?*\n"
        f"1️⃣ Havolani do'stlaringizga yuboring\n"
        f"2️⃣ Ular @uzbek\\_europe kanaliga qo'shiladi\n"
        f"3️⃣ Botni ishga tushiradi\n"
        f"4️⃣ Ikkalovingiz ham ball olasiz\\!\n\n"
        f"💰 *Mukofotlar:*\n"
        f"  • Siz: *{POINTS_FOR_REFERRAL} ball* har bir taklif uchun\n"
        f"  • Do'stingiz: *{POINTS_FOR_JOINING} ball* qo'shilgani uchun\n\n"
        f"📊 *Sizning statistikangiz:*\n"
        f"👥 Taklif qilinganlar: *{referral_count}* kishi\n"
        f"⭐️ Jami toplangan: *{total_earned}* ball\n\n"
        f"🏆 Ko'proq do'st taklif qiling va liderlar jadvalida yuqoriga ko'tariling\\!"
    )
    
    await update.message.reply_text(message, parse_mode=constants.ParseMode.MARKDOWN_V2)

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscription check callback from inline button"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username = query.from_user.username
    first_name = query.from_user.first_name
    
    from utils.helpers import check_channel_membership, log_referral, has_user_joined_before
    
    logger.info(f"🔔 Subscription check callback from user {user_id}")
    
    # Check if user already joined/got points before
    if has_user_joined_before(user_id):
        logger.info(f"⚠️ User {user_id} already joined before, no points awarded")
        await query.edit_message_text(
            "👋 Xush kelibsiz qaytib\\!\n\n"
            "Siz allaqachon botga qo'shilgansiz va ballaringiz hisobga olingan\\.\n\n"
            "📊 /leaderboard \\- reytingni ko'rish\n"
            "🔗 /referral \\- do'stlarni taklif qilish",
            parse_mode=constants.ParseMode.MARKDOWN_V2
        )
        return
    
    # Check if user is now subscribed
    is_member = await check_channel_membership(user_id, context)
    
    if is_member:
        logger.info(f"✅ User {user_id} is now a member")
        
        # Get pending referral data
        pending_referral = context.user_data.get('pending_referral')
        
        if pending_referral:
            referrer_id = pending_referral['referrer_id']
            
            logger.info(f"💰 Awarding points: Referrer {referrer_id} gets {POINTS_FOR_REFERRAL}, User {user_id} gets {POINTS_FOR_JOINING}")
            
            # Log referral first (to mark user as joined)
            log_referral(referrer_id, user_id, username, first_name)
            
            # Award points - CRITICAL: Get the latest username/first_name from the callback
            log_activity(referrer_id, None, None, 'referral', POINTS_FOR_REFERRAL, post_id=user_id)
            log_activity(user_id, username, first_name, 'joining', POINTS_FOR_JOINING)
            
            logger.info(f"✅ Points awarded successfully")
            
            # Clear pending referral
            context.user_data.pop('pending_referral', None)
            
            success_text = (
                f"🎉 *Xush kelibsiz, {escape_markdown(first_name, version=2)}\\!*\n\n"
                f"✅ Siz *{POINTS_FOR_JOINING} ball* oldingiz\\!\n"
                f"🎁 Sizni taklif qilgan foydalanuvchi *{POINTS_FOR_REFERRAL} ball* oldi\\!\n\n"
                f"🇩🇪 *Yevropalik o'zbek* jamoasiga xush kelibsiz\\!\n\n"
                f"📌 *Nima qilishingiz mumkin:*\n"
                f"• Guruhdagi postlarga izoh qoldiring\n"
                f"• Postlarga reaction bering\n"
                f"• Do'stlaringizni taklif qiling\n"
                f"• Ballar yig'ing va sovg'alar yutib oling\\!\n\n"
                f"💡 *Foydali buyruqlar:*\n"
                f"/leaderboard \\- Reytingni ko'rish\n"
                f"/referral \\- Do'stlarni taklif qilish\n\n"
                f"🚀 Faol bo'ling va ko'proq ball to'plang\\!"
            )
            
            await query.edit_message_text(success_text, parse_mode=constants.ParseMode.MARKDOWN_V2)
            
            # Notify referrer
            try:
                referrer_name = f"@{username}" if username else first_name
                referrer_name_escaped = escape_markdown(referrer_name, version=2)
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎉 *Tabriklaymiz\\!*\n\n{referrer_name_escaped} sizning havolangiz orqali qo'shildi\\!\n\n✨ \\+{POINTS_FOR_REFERRAL} ball hisobingizga qo'shildi\\!",
                    parse_mode=constants.ParseMode.MARKDOWN_V2
                )
                logger.info(f"✅ Referrer {referrer_id} notified")
            except Exception as e:
                logger.error(f"❌ Failed to notify referrer: {e}")
        else:
            logger.warning(f"⚠️ No pending referral found for user {user_id}")
            await query.edit_message_text(
                "✅ Siz kanalga qo'shilgansiz\\! /start ni bosing\\.",
                parse_mode=constants.ParseMode.MARKDOWN_V2
            )
    else:
        logger.warning(f"❌ User {user_id} is still not a member")
        await query.answer("❌ Siz hali kanalga qo'shilmagansiz! Iltimos, avval kanalga qo'shiling.", show_alert=True)

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
            
            # Improved fallback logic - try to get actual name from Telegram if missing
            if not username and not first_name:
                try:
                    # Try to fetch user info from Telegram
                    chat_member = await context.bot.get_chat(user_id_display)
                    first_name = chat_member.first_name
                    username = chat_member.username
                    logger.info(f"🔄 Fetched missing user info for {user_id_display}: {first_name} (@{username})")
                    
                    # Update database with fetched info
                    try:
                        supabase.table('activity_log').update({
                            'username': username,
                            'first_name': first_name
                        }).eq('user_id', user_id_display).execute()
                        logger.info(f"✅ Updated database with user info for {user_id_display}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not update database: {e}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not fetch user info for {user_id_display}: {e}")
            
            # Build display name with better fallback
            if username:
                display_name_raw = f"@{username}"
            elif first_name:
                display_name_raw = first_name
            else:
                display_name_raw = f"Foydalanuvchi #{user_id_display}"
            
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
    from config import ADMIN_USER_ID
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
    from config import ADMIN_USER_ID
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
    from config import ADMIN_USER_ID
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