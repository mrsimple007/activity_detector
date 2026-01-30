import logging
from datetime import datetime, timedelta, timezone
from config import (
    supabase, 
    POINTS_FOR_COMMENT_EARLY, 
    POINTS_FOR_COMMENT_LATE,
    POINTS_FOR_REACTION_EARLY,
    POINTS_FOR_REACTION_LATE,
    EARLY_WINDOW_HOURS,
    MAX_DAILY_POINTS,
    COOLDOWN_SECONDS
)
from telegram.ext import ContextTypes
from telegram import constants
from telegram import helpers
from telegram.helpers import escape_markdown

logger = logging.getLogger(__name__)


def calculate_points(activity_type: str, post_timestamp: datetime) -> int:
    """Calculate points based on activity type and time since post"""
    from config import (
        POINTS_FOR_REACTION_EARLY, 
        POINTS_FOR_REACTION_LATE,
        EARLY_WINDOW_HOURS
    )
        
    time_since_post = datetime.now(timezone.utc) - post_timestamp
    hours_since_post = time_since_post.total_seconds() / 3600
    is_early = hours_since_post <= EARLY_WINDOW_HOURS
    
    logger.info(f"⏱️  Time since post: {hours_since_post:.2f} hours (Early: {is_early})")
    
    if activity_type == 'reaction':
        points = POINTS_FOR_REACTION_EARLY if is_early else POINTS_FOR_REACTION_LATE
        logger.info(f"❤️  Reaction points awarded: {points}")
        return points

    return 0


def has_user_commented_on_post(user_id: int, post_id: int) -> bool:    
    try:
        result = supabase.table('activity_log').select('id').eq('user_id', user_id).eq('post_id', post_id).eq('activity_type', 'comment').execute()
        has_commented = len(result.data) > 0
        
        if has_commented:
            logger.info(f"✅ User {user_id} HAS already commented on post {post_id}")
        else:
            logger.info(f"➕ User {user_id} has NOT commented on post {post_id} yet")
        
        return has_commented
    except Exception as e:
        logger.error(f"❌ Error checking comment status: {e}")
        return False


def log_activity(user_id: int, username: str, first_name: str, activity_type: str, 
                 points: int, post_id: int = None, post_timestamp: datetime = None, 
                 channel_id: str = None):
    display_name = f"@{username}" if username else (first_name or f"User {user_id}")
    logger.info(f"   Type: {activity_type}, Points: {points}, Post ID: {post_id}, Channel: {channel_id}")
    
    try:
        timestamp = datetime.now(timezone.utc).isoformat()

        data = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'activity_type': activity_type,
            'points': points,
            'timestamp': timestamp,
            'post_id': post_id,
            'post_timestamp': post_timestamp.isoformat() if post_timestamp else None,
            'channel_id': channel_id
        }
        
        result = supabase.table('activity_log').insert(data).execute()
        logger.info(f"✅ Successfully logged {activity_type} for {display_name} worth {points} points. Row ID: {result.data[0].get('id') if result.data else 'N/A'}")
    except Exception as e:
        logger.error(f"❌ Error logging activity to Supabase: {e}")
        
def get_leaderboard(days: int = None, limit: int = 20):
    period_desc = f"last {days} days" if days else "all time"
    logger.info(f"🏆 Fetching leaderboard for {period_desc} (limit: {limit if limit else 'all'})")
    
    try:
        query = supabase.table('activity_log').select('user_id, username, first_name, points')
        
        if days:
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            query = query.gte('timestamp', cutoff_date)
            logger.info(f"📅 Filtering activities since: {cutoff_date}")
        
        result = query.execute()

        # Aggregate points by user
        user_scores = {}
        for row in result.data:
            user_id = row['user_id']
            if user_id not in user_scores:
                user_scores[user_id] = {
                    'user_id': user_id,
                    'username': row['username'],
                    'first_name': row['first_name'],
                    'total_score': 0
                }
            user_scores[user_id]['total_score'] += row['points']
        
        logger.info(f"👥 Aggregated scores for {len(user_scores)} unique users")
        
        # Sort by score
        sorted_users = sorted(user_scores.values(), key=lambda x: x['total_score'], reverse=True)
        
        # Apply limit if specified
        if limit:
            sorted_users = sorted_users[:limit]        
        return sorted_users
    except Exception as e:
        logger.error(f"❌ Error fetching leaderboard: {e}")
        return []
    

def generate_referral_link(user_id: int, bot_username: str) -> str:
    """Generate a unique referral link for user"""
    return f"https://t.me/{bot_username}?start=ref_{user_id}"

def get_referrer_from_payload(payload: str) -> int:
    """Extract referrer user_id from start payload"""
    if payload and payload.startswith('ref_'):
        try:
            return int(payload.split('_')[1])
        except (IndexError, ValueError):
            return None
    return None

def has_user_joined_before(user_id: int) -> bool:
    """Check if user has already joined via referral"""
    try:
        result = supabase.table('referrals').select('id').eq('referred_user_id', user_id).execute()
        return len(result.data) > 0
    except Exception as e:
        logger.error(f"❌ Error checking referral status: {e}")
        return False

def log_referral(referrer_id: int, referred_user_id: int, referred_username: str, referred_first_name: str):
    """Log referral to database with referrer information"""
    try:
        # Get referrer information
        referrer_info = supabase.table('uzbek_europe_users').select('username, first_name').eq('user_id', referrer_id).limit(1).execute()
        
        referrer_username = None
        referrer_first_name = None
        
        if referrer_info.data:
            referrer_username = referrer_info.data[0].get('username')
            referrer_first_name = referrer_info.data[0].get('first_name')
        
        timestamp = datetime.now(timezone.utc).isoformat()
        data = {
            'referrer_id': referrer_id,
            'referrer_username': referrer_username,
            'referrer_first_name': referrer_first_name,
            'referred_user_id': referred_user_id,
            'referred_username': referred_username,
            'referred_first_name': referred_first_name,
            'timestamp': timestamp
        }
        supabase.table('referrals').insert(data).execute()
        logger.info(f"✅ Referral logged: {referrer_id} ({referrer_first_name}) -> {referred_user_id} ({referred_first_name})")
    except Exception as e:
        logger.error(f"❌ Error logging referral: {e}")

async def check_channel_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is member of the channel"""
    try:
        from config import CHANNEL_USERNAME
        channel_id = f"@{CHANNEL_USERNAME}"
        
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        is_member = member.status in ['member', 'administrator', 'creator']
        
        logger.info(f"✅ Channel membership check for user {user_id}: {is_member} (status: {member.status})")
        return is_member
    except Exception as e:
        logger.error(f"❌ Error checking channel membership: {e}")
        return False
    

def get_referrer_referral_count(referrer_id: int) -> int:
    """Get count of successful referrals for a user"""
    try:
        result = supabase.table('referrals').select('id').eq('referrer_id', referrer_id).execute()
        count = len(result.data)
        return count
    except Exception as e:
        logger.error(f"❌ Error getting referral count: {e}")
        return 0


def save_user_to_db(user_id: int, username: str, first_name: str, last_name: str = None):    
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Check if user exists
        existing = supabase.table('uzbek_europe_users').select('id').eq('user_id', user_id).execute()
        
        user_data = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'updated_at': timestamp
        }
        
        if existing.data:
            # Update existing user
            logger.info(f"🔄 Updating existing user {user_id}")
            supabase.table('uzbek_europe_users').update(user_data).eq('user_id', user_id).execute()
        else:
            user_data['created_at'] = timestamp
            supabase.table('uzbek_europe_users').insert(user_data).execute()
        
        return True
    except Exception as e:
        logger.error(f"❌ Error saving user to database: {e}")
        return False
    


def get_user_stats(user_id: int):
    """Get comprehensive user statistics with per-channel breakdown"""
    try:
        from config import CHANNEL_ID_UZBEK_EUROPE, CHANNEL_ID_MUSLIMBEK, ADMIN_USER_ID, ADMIN_USER_ID_EU, ADMIN_USER_ID_EU_2
        
        result = supabase.table('activity_log').select('*').eq('user_id', user_id).execute()
        
        total_points = 0
        username = None
        first_name = None
        
        # Per-channel statistics
        stats_by_channel = {
            CHANNEL_ID_UZBEK_EUROPE: {
                'comment_points': 0,
                'reaction_points': 0,
                'boost_points': 0,
                'instagram_points': 0,
            },
            CHANNEL_ID_MUSLIMBEK: {
                'comment_points': 0,
                'reaction_points': 0,
                'boost_points': 0,
                'instagram_points': 0,
            }
        }
        
        # Global statistics (not channel-specific)
        referral_points = 0
        quiz_points = 0
        
        for row in result.data:
            points = row.get('points', 0)
            total_points += points
            
            activity_type = row.get('activity_type')
            channel_id = row.get('channel_id')
            
            # Track username and first_name
            if not username:
                username = row.get('username')
            if not first_name:
                first_name = row.get('first_name')
            
            # Global activities (not channel-specific)
            if activity_type == 'referral':
                referral_points += points
            elif activity_type == 'quiz':
                quiz_points += points
            elif activity_type == 'joining':
                referral_points += points  # Joining points count as referral category
            
            # Channel-specific activities
            if channel_id in stats_by_channel:
                if activity_type == 'comment':
                    stats_by_channel[channel_id]['comment_points'] += points
                elif activity_type == 'reaction':
                    stats_by_channel[channel_id]['reaction_points'] += points
                elif activity_type == 'boost':
                    stats_by_channel[channel_id]['boost_points'] += points
                elif activity_type == 'instagram':
                    stats_by_channel[channel_id]['instagram_points'] += points
        
        # Get referral count and breakdown - NEW
        referral_result = supabase.table('referrals').select('is_valid').eq('referrer_id', user_id).execute()
        referral_count = len(referral_result.data)
        
        # Count valid and invalid referrals
        valid_referrals = sum(1 for r in referral_result.data if r.get('is_valid', True))
        invalid_referrals = referral_count - valid_referrals
        
        # Get user position - USE 30 DAYS for consistency with leaderboard
        all_users = get_leaderboard(days=30, limit=None)
        
        # Filter admins
        filtered_users = [u for u in all_users if u.get('user_id') not in [ADMIN_USER_ID, ADMIN_USER_ID_EU, ADMIN_USER_ID_EU_2]]
        
        user_position = None
        for idx, user_data in enumerate(filtered_users):
            if user_data.get('user_id') == user_id:
                user_position = idx + 1
                break
        
        if user_position is None:
            user_position = len(filtered_users) + 1
        
        return {
            'username': username,
            'first_name': first_name,
            'total_points': total_points,
            'referral_points': referral_points,
            'quiz_points': quiz_points,
            'referral_count': referral_count,
            'referral_breakdown': {  # NEW
                'valid': valid_referrals,
                'invalid': invalid_referrals
            },
            'position': user_position,
            'uzbek_europe': stats_by_channel[CHANNEL_ID_UZBEK_EUROPE],
            'muslimbek': stats_by_channel[CHANNEL_ID_MUSLIMBEK]
        }
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return None
    

async def check_user_boost_status(user_id: int, channel_username: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user has boosted a specific channel using Telegram API"""
    try:
        channel_id = f"@{channel_username}"
        
        # Use getUserChatBoosts API
        boosts = await context.bot.get_user_chat_boosts(
            chat_id=channel_id,
            user_id=user_id
        )
        
        # Check if user has active boosts
        has_boost = len(boosts.boosts) > 0
        
        logger.info(f"✅ Boost check for user {user_id} in @{channel_username}: {has_boost} ({len(boosts.boosts)} boosts)")
        return has_boost
        
    except Exception as e:
        logger.error(f"❌ Error checking boost status for user {user_id} in @{channel_username}: {e}")
        return False


def has_user_boosted_channel(user_id: int, channel_id: str) -> bool:
    """Check if user has already received points for boosting this channel"""
    try:
        result = supabase.table('activity_log').select('id').eq('user_id', user_id).eq('activity_type', 'boost').eq('channel_id', channel_id).execute()
        return len(result.data) > 0
    except Exception as e:
        logger.error(f"❌ Error checking boost record: {e}")
        return False



# In utils/helpers.py
def check_rate_limit(user_id: int, activity_type: str) -> bool:
    """Check if user is rate limited for this activity type"""
    try:
        cooldown = COOLDOWN_SECONDS.get(activity_type, 0)
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=cooldown)
        
        result = supabase.table('activity_log')\
            .select('timestamp')\
            .eq('user_id', user_id)\
            .eq('activity_type', activity_type)\
            .gte('timestamp', cutoff_time.isoformat())\
            .order('timestamp', desc=True)\
            .limit(1)\
            .execute()
        
        if result.data:
            return True
        return False
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        return False
    

def check_daily_limit(user_id: int, activity_type: str, points: int, channel_id: str = None) -> tuple[bool, int]:
    """Check daily limit per channel for comments and reactions"""
    try:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get limit for this activity type and channel
        if activity_type in ['comment', 'reaction']:
            if not channel_id or channel_id not in MAX_DAILY_POINTS[activity_type]:
                logger.warning(f"⚠️ No channel_id or invalid channel for {activity_type}")
                return False, points
            
            max_points = MAX_DAILY_POINTS[activity_type][channel_id]
            
            # Query points for this specific channel today
            result = supabase.table('activity_log')\
                .select('points')\
                .eq('user_id', user_id)\
                .eq('activity_type', activity_type)\
                .eq('channel_id', channel_id)\
                .gte('timestamp', today_start.isoformat())\
                .execute()
        else:
            # For other activities (referral, quiz, etc.) - no per-channel limit
            return False, points
        
        total_today = sum(row['points'] for row in result.data)
        
        logger.info(f"📊 User {user_id} has {total_today}/{max_points} points for {activity_type} in {channel_id} today")
        
        if total_today >= max_points:
            return True, 0
        
        # Adjust points if would exceed limit
        adjusted_points = min(points, max_points - total_today)
        return False, adjusted_points
        
    except Exception as e:
        logger.error(f"Error checking daily limit: {e}")
        return False, points
    

def is_user_registered(user_id: int) -> bool:
    try:
        result = supabase.table('uzbek_europe_users').select('id').eq('user_id', user_id).execute()
        is_registered = len(result.data) > 0
        return is_registered
    except Exception as e:
        logger.error(f"❌ Error checking user registration: {e}")
        return False
    

async def check_channel_membership_both(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Check if user is member of BOTH channels"""
    try:
        from config import CHANNEL_USERNAME, CHANNEL_USERNAME_2
        
        # Check first channel
        channel_1 = f"@{CHANNEL_USERNAME}"
        member_1 = await context.bot.get_chat_member(chat_id=channel_1, user_id=user_id)
        is_member_1 = member_1.status in ['member', 'administrator', 'creator']
        
        # Check second channel
        channel_2 = f"@{CHANNEL_USERNAME_2}"
        member_2 = await context.bot.get_chat_member(chat_id=channel_2, user_id=user_id)
        is_member_2 = member_2.status in ['member', 'administrator', 'creator']
        
        logger.info(f"✅ Channel membership check for user {user_id}: {CHANNEL_USERNAME}={is_member_1}, {CHANNEL_USERNAME_2}={is_member_2}")
        
        return {
            'uzbek_europe': is_member_1,
            'muslimbek_01': is_member_2,
            'both': is_member_1 and is_member_2
        }
    except Exception as e:
        logger.error(f"❌ Error checking channel membership: {e}")
        return {'uzbek_europe': False, 'muslimbek_01': False, 'both': False}


async def check_and_cleanup_user_referrals(referrer_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Check all referrals made BY a specific user and cleanup invalid ones"""
    from config import POINTS_FOR_REFERRAL, POINTS_FOR_JOINING
    
    try:
        # FIRST: Check if the REFERRER is still in both channels
        referrer_membership = await check_channel_membership_both(referrer_id, context)
        
        if not referrer_membership['both']:
            # Referrer left channels - invalidate ALL their referrals
            referrals = supabase.table('referrals') \
                .select('*') \
                .eq('referrer_id', referrer_id) \
                .eq('is_valid', True) \
                .execute()
            
            invalid_count = len(referrals.data)
            points_removed = 0
            
            for referral in referrals.data:
                referred_user_id = referral['referred_user_id']
                
                # Remove joining points from referred user
                result = supabase.table('activity_log') \
                    .delete() \
                    .eq('user_id', referred_user_id) \
                    .eq('activity_type', 'joining') \
                    .execute()
                
                if result.data:
                    points_removed += POINTS_FOR_JOINING
                
                # Remove referrer's points
                result = supabase.table('activity_log') \
                    .delete() \
                    .eq('user_id', referrer_id) \
                    .eq('activity_type', 'referral') \
                    .eq('post_id', referred_user_id) \
                    .execute()
                
                if result.data:
                    points_removed += POINTS_FOR_REFERRAL
                
                # Mark referral as invalid
                supabase.table('referrals') \
                    .update({'is_valid': False}) \
                    .eq('id', referral['id']) \
                    .execute()
            
            return {
                'total_checked': invalid_count,
                'valid_referrals': 0,
                'invalid_referrals': invalid_count,
                'rejoined_referrals': 0,
                'points_removed': points_removed,
                'points_restored': 0
            }
        
        # Get all referrals made BY this user
        referrals = supabase.table('referrals') \
            .select('*') \
            .eq('referrer_id', referrer_id) \
            .execute()
        
        if not referrals.data:
            return {
                'total_checked': 0,
                'valid_referrals': 0,
                'invalid_referrals': 0,
                'rejoined_referrals': 0,  # NEW
                'points_removed': 0,
                'points_restored': 0  # NEW
            }
        
        invalid_count = 0
        valid_count = 0
        rejoined_count = 0  # NEW
        points_removed = 0
        points_restored = 0  # NEW
        
        # Check each referral individually to avoid batch errors
        for referral in referrals.data:
            referred_user_id = referral['referred_user_id']
            referred_first_name = referral.get('referred_first_name', 'User')
            referrer_first_name = referral.get('referrer_first_name', 'User')
            is_currently_valid = referral.get('is_valid', True)
            
            try:
                # Check membership for this specific user
                membership = await check_channel_membership_both(referred_user_id, context)
            except Exception as e:
                logger.error(f"❌ Failed to check membership for user {referred_user_id}: {e}")
                # Skip this user if we can't check their membership
                continue
            
                    # Case 1: User LEFT channels (was valid, now invalid)
        if not membership['both'] and is_currently_valid:
            # Remove joining points from referred user
            result = supabase.table('activity_log') \
                .delete() \
                .eq('user_id', referred_user_id) \
                .eq('activity_type', 'joining') \
                .execute()
            
            joining_removed = len(result.data) if result.data else 0
            if joining_removed > 0:
                points_removed += POINTS_FOR_JOINING
                logger.info(f"💰 Removed {POINTS_FOR_JOINING} joining points from user {referred_user_id}")
            
            # Remove referrer's points for this specific referral
            result = supabase.table('activity_log') \
                .delete() \
                .eq('user_id', referrer_id) \
                .eq('activity_type', 'referral') \
                .eq('post_id', referred_user_id) \
                .execute()
            
            referral_removed = len(result.data) if result.data else 0
            if referral_removed > 0:
                points_removed += POINTS_FOR_REFERRAL
                logger.info(f"💰 Removed {POINTS_FOR_REFERRAL} referral points from user {referrer_id}")
            
            # Mark referral as invalid
            supabase.table('referrals') \
                .update({'is_valid': False}) \
                .eq('id', referral['id']) \
                .execute()
            
            invalid_count += 1
            logger.info(f"❌ Marked referral as invalid for user {referred_user_id}")
            
            # Notify referred user
            try:
                if not membership['uzbek_europe'] and not membership['muslimbek_01']:
                    message = (
                        f"⚠️ *Ogohlantirish\\!*\n\n"
                        f"Siz konkurs kanallaridan chiqib ketdingiz\\.\n\n"
                        f"❌ Sizning {POINTS_FOR_JOINING} ballingiz o'chirildi\\.\n\n"
                        f"💡 Qayta qo'shilish uchun:\n"
                        f"• @uzbek\\_europe\n"
                        f"• @muslimbek\\_01"
                    )
                elif not membership['uzbek_europe']:
                    message = (
                        f"⚠️ *Ogohlantirish\\!*\n\n"
                        f"Siz @uzbek\\_europe kanalidan chiqib ketdingiz\\.\n\n"
                        f"❌ Sizning {POINTS_FOR_JOINING} ballingiz o'chirildi\\.\n\n"
                        f"💡 Ballni qaytarish uchun kanalga qayta qo'shiling\\!"
                    )
                else:
                    message = (
                        f"⚠️ *Ogohlantirish\\!*\n\n"
                        f"Siz @muslimbek\\_01 kanalidan chiqib ketdingiz\\.\n\n"
                        f"❌ Sizning {POINTS_FOR_JOINING} ballingiz o'chirildi\\.\n\n"
                        f"💡 Ballni qaytarish uchun kanalga qayta qo'shiling\\!"
                    )
                
                await context.bot.send_message(
                    chat_id=referred_user_id,
                    text=message,
                    parse_mode=constants.ParseMode.MARKDOWN_V2
                )
                logger.info(f"✅ Notified referred user {referred_user_id}")
            except Exception as e:
                logger.error(f"❌ Failed to notify referred user {referred_user_id}: {e}")
            
            # Notify referrer
            try:
                referrer_message = (
                    f"⚠️ *Referal ogohlantirish\\!*\n\n"
                    f"Sizning referal foydalanuvchingiz "
                    f"\\({escape_markdown(referred_first_name, version=2)}\\) "
                    f"@Muslimbek\\_01 yoki @Uzbek\\_Europe kanallaridan chiqib ketdi\\.\n\n"
                    f"❌ Sizning {POINTS_FOR_REFERRAL} referal ballingiz o‘chirildi\\.\n\n"
                    f"💡 Agar ular qayta ushbu kanallarga qo‘shilsa\\, ball qaytariladi\\."
                )
                
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=referrer_message,
                    parse_mode=constants.ParseMode.MARKDOWN_V2
                )
                logger.info(f"✅ Notified referrer {referrer_id}")
            except Exception as e:
                logger.error(f"❌ Failed to notify referrer {referrer_id}: {e}")

        # Case 2: User REJOINED both channels (was invalid, now valid)
        elif membership['both'] and not is_currently_valid:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Restore joining points to referred user
            supabase.table('activity_log').insert({
                'user_id': referred_user_id,
                'username': referral.get('referred_username'),
                'first_name': referred_first_name,
                'activity_type': 'joining',
                'points': POINTS_FOR_JOINING,
                'timestamp': timestamp,
                'post_id': None,
                'post_timestamp': None,
                'channel_id': None
            }).execute()
            points_restored += POINTS_FOR_JOINING
            logger.info(f"💰 Restored {POINTS_FOR_JOINING} joining points to user {referred_user_id}")
            
            # Restore referrer's points
            supabase.table('activity_log').insert({
                'user_id': referrer_id,
                'username': referral.get('referrer_username'),
                'first_name': referrer_first_name,
                'activity_type': 'referral',
                'points': POINTS_FOR_REFERRAL,
                'timestamp': timestamp,
                'post_id': referred_user_id,
                'post_timestamp': None,
                'channel_id': None
            }).execute()
            points_restored += POINTS_FOR_REFERRAL
            logger.info(f"💰 Restored {POINTS_FOR_REFERRAL} referral points to user {referrer_id}")
            
            # Mark referral as valid again
            supabase.table('referrals') \
                .update({'is_valid': True}) \
                .eq('id', referral['id']) \
                .execute()
            
            rejoined_count += 1
            logger.info(f"✅ Marked referral as valid for user {referred_user_id}")
            
            # Notify referred user
            try:
                message = (
                    f"🎉 *Xush kelibsiz\\!*\n\n"
                    f"Siz kanallarimizga qayta qo'shildingiz\\!\n\n"
                    f"✅ Sizning {POINTS_FOR_JOINING} ballingiz qaytarildi\\!\n\n"
                    f"💡 Tanlovda davom eting\\!"
                )
                
                await context.bot.send_message(
                    chat_id=referred_user_id,
                    text=message,
                    parse_mode=constants.ParseMode.MARKDOWN_V2
                )
                logger.info(f"✅ Notified rejoined user {referred_user_id}")
            except Exception as e:
                logger.error(f"❌ Failed to notify rejoined user {referred_user_id}: {e}")
            
            # Notify referrer
            try:
                referrer_message = (
                    f"🎉 *Ajoyib yangilik\\!*\n\n"
                    f"Sizning referal foydalanuvchingiz \\({escape_markdown(referred_first_name, version=2)}\\) "
                    f"kanallarimizga qayta qo'shildi\\!\n\n"
                    f"✅ Sizning {POINTS_FOR_REFERRAL} referal ballingiz qaytarildi\\!\n\n"
                    f"🎯 Davom eting\\!"
                )
                
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=referrer_message,
                    parse_mode=constants.ParseMode.MARKDOWN_V2
                )
                logger.info(f"✅ Notified referrer about rejoin {referrer_id}")
            except Exception as e:
                logger.error(f"❌ Failed to notify referrer about rejoin {referrer_id}: {e}")

        # Case 3: User still valid (in both channels)
        elif membership['both'] and is_currently_valid:
            valid_count += 1
            logger.info(f"✅ User {referred_user_id} still valid in both channels")
        
        return {
            'total_checked': len(referrals.data),
            'valid_referrals': valid_count,
            'invalid_referrals': invalid_count,
            'rejoined_referrals': rejoined_count,  # NEW
            'points_removed': points_removed,
            'points_restored': points_restored  # NEW
        }
        
    except Exception as e:
        logger.error(f"❌ Error checking user referrals: {e}")
        return None