import logging
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
from telegram import constants

from config import (
    ADMIN_USERNAME,
    ADMIN_USERNAME_2,
    YOUTUBE_ABDUGANI,
    supabase,
    POINTS_FOR_YOUTUBE,
    YOUTUBE_MUSLIMBEK,
    CHANNEL_ID_UZBEK_EUROPE,
    CHANNEL_ID_MUSLIMBEK
)

logger = logging.getLogger(__name__)


async def show_youtube_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show YouTube subscription menu"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    try:
        muslimbek_check = supabase.table('activity_log')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('activity_type', 'youtube')\
            .eq('channel_id', CHANNEL_ID_MUSLIMBEK)\
            .execute()
        
        uzbek_europe_check = supabase.table('activity_log')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('activity_type', 'youtube')\
            .eq('channel_id', CHANNEL_ID_UZBEK_EUROPE)\
            .execute()
        
        has_muslimbek = len(muslimbek_check.data) > 0
        has_uzbek_europe = len(uzbek_europe_check.data) > 0
        
    except Exception as e:
        logger.error(f"❌ Error checking YouTube status: {e}")
        has_muslimbek = False
        has_uzbek_europe = False
    
    try:
        pending_requests = supabase.table('youtube_requests')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('status', 'pending')\
            .execute()
        
        pending_muslimbek = any(r['channel_id'] == CHANNEL_ID_MUSLIMBEK for r in pending_requests.data)
        pending_uzbek_europe = any(r['channel_id'] == CHANNEL_ID_UZBEK_EUROPE for r in pending_requests.data)
        
    except Exception as e:
        logger.error(f"❌ Error checking pending requests: {e}")
        pending_muslimbek = False
        pending_uzbek_europe = False
    
    muslimbek_status = "✅ Ball olindi" if has_muslimbek else ("⏳ Kutilmoqda" if pending_muslimbek else f"🎁 {POINTS_FOR_YOUTUBE} ball")
    uzbek_europe_status = "✅ Ball olindi" if has_uzbek_europe else ("⏳ Kutilmoqda" if pending_uzbek_europe else f"🎁 {POINTS_FOR_YOUTUBE} ball")
    
    text = (
        f"📺 *YOUTUBE ORQALI BALL YIGING\\!*\n\n"
        f"Bizning YouTube kanallariga obuna bo'lib qo'shimcha ball oling\\!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔖 *Muslimbek Abdurakhimov*\n"
        f"Status: {escape_markdown(muslimbek_status, version=2)}\n\n"
        f"🔖 *Abdug'ani Bozarov*\n"
        f"Status: {escape_markdown(uzbek_europe_status, version=2)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 *Har bir kanal uchun:* {POINTS_FOR_YOUTUBE} ball\n\n"
        f"⚠️ *MUHIM:*\n"
        f"• Obuna bo'ling va skrinshot oling\n"
        f"• Skrinni {ADMIN_USERNAME} ga yuboring\n"
        f"• Tasdiqlangandan keyin ball olasiz\n"
        f"• Obunalar tekshiriladi\\!\n"
        f"• Agar qaytarib olsangiz\\, ballar olib qo'yiladi\\!\n\n"
        f"👇 Obuna bo'ldingizmi\\?"
    )
    
    keyboard = []
    
    if not has_muslimbek and not pending_muslimbek:
        keyboard.append([InlineKeyboardButton(
            "🔖 Muslimbek Abdurakhimov", 
            callback_data="youtube_muslimbek"
        )])
    
    if not has_uzbek_europe and not pending_uzbek_europe:
        keyboard.append([InlineKeyboardButton(
            "🔖 Abdug'ani Bozarov", 
            callback_data="youtube_uzbek_europe"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ Orqaga", callback_data="menu_participate")])
    
    await query.edit_message_text(
        text,
        parse_mode=constants.ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_youtube_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username = query.from_user.username
    first_name = query.from_user.first_name
    last_name = query.from_user.last_name
    
    # Determine which channel based on callback
    if query.data == "youtube_muslimbek":
        channel_id = CHANNEL_ID_MUSLIMBEK
        channel_name = "Muslimbek Abdurakhimov"
        youtube_url = YOUTUBE_MUSLIMBEK
    else:  # youtube_uzbek_europe
        channel_id = CHANNEL_ID_UZBEK_EUROPE
        channel_name = "Abdug'ani Bozarov"
        youtube_url = YOUTUBE_ABDUGANI
    try:
        existing_points = supabase.table('activity_log')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('activity_type', 'youtube')\
            .eq('channel_id', channel_id)\
            .execute()
        
        if len(existing_points.data) > 0:
            await query.answer("✅ Siz bu kanal uchun allaqachon ball oldingiz!", show_alert=True)
            return
    except Exception as e:
        logger.error(f"❌ Error checking existing points: {e}")
    
    # Check if already has pending request
    try:
        pending = supabase.table('youtube_requests')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('channel_id', channel_id)\
            .eq('status', 'pending')\
            .execute()
        
        if len(pending.data) > 0:
            await query.answer("⏳ Sizning so'rovingiz allaqachon yuborilgan! Javobni kuting.", show_alert=True)
            return
    except Exception as e:
        logger.error(f"❌ Error checking pending requests: {e}")
    
    # Create request in database
    try:
        request_data = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'channel_id': channel_id,
            'channel_name': channel_name,
            'status': 'pending',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'admin_message_ids': {}
        }
        
        result = supabase.table('youtube_requests').insert(request_data).execute()
        request_id = result.data[0]['id']
        
        logger.info(f"✅ Created YouTube request {request_id} for user {user_id}, channel {channel_id}")
        
    except Exception as e:
        logger.error(f"❌ Error creating YouTube request: {e}")
        await query.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.", show_alert=True)
        return
    
    # Send notification to ALL admins
    from config import YOUTUBE_ADMIN_IDS
    admin_message_ids = {}
    
    try:
        user_display = f"@{username}" if username else first_name
        user_info = (
            f"👤 *Foydalanuvchi:* {escape_markdown(user_display, version=2)}\n"
            f"🆔 *ID:* `{user_id}`\n"
            f"📝 *Ism:* {escape_markdown(first_name or 'N/A', version=2)}\n"
            f"📝 *Familiya:* {escape_markdown(last_name or 'N/A', version=2)}\n"
            f"👤 *Username:* {escape_markdown(f'@{username}' if username else 'N/A', version=2)}\n"
        )
        
        admin_text = (
            f"📺 *YOUTUBE OBUNA SO'ROVI*\n\n"
            f"🔖 *Kanal:* {escape_markdown(channel_name, version=2)}\n"
            f"🔗 *YouTube:* {escape_markdown(youtube_url, version=2)}\n\n"
            f"{user_info}\n"
            f"💰 *Ball:* {POINTS_FOR_YOUTUBE}\n\n"
            f"⚠️ *Foydalanuvchiga skrinshot yuborishni eslatdingizmi\\?*"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"youtube_approve_{request_id}"),
                InlineKeyboardButton("❌ Rad etish", callback_data=f"youtube_decline_{request_id}")
            ]
        ]
        
        # Send to all admins and store message IDs
        for admin_id in YOUTUBE_ADMIN_IDS:
            try:
                sent_message = await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    parse_mode=constants.ParseMode.MARKDOWN_V2,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                admin_message_ids[str(admin_id)] = sent_message.message_id
                logger.info(f"✅ Sent YouTube request notification to admin {admin_id}")
            except Exception as e:
                logger.error(f"❌ Error sending notification to admin {admin_id}: {e}")
        
        # Update request with message IDs
        supabase.table('youtube_requests')\
            .update({'admin_message_ids': admin_message_ids})\
            .eq('id', request_id)\
            .execute()
        
    except Exception as e:
        logger.error(f"❌ Error sending admin notifications: {e}")
    
    # Inform user
    user_text = (
        f"✅ *So'rovingiz yuborildi\\!*\n\n"
        f"📺 *Kanal:* {escape_markdown(channel_name, version=2)}\n\n"
        f"📸 *Endi quyidagilarni bajaring:*\n"
        f"1️⃣ YouTube kanaliga o'ting\n"
        f"2️⃣ Obuna tugmasini bosing\n"
        f"3️⃣ Skrinshot oling\n"
        f"4️⃣ /send\\_youtube\\_screenshot buyrug'ini yuboring va skrinni yuklang\n"
        f"5️⃣ Yoki skrinni to'g'ridan to'g'ri {ADMIN_USERNAME} yoki {ADMIN_USERNAME_2} ga yuborishingiz mumkin\n\n"
        f"⏳ Tasdiqlangandan keyin ball olasiz\\!\n\n"
        f"🔗 *YouTube:* {escape_markdown(youtube_url, version=2)}"
    )
    
    await query.edit_message_text(
        user_text,
        parse_mode=constants.ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Orqaga", callback_data="youtube_menu")
        ]])
    )


async def handle_youtube_admin_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin approval/decline of YouTube request"""
    query = update.callback_query
    await query.answer()
    
    admin_id = query.from_user.id
    admin_username = query.from_user.username or query.from_user.first_name
    
    # Check if user is an admin
    from config import YOUTUBE_ADMIN_IDS
    if admin_id not in YOUTUBE_ADMIN_IDS:
        await query.answer("❌ Siz admin emassiz!", show_alert=True)
        return
    
    # Parse callback data
    action, request_id = query.data.rsplit('_', 1)
    is_approve = action == "youtube_approve"
    
    try:
        # Get request details
        request = supabase.table('youtube_requests')\
            .select('*')\
            .eq('id', request_id)\
            .execute()
        
        if not request.data:
            await query.answer("❌ So'rov topilmadi!", show_alert=True)
            return
        
        request_data = request.data[0]
        
        # Check if already processed
        if request_data['status'] != 'pending':
            processed_by = request_data.get('processed_by_username', 'admin')
            await query.answer(f"⚠️ Bu so'rov allaqachon {request_data['status']} qilingan ({processed_by} tomonidan)!", show_alert=True)
            return
        
        user_id = request_data['user_id']
        username = request_data['username']
        first_name = request_data['first_name']
        channel_id = request_data['channel_id']
        channel_name = request_data['channel_name']
        admin_message_ids = request_data.get('admin_message_ids', {})
        
        if is_approve:
            # Check if user already received points for this channel (prevent duplicate)
            try:
                existing_points = supabase.table('activity_log')\
                    .select('id')\
                    .eq('user_id', user_id)\
                    .eq('activity_type', 'youtube')\
                    .eq('channel_id', channel_id)\
                    .execute()
                
                if len(existing_points.data) > 0:
                    # Already received points
                    supabase.table('youtube_requests')\
                        .update({
                            'status': 'approved',
                            'processed_at': datetime.now(timezone.utc).isoformat(),
                            'processed_by': admin_id,
                            'processed_by_username': admin_username
                        })\
                        .eq('id', request_id)\
                        .execute()
                    
                    logger.warning(f"⚠️ User {user_id} already received points for YouTube channel {channel_id}")
                    
                    await query.answer(f"⚠️ Foydalanuvchi bu kanal uchun allaqachon ball olgan! So'rov tasdiqlandi, lekin ball berilmadi.", show_alert=True)
                    
                    user_text = (
                        f"✅ *So'rovingiz tasdiqlandi\\!*\n\n"
                        f"📺 *Kanal:* {escape_markdown(channel_name, version=2)}\n\n"
                        f"⚠️ Siz bu kanal uchun allaqachon ball olgan edingiz\\."
                    )
                    
                    keyboard = [
                        [InlineKeyboardButton("👤 Profilim", callback_data="menu_profile")],
                        [InlineKeyboardButton("🏆 Liderlar", callback_data="menu_leaderboard")],
                        [InlineKeyboardButton("🎯 Bosh menyu", callback_data="menu_main")]
                    ]
                    
                    admin_response = f"✅ So'rov tasdiqlandi, lekin ball allaqachon berilgan edi ({admin_username} tomonidan)!"
                    
                else:
                    # Award points normally
                    from utils.helpers import log_activity
                    log_activity(
                        user_id=user_id,
                        username=username,
                        first_name=first_name,
                        activity_type='youtube',
                        points=POINTS_FOR_YOUTUBE,
                        post_id=None,
                        post_timestamp=None,
                        channel_id=channel_id
                    )
                    
                    # Update request status
                    supabase.table('youtube_requests')\
                        .update({
                            'status': 'approved',
                            'processed_at': datetime.now(timezone.utc).isoformat(),
                            'processed_by': admin_id,
                            'processed_by_username': admin_username
                        })\
                        .eq('id', request_id)\
                        .execute()
                    
                    logger.info(f"✅ Approved YouTube request {request_id} by admin {admin_username}, awarded {POINTS_FOR_YOUTUBE} points to user {user_id}")
                    
                    # Notify user
                    user_text = (
                        f"🎉 *Tabriklaymiz\\!*\n\n"
                        f"Sizning YouTube obuna so'rovingiz tasdiqlandi\\!\n\n"
                        f"📺 *Kanal:* {escape_markdown(channel_name, version=2)}\n"
                        f"💰 *Olingan ball:* \\+{POINTS_FOR_YOUTUBE}\n\n"
                        f"✅ Ballaringiz hisobingizga qo'shildi\\!"
                    )
                    
                    keyboard = [
                        [InlineKeyboardButton("👤 Profilim", callback_data="menu_profile")],
                        [InlineKeyboardButton("🏆 Liderlar", callback_data="menu_leaderboard")],
                        [InlineKeyboardButton("🎯 Bosh menyu", callback_data="menu_main")]
                    ]
                    
                    admin_response = f"✅ So'rov tasdiqlandi ({admin_username} tomonidan)!"
                    
            except Exception as e:
                logger.error(f"❌ Error checking existing points: {e}")
                await query.answer("❌ Xatolik yuz berdi!", show_alert=True)
                return
            
        else:
            # Decline request
            supabase.table('youtube_requests')\
                .update({
                    'status': 'declined',
                    'processed_at': datetime.now(timezone.utc).isoformat(),
                    'processed_by': admin_id,
                    'processed_by_username': admin_username
                })\
                .eq('id', request_id)\
                .execute()
            
            logger.info(f"❌ Declined YouTube request {request_id} by admin {admin_username} for user {user_id}")
            
            # Notify user
            user_text = (
                f"❌ *So'rovingiz rad etildi*\n\n"
                f"📺 *Kanal:* {escape_markdown(channel_name, version=2)}\n\n"
                f"Iltimos\\, quyidagilarni tekshiring:\n"
                f"• YouTube kanaliga haqiqatan ham obuna bo'lganmisiz\\?\n"
                f"• Skrinshot aniq ko'rinib turadimi\\?\n"
                f"• To'g'ri kanalga obuna bo'lganmisiz\\?\n\n"
                f"Qaytadan urinib ko'rishingiz mumkin\\!"
            )
            
            keyboard = [
                [InlineKeyboardButton("📺 Qayta urinish", callback_data="youtube_menu")],
                [InlineKeyboardButton("🎯 Bosh menyu", callback_data="menu_main")]
            ]
            
            admin_response = f"❌ So'rov rad etildi ({admin_username} tomonidan)!"
        
        # Send notification to user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=user_text,
                parse_mode=constants.ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"❌ Error sending user notification: {e}")
        
        # Update ALL admin messages
        user_display = f"@{username}" if username else first_name
        formatted_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        escaped_time = escape_markdown(formatted_time, version=2)

        updated_admin_text = (
            f"{'✅ TASDIQLANDI' if is_approve else '❌ RAD ETILDI'}\n\n"
            f"📺 *Kanal:* {escape_markdown(channel_name, version=2)}\n"
            f"👤 *Foydalanuvchi:* {escape_markdown(user_display, version=2)}\n"
            f"💰 *Ball:* {POINTS_FOR_YOUTUBE if is_approve else 0}\n\n"
            f"👨‍💼 *Admin:* {escape_markdown(admin_username, version=2)}\n"
            f"⏰ *Vaqt:* {escaped_time}"
        )
        
        # Update the current admin's message
        try:
            await query.edit_message_text(
                text=updated_admin_text,
                parse_mode=constants.ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.error(f"❌ Error updating current admin message: {e}")
        
        # Update messages for OTHER admins
        for admin_id_str, message_id in admin_message_ids.items():
            if int(admin_id_str) == admin_id:
                continue
                
            try:
                await context.bot.edit_message_text(
                    chat_id=int(admin_id_str),
                    message_id=message_id,
                    text=updated_admin_text,
                    parse_mode=constants.ParseMode.MARKDOWN_V2
                )
            except Exception as e:
                logger.error(f"❌ Error updating message for admin {admin_id_str}: {e}")
        
        await query.answer(admin_response, show_alert=True)
        
    except Exception as e:
        logger.error(f"❌ Error processing YouTube request: {e}")
        await query.answer("❌ Xatolik yuz berdi!", show_alert=True)


async def send_youtube_screenshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to initiate YouTube screenshot upload"""
    user_id = update.message.from_user.id
    
    text = (
        f"📸 *YOUTUBE SKRINSHOT YUBORISH*\n\n"
        f"Iltimos\\, YouTube obuna skrinshot'ingizni yuboring\\.\n\n"
        f"⚠️ *Eslatma:*\n"
        f"• Skrinshot aniq ko'rinishi kerak\n"
        f"• Obuna qilganingiz ko'rinib turishi shart\n"
        f"• Har bir kanal uchun alohida skrinshot yuboring\n\n"
        f"📤 Rasmni hozir yuboring\\!"
    )
    
    # Set state for waiting screenshot
    context.user_data['waiting_youtube_screenshot'] = True
    
    await update.message.reply_text(
        text,
        parse_mode=constants.ParseMode.MARKDOWN_V2
    )


async def handle_youtube_screenshot_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YouTube screenshot photo upload"""
    if not context.user_data.get('waiting_youtube_screenshot'):
        return
    
    user_id = update.message.from_user.id
    username = update.message.from_user.username 
    first_name = update.message.from_user.first_name
    
    # Get the photo
    photo = update.message.photo[-1]
    
    # Get user's pending requests
    try:
        pending_requests = supabase.table('youtube_requests')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('status', 'pending')\
            .execute()
        
        if not pending_requests.data:
            await update.message.reply_text(
                "❌ Sizda hozirda kutilayotgan YouTube so'rov yo'q\\. Avval YouTube obuna so'rovini yuboring\\.",
                parse_mode=constants.ParseMode.MARKDOWN_V2
            )
            context.user_data['waiting_youtube_screenshot'] = False
            return
        
        # Forward screenshot to all admins
        from config import YOUTUBE_ADMIN_IDS
        
        user_display = f"@{username}" if username else first_name
        caption = (
            f"📸 *YOUTUBE SKRINSHOT*\n\n"
            f"👤 *Foydalanuvchi:* {escape_markdown(user_display, version=2)}\n"
            f"🆔 *ID:* `{user_id}`\n\n"
            f"⏳ *Kutilayotgan so'rovlar:* {len(pending_requests.data)} ta"
        )
        
        for admin_id in YOUTUBE_ADMIN_IDS:
            try:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo.file_id,
                    caption=caption,
                    parse_mode=constants.ParseMode.MARKDOWN_V2
                )
                logger.info(f"✅ Forwarded YouTube screenshot to admin {admin_id}")
            except Exception as e:
                logger.error(f"❌ Error forwarding to admin {admin_id}: {e}")
        
        # Confirm to user
        await update.message.reply_text(
            "✅ Skrinshot adminlarga yuborildi\\! Javobni kuting\\.",
            parse_mode=constants.ParseMode.MARKDOWN_V2
        )
        
        # Reset state
        context.user_data['waiting_youtube_screenshot'] = False
        
    except Exception as e:
        logger.error(f"❌ Error handling YouTube screenshot: {e}")
        await update.message.reply_text(
            "❌ Xatolik yuz berdi\\. Qaytadan urinib ko'ring\\.",
            parse_mode=constants.ParseMode.MARKDOWN_V2
        )