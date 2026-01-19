import logging
import json
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes

from config import (
    supabase,
    ADMIN_USER_ID,
    ADMIN_USER_ID_EU,
    ADMIN_USER_ID_EU_2
)

logger = logging.getLogger(__name__)

WEBAPP_URL = "https://mrsimple007.github.io/uzbek_europe_leaderboard/"

async def webapp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send Mini App button - data will be fetched by the webapp itself"""
    user_id = update.message.from_user.id
    
    logger.info(f"📱 /webapp command received from user {user_id}")
    
    try:
        webapp_url = WEBAPP_URL
        
        keyboard = [
            [InlineKeyboardButton(
                "📊 Batafsil Liderlar Jadvali", 
                web_app=WebAppInfo(url=webapp_url)
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🏆 *Liderlar jadvalini ko'rish*\n\n"
            "Quyidagi tugmani bosib, batafsil statistikani ko'rishingiz mumkin!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        logger.info(f"✅ WebApp button sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error sending webapp: {e}")
        await update.message.reply_text(
            "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring."
        )


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle data requests from Web App"""
    user_id = update.message.from_user.id
    web_app_data = update.message.web_app_data.data
    
    logger.info(f"📨 Received web app data from user {user_id}: {web_app_data}")
    
    try:
        data = json.loads(web_app_data)
        action = data.get('action')
        
        if action == 'get_leaderboard':
            days = data.get('days', 30)
            leaderboard_data = get_detailed_leaderboard(user_id, days)
            
            # Send response back - but this is limited too
            # Better to have webapp fetch directly from Supabase
            await update.message.reply_text(
                f"✅ Ma'lumot yuklandi!\n\n"
                f"📊 Jami {len(leaderboard_data['leaderboard'])} foydalanuvchi",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"❌ Error handling webapp data: {e}")


def get_detailed_leaderboard(current_user_id: int, days: int = 30):
    """
    Get detailed leaderboard with activity breakdown
    Returns JSON-ready data structure
    """
    logger.info(f"📊 Fetching detailed leaderboard for last {days} days")
    
    try:
        # Calculate cutoff date
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        # Fetch all activities within date range
        result = supabase.table('activity_log')\
            .select('user_id, username, first_name, points, activity_type, channel_id')\
            .gte('timestamp', cutoff_date)\
            .execute()
        
        logger.info(f"📥 Fetched {len(result.data)} activity records")
        
        # Aggregate by user with activity breakdown
        user_scores = {}
        
        for row in result.data:
            uid = row['user_id']
            
            if uid not in user_scores:
                user_scores[uid] = {
                    'user_id': uid,
                    'username': row['username'],
                    'first_name': row['first_name'],
                    'total_score': 0,
                    'comment_points': 0,
                    'reaction_points': 0,
                    'boost_points': 0,
                    'quiz_points': 0,
                    'referral_points': 0,
                    'uzbek_europe_points': 0,
                    'muslimbek_points': 0
                }
            
            points = row['points']
            activity = row['activity_type']
            channel = row.get('channel_id')
            
            # Add to total
            user_scores[uid]['total_score'] += points
            
            # Breakdown by activity type
            if activity == 'comment':
                user_scores[uid]['comment_points'] += points
            elif activity == 'reaction':
                user_scores[uid]['reaction_points'] += points
            elif activity == 'boost':
                user_scores[uid]['boost_points'] += points
            elif activity == 'quiz':
                user_scores[uid]['quiz_points'] += points
            elif activity in ['referral', 'joining']:
                user_scores[uid]['referral_points'] += points
            
            # Breakdown by channel
            if channel == 'uzbek_europe':
                user_scores[uid]['uzbek_europe_points'] += points
            elif channel == 'muslimbek_01':
                user_scores[uid]['muslimbek_points'] += points
        
        # Filter out admins
        filtered_users = [
            user for user in user_scores.values()
            if user['user_id'] not in [ADMIN_USER_ID, ADMIN_USER_ID_EU, ADMIN_USER_ID_EU_2]
        ]
        
        # Sort by total score
        sorted_users = sorted(
            filtered_users, 
            key=lambda x: x['total_score'], 
            reverse=True
        )
        
        logger.info(f"👥 Processed {len(sorted_users)} unique users")
        
        # Find current user's position
        my_position = None
        for idx, user in enumerate(sorted_users):
            if user['user_id'] == current_user_id:
                my_position = {
                    'rank': idx + 1,
                    'points': user['total_score'],
                    'user_data': user
                }
                break
        
        # Return data structure
        return {
            'leaderboard': sorted_users[:50],  # Top 50
            'my_position': my_position,
            'total_users': len(sorted_users),
            'date_range': {
                'days': days,
                'from': cutoff_date,
                'to': datetime.now(timezone.utc).isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching detailed leaderboard: {e}")
        return {
            'leaderboard': [],
            'my_position': None,
            'total_users': 0,
            'error': str(e)
        }