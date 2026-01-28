import logging
import random
from datetime import datetime, timezone, timedelta
from telegram import Update, constants, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from config import (
    supabase, 
    ADMIN_USER_ID_EU,
    ADMIN_USER_ID_EU_2,
    ADMIN_USER_ID,
    POINTS_FOR_COMMENT_EARLY,
    POINTS_FOR_COMMENT_LATE,
    POINTS_FOR_REACTION_EARLY,
    POINTS_FOR_REACTION_LATE,
    GROUP_CHAT_ID,
    POINTS_FOR_REFERRAL,
    POINTS_FOR_JOINING,
    CHANNEL_USERNAME,
    CHANNEL_USERNAME_2,
    FIRST_COMMENT_POINTS,
    SECOND_COMMENT_POINTS,
    THIRD_COMMENT_POINTS,
    OTHER_COMMENT_POINTS,
    POINTS_FOR_BOOSTING,
    MAX_REFERRALS_FOR_POINTS,
    POINTS_FOR_QUIZ,
    CHANNEL_ID_MUSLIMBEK,
    CHANNEL_ID_UZBEK_EUROPE
)
from utils.helpers import get_leaderboard, log_activity, generate_referral_link, save_user_to_db, is_user_registered

logger = logging.getLogger(__name__)

ADMIN_USER_ID = ADMIN_USER_ID_EU



def get_main_menu_keyboard():
    """Generate main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("🎯 Ishtirok etish", callback_data="menu_participate")],
        [InlineKeyboardButton("👤 Profilim", callback_data="menu_profile")],
        [InlineKeyboardButton("🏆 Liderlar", callback_data="menu_leaderboard")],
        [InlineKeyboardButton("📊 Batafsil ma'lumot", callback_data="show_webapp")],
        [InlineKeyboardButton("📋 Qoidalar", callback_data="menu_rules")], 
    ]
    return InlineKeyboardMarkup(keyboard)


def get_leaderboard_keyboard():
    """Generate leaderboard menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("📊 Batafsil ma'lumot", callback_data="show_webapp")],
        [InlineKeyboardButton("👤 Profilim", callback_data="menu_profile")],
        [InlineKeyboardButton("◀️ Orqaga", callback_data="menu_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_participate_keyboard(user_id: int, bot_username: str):
    """Generate participate menu keyboard"""
    referral_link = generate_referral_link(user_id, bot_username)
    share_text = f"🎉 Bu mening havolam. Qo'shiling va 400,000 so'm yutib oling!\n\n🇩🇪 Simple Quizzer tanlovida ishtirok eting!\n\n Ro'yxatdan o'tib menga 5 ball, o'zingizga esa 3 ball ishlab oling👇\n {referral_link}"
    
    # URL encode the share text
    import urllib.parse
    encoded_text = urllib.parse.quote(share_text)
    share_url = f"https://t.me/share/url?url={urllib.parse.quote(referral_link)}&text={encoded_text}"
    
    keyboard = [
        [InlineKeyboardButton("📤 Ulashish", url=share_url)],
        [InlineKeyboardButton("📱 Instagramda ball olish", callback_data="instagram_menu")],  
        [InlineKeyboardButton("🚀 Boost qilish", callback_data="boost_channel")],
        [InlineKeyboardButton("👤 Mening profilim", callback_data="menu_profile")],
        [InlineKeyboardButton("🏆 Liderlar", callback_data="menu_leaderboard")],
        [InlineKeyboardButton("◀️ Orqaga", callback_data="menu_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_profile_keyboard(user_id: int, bot_username: str):
    """Generate profile menu keyboard with referral info button"""
    keyboard = [
        [InlineKeyboardButton("📤 Referal ma'lumot", callback_data="show_referral_info")],
        [InlineKeyboardButton("🚀 Boost qilish", callback_data="boost_channel")],
        [InlineKeyboardButton("📱 Instagramda ball olish", callback_data="instagram_menu")],  
        [InlineKeyboardButton("🏆 Liderlar", callback_data="menu_leaderboard")],
        [InlineKeyboardButton("◀️ Orqaga", callback_data="menu_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - welcome message and referral tracking"""
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    first_name = update.message.from_user.first_name
    last_name = update.message.from_user.last_name

    referral_payload = context.args[0] if context.args else None
    
    logger.info(f"🚀 /start command received from user {user_id}")
    if referral_payload:
        logger.info(f"🔗 Referral payload: {referral_payload}")
    
    # Check channel membership for ALL users
    from utils.helpers import check_channel_membership
    is_member = await check_channel_membership(user_id, context)
    
    if not is_member:
        logger.info(f"❌ User {user_id} is not subscribed to channel")
        
        # Store user data and referral info for later
        context.user_data['pending_user'] = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'referral_payload': referral_payload
        }
        
        # Create inline keyboard with channel links and check button
        keyboard = [
            [InlineKeyboardButton("📢 Uzbek Europe", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton("📢 Muslimbek", url=f"https://t.me/{CHANNEL_USERNAME_2}")],
            [InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_subscription_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        join_message = (
            f"🎉 *KONKURS BOSHLANDI\\!* 🎉\n\n"
            f"🏆 *Qatnashish uchun avval kanallarimizga obuna bo‘ling\\!* \n"
            f"💸 *Bu orqali siz konkursga qo'shilasiz\\!* \n\n"
            f"💰 Bu safar *umumiy yutuq miqdori — 1 000 000 SO‘M\\!* \n"
            f"👇 Quyidagi tugmalarni bosing, kanallarga obuna bo‘ling\n"
            f"va so‘ng obunani tekshiring\\!\n\n"
            f"📌 *To‘liq ma’lumot:* https://t\\.me/simplelearnuz/183\n"
        )
        
        # Send main subscription message
        await update.message.reply_text(
            join_message, 
            parse_mode=constants.ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup
        )
        
        await send_bot_promo(update, context, "both")


        # If coming from referral, send additional bonus message
        if referral_payload:
            bonus_message = (
                f"🎁 *BONUS OLISH UCHUN\\!*\n\n"
                f"✅ Yuqoridagi *ikkala kanalga* obuna bo'ling\n"
                f"✅ *'Obunani tekshirish'* tugmasini bosing\n"
                f"✅ Bonus ballaringiz avtomatik hisobingizga qo'shiladi\\!\n\n"
                f"⚠️ *Muhim:* Bonus faqat *ikkala kanalga* qo'shilganingizdan keyin beriladi\\!"
            )
            
            await update.message.reply_text(
                bonus_message,
                parse_mode=constants.ParseMode.MARKDOWN_V2
            )
        
        return
    
    # User is subscribed, continue with normal flow
    logger.info(f"✅ User {user_id} is subscribed to channel")
    bot_username = (await context.bot.get_me()).username
    
    if referral_payload:
        from utils.helpers import get_referrer_from_payload
        
        referrer_id = get_referrer_from_payload(referral_payload)
        
        if referrer_id and referrer_id != user_id:
            # OPTIMIZATION: Single batch check for registration AND referral status
            try:
                user_check = supabase.table('uzbek_europe_users').select('id').eq('user_id', user_id).execute()
                referral_check = supabase.table('referrals').select('id').eq('referred_user_id', user_id).execute()
                
                is_registered = len(user_check.data) > 0
                already_referred = len(referral_check.data) > 0
                
                if is_registered or already_referred:
                    logger.info(f"⚠️ User {user_id} already registered or referred")
                    save_user_to_db(user_id, username, first_name, last_name)
                    await update.message.reply_text(
                        "👋 Xush kelibsiz\\!\n\n"
                        "Siz allaqachon botga qo'shilgansiz va ballaringiz hisobga olingan\\.\n\n"
                        "Quyidagi menyudan foydalaning:",
                        parse_mode=constants.ParseMode.MARKDOWN_V2,
                        reply_markup=get_main_menu_keyboard()
                    )
                    return
            except Exception as e:
                logger.error(f"❌ Error checking user status: {e}")
                await update.message.reply_text(
                    "❌ Xatolik yuz berdi\\. Qaytadan urinib ko'ring\\.",
                    parse_mode=constants.ParseMode.MARKDOWN_V2
                )
                return
            
            # Save user to DB first
            save_user_to_db(user_id, username, first_name, last_name)
            
            # OPTIMIZATION: Fetch referrer info and count in parallel
            try:
                referrer_info_result = supabase.table('uzbek_europe_users').select('username, first_name').eq('user_id', referrer_id).limit(1).execute()
                referral_count_result = supabase.table('referrals').select('id').eq('referrer_id', referrer_id).execute()
                
                referrer_username = None
                referrer_first_name = None
                if referrer_info_result.data:
                    referrer_username = referrer_info_result.data[0].get('username')
                    referrer_first_name = referrer_info_result.data[0].get('first_name')
                    logger.info(f"📋 Retrieved referrer info: {referrer_username}, {referrer_first_name}")
                
                referrer_count = len(referral_count_result.data)
                
            except Exception as e:
                logger.error(f"❌ Error fetching referrer data: {e}")
                referrer_username = None
                referrer_first_name = None
                referrer_count = 0
            
            # OPTIMIZATION: Batch insert all activity logs and referral
            timestamp = datetime.now(timezone.utc).isoformat()
            activities_to_log = []
            
            # Check if referrer gets points
            if referrer_count < MAX_REFERRALS_FOR_POINTS:
                # Referrer gets points
                activities_to_log.append({
                    'user_id': referrer_id,
                    'username': referrer_username,
                    'first_name': referrer_first_name,
                    'activity_type': 'referral',
                    'points': POINTS_FOR_REFERRAL,
                    'timestamp': timestamp,
                    'post_id': user_id,
                    'post_timestamp': None,
                    'channel_id': None
                })
            
            # User always gets joining points
            activities_to_log.append({
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'activity_type': 'joining',
                'points': POINTS_FOR_JOINING,
                'timestamp': timestamp,
                'post_id': None,
                'post_timestamp': None,
                'channel_id': None
            })
            
            # Referral record
            referral_data = {
                'referrer_id': referrer_id,
                'referrer_username': referrer_username,
                'referrer_first_name': referrer_first_name,
                'referred_user_id': user_id,
                'referred_username': username,
                'referred_first_name': first_name,
                'timestamp': timestamp
            }
            
            try:
                # BATCH INSERT: All activities + referral in 2 calls instead of 3-4
                supabase.table('activity_log').insert(activities_to_log).execute()
                supabase.table('referrals').insert(referral_data).execute()
                logger.info(f"✅ Batch logged {len(activities_to_log)} activities and referral")
            except Exception as e:
                logger.error(f"❌ Error batch logging: {e}")
            
            # Build response message
            referral_link = generate_referral_link(user_id, bot_username)
            
            if referrer_count >= MAX_REFERRALS_FOR_POINTS:
                # User still gets points, but referrer doesn't
                welcome_text = (
                    f"🎉 *Xush kelibsiz, {escape_markdown(first_name, version=2)}\\!*\n\n"
                    f"✅ Siz *{POINTS_FOR_JOINING} ball* oldingiz\\!\n\n"
                    f"🏆 *400 000 so'm yuting\\!*\n"
                    f"Siz ham tanlovimizda ishtirok eting\\!\n\n"
                    f"📤 *Do'stlaringizni taklif qiling:*\n"
                    f"Har bir do'stingiz uchun *{POINTS_FOR_REFERRAL} ball* oling\\!\n\n"
                    f"🔗 *Sizning referal havolangiz:*\n"
                    f"`{escape_markdown(referral_link, version=2)}`\n\n"
                    f"Quyidagi menyudan foydalaning:"
                )
            else:
                # Both get points
                welcome_text = (
                    f"🎉 *Xush kelibsiz, {escape_markdown(first_name, version=2)}\\!*\n\n"
                    f"✅ Siz *{POINTS_FOR_JOINING} ball* oldingiz\\!\n"
                    f"🎁 Sizni taklif qilgan foydalanuvchi *{POINTS_FOR_REFERRAL} ball* oldi\\!\n\n"
                    f"🏆 *400 000 so'm yutib oling\\!*\n"
                    f"Siz ham tanlovimizda ishtirok eting\\!\n\n"
                    f"📤 *Do'stlaringizni taklif qiling:*\n"
                    f"Har bir do'stingiz uchun *{POINTS_FOR_REFERRAL} ball* olasiz\\!\n\n"
                    f"🔗 *Sizning referal havolangiz:*\n"
                    f"`{escape_markdown(referral_link, version=2)}`\n\n"
                    f"Quyidagi menyulardan foydalaning:"
                )
                
                # Notify referrer (async, don't wait)
                try:
                    referrer_name = f"@{username}" if username else first_name
                    referrer_name_escaped = escape_markdown(referrer_name, version=2)
                    # Create task to send message asynchronously without blocking
                    context.application.create_task(
                        context.bot.send_message(
                            chat_id=referrer_id,
                            text=f"🎉 *Tabriklaymiz\\!*\n\n{referrer_name_escaped} sizning havolangiz orqali qo'shildi\\!\n\n✨ \\+{POINTS_FOR_REFERRAL} ball hisobingizga qo'shildi\\!",
                            parse_mode=constants.ParseMode.MARKDOWN_V2
                        )
                    )
                    logger.info(f"✅ Referrer {referrer_id} notification queued")
                except Exception as e:
                    logger.error(f"❌ Failed to queue referrer notification: {e}")
            
            import urllib.parse
            share_text = f"🎉 Bu mening havolam. Qo'shiling va 400,000 so'm yutib oling!\n\n🇩🇪 Simple Quizzer tanlovida ishtirok eting!\n\n Ro'yxatdan o'tib menga 5 ball, o'zingizga esa 3 ball ishlab oling👇\n {referral_link}"
            encoded_text = urllib.parse.quote(share_text)
            share_url = f"https://t.me/share/url?url={urllib.parse.quote(referral_link)}&text={encoded_text}"

            keyboard = [
                [InlineKeyboardButton("📤 Ulashish", url=share_url)],
                [InlineKeyboardButton("🎯 Bosh menyu", callback_data="menu_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                welcome_text, 
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

    save_user_to_db(user_id, username, first_name, last_name)
    
    welcome_msg = (
        f"👋 Salom, {escape_markdown(first_name, version=2)}\\!\n\n"
        f"🇺🇿 *SimpleQuizzer Tanlovi\\!* 🔥\n\n"
        f"*1 MILLION SO'MLIK* tanlov endilikda @Uzbek\\_Europe va @Muslimbek\\_01 tomonidan olib boriladi\\.\n\n"
        f"🎯 *Qanday ishtirok etish mumkin:*\n"
        f"• @SimpleQuizzer\\_bot orqali quizlar yarating\n"
        f"• Quizlarni yeching va ball to'plang\n"
        f"• Kanallarimizda aktiv bo'ling \\(komment, reaksiya, ulashish\\)\n"
        f"• Do'stlaringizni taklif qiling va ballar ishlang\n\n"
        f"Quyidagi menyudan foydalaning:"
    )
    



    try:
        await update.message.reply_text(
            welcome_msg, 
            parse_mode=constants.ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )

        await send_bot_promo(update, context, "both")

    except Exception as e:
        logger.error(f"❌ Error sending start message: {e}")
        await update.message.reply_text(welcome_msg.replace('\\', '').replace('*', ''))


async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all menu button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username = query.from_user.username
    first_name = query.from_user.first_name
    bot_username = (await context.bot.get_me()).username
    
    callback_data = query.data
    
    try:
        if callback_data == "menu_main":
            # Show main menu
            # Regular welcome message for subscribed users without referral
            welcome_msg = (
                f"👋 Salom, {escape_markdown(first_name, version=2)}\\!\n\n"
                f"🇺🇿 *SimpleQuizzer Tanlovi\\!* 🔥\n\n"
                f"Endilikda @Uzbek\\_Europe va @Muslimbek\\_01 tomonidan olib boriladi\\.\n\n"
                f"🎯 *Qanday ishtirok etish:*\n"
                f"• @SimpleQuizzer\\_bot orqali quizlar yarating\n"
                f"• Kanallarimizda aktiv bo'ling \\(komment, reaksiya, ulashish\\)\n"
                f"• Quizlarni yeching va ball to'plang\n"
                f"• Do'stlaringizni taklif qiling\n\n"
                f"Quyidagi menyudan foydalaning:"
            )
            await query.edit_message_text(
                welcome_msg,
                parse_mode=constants.ParseMode.MARKDOWN_V2,
                reply_markup=get_main_menu_keyboard()
            )
        
        elif callback_data == "menu_participate":
        # Show participate information
            referral_link = generate_referral_link(user_id, bot_username)
            text = (
                f"🎯 *TANLOVDA ISHTIROK ETING\\!*\n\n"
                f"🇩🇪 *Yevropalik o'zbek* jamoasiga qo'shiling va sovg'alar yutib oling\\!\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 *Ballar qanday ishlab topiladi:*\n\n"
                f"📝 *Kommentlar:*\n"
                f"  • 1\\-izoh: {FIRST_COMMENT_POINTS} ball\n"
                f"  • 2\\-izoh: {SECOND_COMMENT_POINTS} ball\n"
                f"  • 3\\-izoh: {THIRD_COMMENT_POINTS} ball\n"
                f"  • Boshqa kommentlar: {OTHER_COMMENT_POINTS} ball\n\n"
                f"❤️ *Reaksiyalar:*\n"
                f"  • Har bir reaksiya: {POINTS_FOR_REACTION_EARLY} ball \\(birinchi 48 soat\\)\n"
                f"  • Keyinroq: {POINTS_FOR_REACTION_LATE} ball\n\n"
                f"🎯 *Quiz tuzish:*\n"
                f"  • Har bir quiz: {POINTS_FOR_QUIZ} ball\n"
                f"  • @SimpleQuizzer\\_bot orqali quiz yarating\\!\n\n"
                f"👥 *Referal:*\n"
                f"  • Har bir do'stingiz uchun siz: {POINTS_FOR_REFERRAL} ball\n"
                f"  • Do'stingiz qo'shilgani uchun unga: {POINTS_FOR_JOINING} ball\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🔗 *Sizning referal havolangiz:*\n"
                f"`{referral_link}`\n\n"
                f"🏆 Ko'proq ball to'plang va liderlar jadvalida yuqoriga ko'tariling\\!"
            )
            await query.edit_message_text(
                text,
                parse_mode=constants.ParseMode.MARKDOWN_V2,
                reply_markup=get_participate_keyboard(user_id, bot_username)  
            )


        elif callback_data == "menu_profile":
            from utils.helpers import get_user_stats
            stats = get_user_stats(user_id)
            
            if stats:
                display_name = f"@{stats['username']}" if stats['username'] else (stats['first_name'] or "Foydalanuvchi")
                display_name_escaped = escape_markdown(display_name, version=2)
                
                uzbek_europe = stats['uzbek_europe']
                muslimbek = stats['muslimbek']
                
                uzbek_channel = escape_markdown("@uzbek_europe", version=2)
                muslimbek_channel = escape_markdown("@muslimbek_01", version=2)

                text = (
                    f"📊 *Sizning ko'rsatkichlaringiz:*\n\n"
                    f"👤 Nickname: {display_name_escaped}\n"
                    f"🎯 Jami ballar: *{stats['total_points']}*\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🇩🇪 *Uzbek Europe \\({uzbek_channel}\\) kanalida:*\n"
                    f"📝 Komment ballari: {uzbek_europe['comment_points']}\n"
                    f"❤️ Reaksiya ballari: {uzbek_europe['reaction_points']}\n"
                    f"📱 Instagram ballari: {uzbek_europe['instagram_points']}\n"  # Added
                    f"🚀 Boost ballari: {uzbek_europe['boost_points']}\n\n"
                    f"📚 *Muslimbek \\({muslimbek_channel}\\) kanalida:*\n"
                    f"📝 Komment ballari: {muslimbek['comment_points']}\n"
                    f"❤️ Reaksiya ballari: {muslimbek['reaction_points']}\n"
                    f"📱 Instagram ballari: {muslimbek['instagram_points']}\n"  # Added
                    f"🚀 Boost ballari: {muslimbek['boost_points']}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🎯 Quiz ballari: {stats['quiz_points']}\n"
                    f"👥 Referal ballari: {stats['referral_points']}\n"
                    f"🔗 Referal takliflar: {stats['referral_count']} ta\n"
                    f"🏆 O'rin: \\#{stats['position']}\n\n"
                )
                
                if stats['position'] > 50:
                    text += f"📍 TOP 15 ga kirishga harakat qiling\\!"
                elif stats['position'] > 15:
                    text += f"📍 TOP 15 ga yaqinlashdingiz\\!"
                else:
                    text += f"🌟 Ajoyib natija\\! Davom eting\\!"
            else:
                text = "❌ Statistika yuklanmadi\\. Qaytadan urinib ko'ring\\."
            
            await query.edit_message_text(
                text,
                parse_mode=constants.ParseMode.MARKDOWN_V2,
                reply_markup=get_profile_keyboard(user_id, bot_username)
            )

        
        if callback_data == "menu_leaderboard":
            # Show leaderboard - ONLY LAST 30 DAYS
            from datetime import datetime, timedelta, timezone
            
            top_users_30 = get_leaderboard(days=30, limit=16)
            top_users_30 = [u for u in top_users_30 if u.get('user_id') not in [ADMIN_USER_ID, ADMIN_USER_ID_EU, ADMIN_USER_ID_EU_2]][:15]
            
            # Calculate date range
            now = datetime.now(timezone.utc)
            date_30_start = (now - timedelta(days=30)).strftime('%d\\.%m')
            date_now = now.strftime('%d\\.%m')
            
            if not top_users_30:
                text = "📊 Hali hech qanday faollik qayd etilmagan\\!"
            else:
                text = f"🏆 *LIDERLAR JADVALI*\n\n"
                
                # Last 30 days - TOP 15
                text += f"📅 *Oxirgi 30 kun* \\({date_30_start}\\-{date_now}\\)\n"
                for i, user_data in enumerate(top_users_30):
                    first_name_u = user_data.get('first_name', 'User')
                    score = user_data.get('total_score')
                    display_name_escaped = escape_markdown(first_name_u, version=2)
                    
                    if i == 0:
                        rank = "🥇"
                    elif i == 1:
                        rank = "🥈"
                    elif i == 2:
                        rank = "🥉"
                    else:
                        rank = f"{i + 1}\\."
                    
                    text += f"{rank} {display_name_escaped} \\- {score} ball\n"
            
            await query.edit_message_text(
                text,
                parse_mode=constants.ParseMode.MARKDOWN_V2,
                reply_markup=get_leaderboard_keyboard()
            )

        
        elif callback_data == "boost_channel":
            await query.answer(
                f"Kanalni boost qilish uchun @{CHANNEL_USERNAME} kanaliga o'ting va Boost tugmasini bosing!",
                show_alert=True
            )
    
        elif callback_data == "show_referral_info":
            # Show referral information
            from config import MAX_REFERRALS_FOR_POINTS
            
            referral_link = generate_referral_link(user_id, bot_username)
            
            # Get referral count
            try:
                result = supabase.table('referrals').select('id').eq('referrer_id', user_id).execute()
                referral_count = len(result.data)
            except:
                referral_count = 0
            
            total_earned = min(referral_count, MAX_REFERRALS_FOR_POINTS) * POINTS_FOR_REFERRAL
            remaining = max(0, MAX_REFERRALS_FOR_POINTS - referral_count)
            
            text = (
                f"🎁 *DO'STLARINGIZNI TAKLIF QILING\\!*\n\n"
                f"🔗 *Sizning referal havolangiz:*\n"
                f"`{escape_markdown(referral_link, version=2)}`\n\n"
                f"⚠️ *MUHIM:* Do'stingiz kanalga qo'shilgandan so'ng bonus beriladi\\!\n\n"
                f"📊 *Qanday ishlaydi:*\n"
                f"1️⃣ Do'stingiz havolangizni bosadi\n"
                f"2️⃣ Botga start beradi\n"
                f"3️⃣ @{escape_markdown(CHANNEL_USERNAME, version=2)} va @{escape_markdown(CHANNEL_USERNAME_2, version=2)} kanaliga qo'shiladi\n"
                f"4️⃣ Siz *{POINTS_FOR_REFERRAL} ball* olasiz\\!\n"
                f"5️⃣ Do'stingiz *{POINTS_FOR_JOINING} ball* oladi\\!\n\n"
                f"📈 *Sizning statistikangiz:*\n"
                f"👥 Taklif qilinganlar: *{referral_count}* kishi\n"
                f"⭐️ Jami toplangan: *{total_earned}* ball\n"
            )
            
            if referral_count >= MAX_REFERRALS_FOR_POINTS:
                text += f"\n⚠️ *Maksimal chegara:* Siz {MAX_REFERRALS_FOR_POINTS} ta referal uchun ball oldingiz\\!\n"
            else:
                text += f"\n💡 Yana *{remaining}* ta referal uchun ball olishingiz mumkin\\!\n"
            
            text += f"\n🏆 Ko'proq do'st taklif qiling va liderlar jadvalida yuqoriga ko'tariling\\!"
            
            share_text = f"🎉 Bu mening havolam. Qo'shiling va 400,000 so'm yutib oling!\n\n🇩🇪 Simple Quizzer tanlovida ishtirok eting!\n\n Ro'yxatdan o'tib menga 5 ball, o'zingizga esa 3 ball ishlab oling👇\n {referral_link}"
            
            keyboard = [
                [InlineKeyboardButton("📤 Ulashish", switch_inline_query=share_text)],
                [InlineKeyboardButton("◀️ Orqaga", callback_data="menu_profile")]
            ]
            
            await query.edit_message_text(
                text,
                parse_mode=constants.ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif callback_data == "show_webapp":
            # Show webapp button with informative message
            from handlers.webapp_handler import WEBAPP_URL
            from telegram import WebAppInfo
            
            keyboard = [
                [InlineKeyboardButton(
                    "📊 Ochish", 
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )],
                [InlineKeyboardButton("◀️ Orqaga", callback_data="menu_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message_text = (
                f"📊 *Batafsil Liderlar Jadvali*\n\n"
                f"Bu yerda siz quyidagilarni ko'rishingiz mumkin:\n\n"
                f"✅ Barcha ishtirokchilar reytingi\n"
                f"✅ Har bir kanal bo'yicha ball taqsimoti\n"
                f"✅ Izoh, reaksiya va boost ballari\n"
                f"✅ Quiz va referal ballari\n"
                f"✅ Sizning aniq pozitsiyangiz\n\n"
                f"💡 *Qulayliklar:*\n"
                f"• 🔄 Real vaqtda yangilanadi\n"
                f"• 🎯 Shaxsiy statistika\n\n"
                f"👇 Ochish uchun tugmani bosing:"
            )
            
            await query.edit_message_text(
                message_text,
                parse_mode=constants.ParseMode.MARKDOWN_V2,
                reply_markup=reply_markup
            )

            await send_bot_promo(update, context, "slides")


        
        elif callback_data == "menu_rules":
            # Show rules
            rules_text = (
                f"📋 *TANLOV QOIDALARI*\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 *Kommentlar*\n"
                f"Endilikda siz 2 ta kanal \\(@Muslimbek\\_01 va @Uzbek\\_europe\\) orqali:\n"
                f"➡️ har bir kanaldan 25 balldan\n"
                f"✅ jami 50 ball to'plashingiz mumkin\n\n"
                f"👍 *Reaksiyalar*\n"
                f"➡️ 2 ta kanal: 10 \\+ 10\n"
                f"✅ jami 20 ball\n\n"
                f"📱 *Instagram obunalar:*\n"
                f"➡️ Har bir sahifa uchun: 25 ball\n"
                f"➡️ 2 ta sahifa: @\\_muslimbek\\_01 va @uzbek\\_german\n"
                f"✅ jami 50 ball\n\n"
                f"👥 *Referrallar uchun:*\n"
                f"🔒 Maksimal limit — 200 ball\n\n"
                f"💣 *Boost uchun:*\n"
                f"• Har bir boost uchun: 20 balldan beriladi va bu yerda ham limit yo'q\\!\n\n"
                f"🧠 *Eng zo'r imkoniyat\\!*\n"
                f"Qolgan barcha ballarni cheklovsiz tarzda 👉 @SimpleQuizzer\\_bot orqali Quiz tuzib yig'ishingiz mumkin\\! "
                f"Har bir quiz uchun \\+2 ball dan beriladi va bu yerda hech qanday cheklov yo'q\\!\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🔥 *Barchaga Omad\\!*"
            )
            
            keyboard = [
                [InlineKeyboardButton("◀️ Orqaga", callback_data="menu_main")]
            ]
            
            await query.edit_message_text(
                rules_text,
                parse_mode=constants.ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            await send_bot_promo(update, context, "quizzer")




    except Exception as e:
        logger.error(f"Error handling menu callback: {e}")
        await query.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.", show_alert=True)


async def handle_boost_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle boost channel callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    try:
        # Check boost status for both channels
        boost_status = await check_boost_status(user_id, context)
        
        status_europe = (
            "Boost qilingan ✅"
            if boost_status['uzbek_europe']
            else f"Boost qilinmagan \\({POINTS_FOR_BOOSTING} ball\\)"
        )
        status_muslimbek = (
            "Boost qilingan ✅"
            if boost_status['muslimbek_01']
            else f"Boost qilinmagan \\({POINTS_FOR_BOOSTING} ball\\)"
        )

        text = (
            f"🚀 *BOOST QILISH*\n\n"
            f"Kanallarni boost qilib qo'shimcha ball yig'ing\\!\n\n"
            f"📊 *Har bir kanal uchun:*\n"
            f"⭐️ 1 boost \\= {POINTS_FOR_BOOSTING} ball\n\n"
            f"💡 *Jami:*\n"
            f"🎁 2 ta kanal × {POINTS_FOR_BOOSTING} ball \\= {POINTS_FOR_BOOSTING * 2} ball\n\n"
            f"📋 *Sizning statusingiz:*\n\n"
            f"{'🟢' if boost_status['uzbek_europe'] else '⚪️'} *Yevropalik o'zbek*\n"
            f"   {status_europe}\n\n"
            f"{'🟢' if boost_status['muslimbek_01'] else '⚪️'} *Muslimbek Abdurakhimov*\n"
            f"   {status_muslimbek}\n\n"
            f"💡 Kanalga o'tib, Boost tugmasini bosing\\!"
        )
        
        keyboard = [
            [InlineKeyboardButton("🚀 Uzbek Europe - Boost", url="https://t.me/boost/Uzbek_Europe")],
            [InlineKeyboardButton("🚀 Muslimbek - Boost", url="https://t.me/boost/Muslimbek_01")],
            [InlineKeyboardButton("✅ Boost Tekshirish", callback_data="check_boost_status")],
            [InlineKeyboardButton("◀️ Orqaga", callback_data="menu_main")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=constants.ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error handling boost callback: {e}")
        await query.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.", show_alert=True)

async def check_boost_status(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Check if user has boosted the channels"""
    from utils.helpers import check_user_boost_status
    
    try:
        # Check actual boost status via Telegram API
        uzbek_europe_boosted = await check_user_boost_status(user_id, CHANNEL_USERNAME, context)
        muslimbek_boosted = await check_user_boost_status(user_id, CHANNEL_USERNAME_2, context)
        
        return {
            'uzbek_europe': uzbek_europe_boosted,
            'muslimbek_01': muslimbek_boosted
        }
    except Exception as e:
        logger.error(f"Error checking boost status: {e}")
        return {'uzbek_europe': False, 'muslimbek_01': False}

async def check_boost_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle boost status check callback - award points if boosted"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username = query.from_user.username
    first_name = query.from_user.first_name
    
    try:
        from utils.helpers import has_user_boosted_channel
        
        # Check actual boost status
        boost_status = await check_boost_status(user_id, context)
        
        points_awarded = 0
        messages = []
        
        # Check Uzbek Europe
        if boost_status['uzbek_europe']:
            if not has_user_boosted_channel(user_id, CHANNEL_ID_UZBEK_EUROPE):
                log_activity(user_id, username, first_name, 'boost', POINTS_FOR_BOOSTING, post_id=None, channel_id=CHANNEL_ID_UZBEK_EUROPE)
                points_awarded += POINTS_FOR_BOOSTING
                messages.append(f"🎉 Uzbek Europe uchun +{POINTS_FOR_BOOSTING} ball!")
                logger.info(f"✅ Awarded {POINTS_FOR_BOOSTING} points to user {user_id} for boosting Uzbek Europe")
            else:
                messages.append("✅ Uzbek Europe uchun ball allaqachon berilgan")
        
        # Check Muslimbek
        if boost_status['muslimbek_01']:
            if not has_user_boosted_channel(user_id, CHANNEL_ID_MUSLIMBEK):
                log_activity(user_id, username, first_name, 'boost', POINTS_FOR_BOOSTING, post_id=None, channel_id=CHANNEL_ID_MUSLIMBEK)
                points_awarded += POINTS_FOR_BOOSTING
                messages.append(f"🎉 Muslimbek uchun +{POINTS_FOR_BOOSTING} ball!")
                logger.info(f"✅ Awarded {POINTS_FOR_BOOSTING} points to user {user_id} for boosting Muslimbek")
            else:
                messages.append("✅ Muslimbek uchun ball allaqachon berilgan")
        
        # Send separate notification message
        if points_awarded > 0:
            notification = f"🎉 *Tabriklaymiz\\!*\n\n" + "\n".join([escape_markdown(msg, version=2) for msg in messages]) + f"\n\n💰 Jami: \\+{points_awarded} ball"
            await context.bot.send_message(
                chat_id=user_id,
                text=notification,
                parse_mode=constants.ParseMode.MARKDOWN_V2
            )
        elif not boost_status['uzbek_europe'] and not boost_status['muslimbek_01']:
            notification = "❌ Siz hali hech qanday kanalni boost qilmagansiz\\!\n\nIltimos, kanallarni boost qiling va qayta tekshiring\\."
            await context.bot.send_message(
                chat_id=user_id,
                text=notification,
                parse_mode=constants.ParseMode.MARKDOWN_V2
            )
        else:
            notification = "✅ Barcha boostlar uchun ball allaqachon berilgan\\!"
            await context.bot.send_message(
                chat_id=user_id,
                text=notification,
                parse_mode=constants.ParseMode.MARKDOWN_V2
            )
        
    except Exception as e:
        logger.error(f"Error checking boost status: {e}")
        await query.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.", show_alert=True)


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's referral link and stats"""
    user_id = update.message.from_user.id
    bot_username = (await context.bot.get_me()).username
    
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
        f"🔗 *Sizning referal havolangiz:*\n"
        f"`{referral_link}`\n\n"
        f"📊 *Sizning statistikangiz:*\n"
        f"👥 Taklif qilinganlar: *{referral_count}* kishi\n"
        f"⭐️ Jami toplangan: *{total_earned}* ball\n\n"
        f"🏆 Ko'proq do'st taklif qiling va liderlar jadvalida yuqoriga ko'tariling\\!"
    )
    
    await update.message.reply_text(message, parse_mode=constants.ParseMode.MARKDOWN_V2)


async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscription check for regular /start users"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    from utils.helpers import check_channel_membership, get_referrer_from_payload
    
    logger.info(f"🔔 Main subscription check callback from user {user_id}")
    
    # Get pending user data
    pending_user = context.user_data.get('pending_user')
    if not pending_user:
        logger.warning(f"⚠️ No pending user data found for {user_id}")
        await query.edit_message_text(
            "❌ Xatolik yuz berdi\\. Iltimos, /start ni qayta bosing\\.",
            parse_mode=constants.ParseMode.MARKDOWN_V2
        )
        return
    
    username = pending_user['username']
    first_name = pending_user['first_name']
    last_name = pending_user['last_name']
    referral_payload = pending_user.get('referral_payload')
    
    # Check if user is now subscribed
    is_member = await check_channel_membership(user_id, context)
    
    if not is_member:
        logger.warning(f"❌ User {user_id} is still not a member")
        await query.answer("❌ Siz hali kanallarimizga qo'shilmagansiz! Iltimos, avval kanallarimizga qo'shiling.", show_alert=True)
        return
    
    logger.info(f"✅ User {user_id} is now a member - proceeding with referral logic")
    
    # Get bot username
    bot_username = (await context.bot.get_me()).username
    
    # Handle referral if exists - ONLY AFTER MEMBERSHIP IS CONFIRMED
    if referral_payload:
        referrer_id = get_referrer_from_payload(referral_payload)
        
        if referrer_id and referrer_id != user_id:
            # OPTIMIZATION: Batch check for registration AND referral status
            try:
                user_check = supabase.table('uzbek_europe_users').select('id').eq('user_id', user_id).execute()
                referral_check = supabase.table('referrals').select('id').eq('referred_user_id', user_id).execute()
                
                is_registered = len(user_check.data) > 0
                already_referred = len(referral_check.data) > 0
                
                if is_registered or already_referred:
                    logger.info(f"⚠️ User {user_id} already registered or referred")
                    save_user_to_db(user_id, username, first_name, last_name)
                    await query.edit_message_text(
                        "👋 Xush kelibsiz\\!\n\n"
                        "Siz allaqachon botga qo'shilgansiz va ballaringiz hisobga olingan\\.\n\n"
                        "Quyidagi menyudan foydalaning:",
                        parse_mode=constants.ParseMode.MARKDOWN_V2,
                        reply_markup=get_main_menu_keyboard()
                    )
                    context.user_data.pop('pending_user', None)
                    return
            except Exception as e:
                logger.error(f"❌ Error checking user status: {e}")
                await query.edit_message_text(
                    "❌ Xatolik yuz berdi\\. Qaytadan urinib ko'ring\\.",
                    parse_mode=constants.ParseMode.MARKDOWN_V2
                )
                return
            
            # Save user to DB
            save_user_to_db(user_id, username, first_name, last_name)
            
            # OPTIMIZATION: Fetch referrer info and count in parallel
            try:
                referrer_info_result = supabase.table('uzbek_europe_users').select('username, first_name').eq('user_id', referrer_id).limit(1).execute()
                referral_count_result = supabase.table('referrals').select('id').eq('referrer_id', referrer_id).execute()
                
                referrer_username = None
                referrer_first_name = None
                if referrer_info_result.data:
                    referrer_username = referrer_info_result.data[0].get('username')
                    referrer_first_name = referrer_info_result.data[0].get('first_name')
                    logger.info(f"📋 Retrieved referrer info: {referrer_username}, {referrer_first_name}")
                
                referrer_count = len(referral_count_result.data)
                
            except Exception as e:
                logger.error(f"❌ Error fetching referrer data: {e}")
                referrer_username = None
                referrer_first_name = None
                referrer_count = 0
            
            # OPTIMIZATION: Batch insert all activities and referral
            timestamp = datetime.now(timezone.utc).isoformat()
            activities_to_log = []
            
            if referrer_count < MAX_REFERRALS_FOR_POINTS:
                # Referrer gets points
                activities_to_log.append({
                    'user_id': referrer_id,
                    'username': referrer_username,
                    'first_name': referrer_first_name,
                    'activity_type': 'referral',
                    'points': POINTS_FOR_REFERRAL,
                    'timestamp': timestamp,
                    'post_id': user_id,
                    'post_timestamp': None,
                    'channel_id': None
                })
            
            # User gets joining points
            activities_to_log.append({
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'activity_type': 'joining',
                'points': POINTS_FOR_JOINING,
                'timestamp': timestamp,
                'post_id': None,
                'post_timestamp': None,
                'channel_id': None
            })
            
            # Referral record
            referral_data = {
                'referrer_id': referrer_id,
                'referrer_username': referrer_username,
                'referrer_first_name': referrer_first_name,
                'referred_user_id': user_id,
                'referred_username': username,
                'referred_first_name': first_name,
                'timestamp': timestamp
            }
            
            try:
                # BATCH INSERT
                supabase.table('activity_log').insert(activities_to_log).execute()
                supabase.table('referrals').insert(referral_data).execute()
                logger.info(f"✅ Batch logged {len(activities_to_log)} activities and referral")
            except Exception as e:
                logger.error(f"❌ Error batch logging: {e}")
            
            # Build success message
            if referrer_count >= MAX_REFERRALS_FOR_POINTS:
                # User gets points, referrer doesn't
                logger.info(f"⚠️ Referrer {referrer_id} reached limit ({referrer_count}/{MAX_REFERRALS_FOR_POINTS}), no points awarded to referrer")
                
                success_text = (
                    f"🎉 *Xush kelibsiz, {escape_markdown(first_name, version=2)}\\!*\n\n"
                    f"✅ Siz *{POINTS_FOR_JOINING} ball* oldingiz\\!\n\n"
                    f"🇩🇪 *Yevropalik o'zbek* jamoasiga xush kelibsiz\\!\n\n"
                    f"Quyidagi menyudan foydalaning:"
                )
            else:
                # Both get points
                logger.info(f"💰 Awarding points: Referrer {referrer_id} gets {POINTS_FOR_REFERRAL}, User {user_id} gets {POINTS_FOR_JOINING}")
                
                success_text = (
                    f"🎉 *Xush kelibsiz, {escape_markdown(first_name, version=2)}\\!*\n\n"
                    f"✅ Siz *{POINTS_FOR_JOINING} ball* oldingiz\\!\n"
                    f"🎁 Sizni taklif qilgan foydalanuvchi *{POINTS_FOR_REFERRAL} ball* oldi\\!\n\n"
                    f"🇩🇪 *Yevropalik o'zbek* jamoasiga xush kelibsiz\\!\n\n"
                    f"Siz ham tanlovimizda ishtirok eting va 400 000 so'm yutib oling\\!\n\n"
                    f"Quyidagi menyudan foydalaning:"
                )
                
                # Notify referrer (async, don't wait)
                try:
                    referrer_name = f"@{username}" if username else first_name
                    referrer_name_escaped = escape_markdown(referrer_name, version=2)
                    context.application.create_task(
                        context.bot.send_message(
                            chat_id=referrer_id,
                            text=f"🎉 *Tabriklaymiz\\!*\n\n{referrer_name_escaped} sizning havolangiz orqali qo'shildi\\!\n\n✨ \\+{POINTS_FOR_REFERRAL} ball hisobingizga qo'shildi\\!",
                            parse_mode=constants.ParseMode.MARKDOWN_V2
                        )
                    )
                    logger.info(f"✅ Referrer {referrer_id} notification queued")
                except Exception as e:
                    logger.error(f"❌ Failed to queue referrer notification: {e}")
            
            await query.edit_message_text(
                success_text,
                parse_mode=constants.ParseMode.MARKDOWN_V2,
                reply_markup=get_main_menu_keyboard()
            )
        else:
            # Regular user without valid referral
            save_user_to_db(user_id, username, first_name, last_name)
            welcome_msg = (
                f"👋 Salom, {escape_markdown(first_name, version=2)}\\!\n\n"
                f"🇺🇿 *SimpleQuizzer Tanlovi\\!* 🔥\n\n"
                f"Quyidagi menyudan foydalaning:"
            )
            await query.edit_message_text(
                welcome_msg,
                parse_mode=constants.ParseMode.MARKDOWN_V2,
                reply_markup=get_main_menu_keyboard()
            )
    else:
        # Regular user without referral
        save_user_to_db(user_id, username, first_name, last_name)
        welcome_msg = (
            f"👋 Salom, {escape_markdown(first_name, version=2)}\\!\n\n"
            f"🇺🇿 *SimpleQuizzer Tanlovi\\!* 🔥\n\n"
            f"Quyidagi menyudan foydalaning:"
        )
        await query.edit_message_text(
            welcome_msg,
            parse_mode=constants.ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )
    
    # Clear pending user data
    context.user_data.pop('pending_user', None)
    logger.info(f"✅ Subscription check completed for user {user_id}")

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the leaderboard with user's position - ONLY LAST 30 DAYS"""
    user_id = update.message.from_user.id
    logger.info(f"🏆 /leaderboard command received from user {user_id}")
    
    days = 30
    
    logger.info(f"📊 Generating leaderboard for last {days} days")
    
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    # ESCAPE THE DOTS
    date_range = (
        f"{start_date.strftime('%d.%m')} dan "
        f"{end_date.strftime('%d.%m')} gacha"
    )

    # Get ALL users EXCLUDING admins
    all_users = get_leaderboard(days=days, limit=None)
    all_users = [u for u in all_users if u.get('user_id') not in [ADMIN_USER_ID, ADMIN_USER_ID_EU, ADMIN_USER_ID_EU_2]]
    top_users = all_users[:20]

    if not all_users:
        logger.warning(f"⚠️ No activity for last {days} days")
        await update.message.reply_text("Oxirgi 30 kunda hech qanday faollik qayd etilmagan!")
        return

    # Find requesting user's position
    user_position = None
    user_score = 0
    
    if user_id not in [ADMIN_USER_ID, ADMIN_USER_ID_EU, ADMIN_USER_ID_EU_2]:
        for idx, user_data in enumerate(all_users):
            if user_data.get('user_id') == user_id:
                user_position = idx + 1
                user_score = user_data.get('total_score', 0)
                break
    
    leaderboard_text = f"📊 *Eng faol foydalanuvchilar \\(Oxirgi 30 kun\\)*\n"
    leaderboard_text += f"_{date_range}_\n\n"

    for i, user_data in enumerate(top_users):
        username = user_data.get('username')
        first_name = user_data.get('first_name')
        user_id_display = user_data.get('user_id')
        score = user_data.get('total_score')
        
        display_name_raw = f"@{username}" if username else (first_name or f"User {user_id_display}")
        display_name_escaped = escape_markdown(display_name_raw, version=2)
        
        if i == 0:
            rank = "🥇"
        elif i == 1:
            rank = "🥈"
        elif i == 2:
            rank = "🥉"
        else:
            rank = f"{i + 1}\\."
        
        leaderboard_text += f"{rank} {display_name_escaped} \\- {score} ball\n"
    
    # Show user's position
    if user_position:
        leaderboard_text += f"\n🎯 *Sizning pozitsiyangiz:* \\#{user_position} \\- {user_score} ball"
    else:
        leaderboard_text += f"\n💡 _Siz oxirgi 30 kunda faollik ko'rsatmagansiz\\._"

    try:
        await update.message.reply_text(leaderboard_text, parse_mode=constants.ParseMode.MARKDOWN_V2)
        logger.info(f"✅ Leaderboard sent successfully")
    except Exception as e:
        logger.error(f"❌ Failed to send leaderboard: {e}")
        await update.message.reply_text(leaderboard_text.replace('\\', ''))

async def post_contest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    logger.info(f"🎯 /contest command received from user {user_id}")
    
    if user_id != ADMIN_USER_ID_EU:
        logger.warning(f"🚫 Unauthorized contest post attempt by user {user_id}")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    logger.info(f"👑 Admin authorized, posting contest leaderboard")
    
    try:
        top_users = get_leaderboard(days=None, limit=10)
        
        if not top_users:
            await update.message.reply_text("No activity recorded yet!")
            return
        
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
        
        contest_msg += "\nRandom winner will be picked from Top 10\\."
        
        sent_message = await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=contest_msg,
            parse_mode=constants.ParseMode.MARKDOWN_V2
        )
        
        if 'contest_post_id' not in context.bot_data:
            context.bot_data['contest_post_id'] = []
        context.bot_data['contest_post_id'].append(sent_message.message_id)
        
        logger.info(f"✅ Contest posted successfully with message_id: {sent_message.message_id}")
        await update.message.reply_text(f"✅ Contest posted to group! Message ID: {sent_message.message_id}")
        
    except Exception as e:
        logger.error(f"❌ Error posting contest: {e}")
        await update.message.reply_text(f"❌ Error posting contest: {e}")


async def pick_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    logger.info(f"🎲 /pickwinner command received from user {user_id}")
    
    if user_id != ADMIN_USER_ID_EU:
        logger.warning(f"🚫 Unauthorized winner pick attempt by user {user_id}")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    logger.info(f"👑 Admin authorized, picking winner")
    
    try:
        top_users = get_leaderboard(days=None, limit=10)
        
        if not top_users:
            await update.message.reply_text("No users to pick from!")
            return
        
        winner = random.choice(top_users)
        username = winner.get('username')
        first_name = winner.get('first_name')
        winner_id = winner.get('user_id')
        score = winner.get('total_score')
        
        display_name_raw = f"@{username}" if username else (first_name or f"User {winner_id}")
        display_name_escaped = escape_markdown(display_name_raw, version=2)
        
        winner_msg = "🎊 *WINNER ANNOUNCEMENT\\!* 🎊\n\n"
        winner_msg += f"🎉 Congratulations {display_name_escaped}\\!\n\n"
        winner_msg += f"🏆 Score: {score} points\n\n"
        winner_msg += "You've been randomly selected from our Top 10\\!"
        
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
    user_id = update.message.from_user.id
    logger.info(f"🔄 /resettop command received from user {user_id}")
    
    if user_id != ADMIN_USER_ID_EU:
        logger.warning(f"🚫 Unauthorized reset attempt by user {user_id}")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    logger.info(f"👑 Admin authorized, proceeding with reset")
    
    try:
        logger.info(f"📥 Fetching all activity records")
        result = supabase.table('activity_log').select('*').execute()
        
        if result.data:
            record_count = len(result.data)
            logger.info(f"📦 Found {record_count} records to archive")
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            logger.info(f"🕐 Archive timestamp: {timestamp}")
            
            for idx, row in enumerate(result.data):
                row['archive_timestamp'] = timestamp
                supabase.table('activity_log_archive').insert(row).execute()
                if (idx + 1) % 100 == 0:
                    logger.info(f"📤 Archived {idx + 1}/{record_count} records")
            
            logger.info(f"✅ All {record_count} records archived successfully")
            
            logger.info(f"🗑️ Deleting records from main table")
            supabase.table('activity_log').delete().neq('id', 0).execute()
            logger.info(f"✅ Main table cleared")
            
            if 'contest_post_id' in context.bot_data:
                context.bot_data['contest_post_id'] = []
            
            await update.message.reply_text(f"✅ Activity log archived and reset! {record_count} records archived.")
            logger.info(f"🎉 Reset completed successfully")
        else:
            logger.info(f"⚠️ No records found to archive")
            await update.message.reply_text("No records to archive.")
            
    except Exception as e:
        logger.error(f"❌ Error resetting scores: {e}")
        await update.message.reply_text(f"❌ An error occurred while resetting the log: {e}")


async def send_bot_promo(update: Update, context: ContextTypes.DEFAULT_TYPE, promo_type: str):
    """Send bot promotion message if user is not in bot exclusion list"""
    from config import BOT_IDS_TO_REMOVE, SIMPLE_QUIZZER_PROMO, SIMPLE_SLIDES_PROMO, BOTH_BOTS_PROMO
    
    # Get user_id from either message or callback query
    if update.message:
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
        chat_id = update.callback_query.message.chat_id
    else:
        return
    
    # Don't send promo to bots or admins
    if user_id in BOT_IDS_TO_REMOVE or user_id in [ADMIN_USER_ID, ADMIN_USER_ID_EU, ADMIN_USER_ID_EU_2]:
        return
    
    # Select appropriate promo message
    promo_message = None
    if promo_type == "quizzer":
        promo_message = SIMPLE_QUIZZER_PROMO
    elif promo_type == "slides":
        promo_message = SIMPLE_SLIDES_PROMO
    elif promo_type == "both":
        promo_message = BOTH_BOTS_PROMO
    
    if promo_message:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=promo_message,
                parse_mode=constants.ParseMode.MARKDOWN_V2
            )
            logger.info(f"✅ Sent {promo_type} promo to user {user_id}")
        except Exception as e:
            logger.error(f"❌ Failed to send promo: {e}")