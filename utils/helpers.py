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

logger = logging.getLogger(__name__)


def calculate_points(activity_type: str, post_timestamp: datetime) -> int:
    """Calculate points based on activity type and time since post"""
    from config import (
        POINTS_FOR_REACTION_EARLY, 
        POINTS_FOR_REACTION_LATE,
        EARLY_WINDOW_HOURS
    )
    
    logger.info(f"📊 Calculating points for activity_type='{activity_type}'")
    
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
    """Check if user has already commented on this post"""
    logger.info(f"🔍 Checking if user {user_id} already commented on post {post_id}")
    
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
    """Log user activity to Supabase with channel tracking"""
    display_name = f"@{username}" if username else (first_name or f"User {user_id}")
    logger.info(f"📝 Logging activity for user: {display_name} (ID: {user_id})")
    logger.info(f"   Type: {activity_type}, Points: {points}, Post ID: {post_id}, Channel: {channel_id}")
    
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if activity_type == 'referral' and (not username or not first_name):
            try:
                existing_user = supabase.table('activity_log').select('username, first_name').eq('user_id', user_id).limit(1).execute()
                if existing_user.data:
                    username = existing_user.data[0].get('username') or username
                    first_name = existing_user.data[0].get('first_name') or first_name
                    logger.info(f"📋 Retrieved existing user info: username={username}, first_name={first_name}")
            except Exception as e:
                logger.warning(f"⚠️ Could not retrieve existing user info: {e}")
        
        data = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'activity_type': activity_type,
            'points': points,
            'timestamp': timestamp,
            'post_id': post_id,  # This should be None for boost activities
            'post_timestamp': post_timestamp.isoformat() if post_timestamp else None,
            'channel_id': channel_id
        }
        
        logger.info(f"💾 Inserting into Supabase: {data}")
        result = supabase.table('activity_log').insert(data).execute()
        logger.info(f"✅ Successfully logged {activity_type} for {display_name} worth {points} points. Row ID: {result.data[0].get('id') if result.data else 'N/A'}")
    except Exception as e:
        logger.error(f"❌ Error logging activity to Supabase: {e}")
        logger.error(f"❌ Failed data: user_id={user_id}, activity_type={activity_type}, points={points}")

        
def get_leaderboard(days: int = None, limit: int = 20):
    """Get leaderboard from Supabase - quiz points now included in activity_log"""
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
        
        # No more separate quiz point calculation - it's already in activity_log!
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
    """Log referral to database"""
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        data = {
            'referrer_id': referrer_id,
            'referred_user_id': referred_user_id,
            'referred_username': referred_username,
            'referred_first_name': referred_first_name,
            'timestamp': timestamp
        }
        supabase.table('referrals').insert(data).execute()
        logger.info(f"✅ Referral logged: {referrer_id} -> {referred_user_id}")
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
        logger.info(f"📊 Referrer {referrer_id} has {count} referrals")
        return count
    except Exception as e:
        logger.error(f"❌ Error getting referral count: {e}")
        return 0


def save_user_to_db(user_id: int, username: str, first_name: str, last_name: str = None):
    """Save or update user in uzbek_europe_users table"""
    logger.info(f"💾 Saving user {user_id} to uzbek_europe_users table")
    
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
        
        logger.info(f"✅ User {user_id} saved successfully to uzbek_europe_users")
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
            },
            CHANNEL_ID_MUSLIMBEK: {
                'comment_points': 0,
                'reaction_points': 0,
                'boost_points': 0,
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
        
        # Get referral count
        referral_result = supabase.table('referrals').select('id').eq('referrer_id', user_id).execute()
        referral_count = len(referral_result.data)
        
        # Get user position - USE 30 DAYS for consistency with leaderboard
        all_users = get_leaderboard(days=30, limit=None)
        
        # Filter admins
        filtered_users = [u for u in all_users if u.get('user_id') not in [ADMIN_USER_ID, ADMIN_USER_ID_EU, ADMIN_USER_ID_EU_2]]
        
        user_position = None
        for idx, user_data in enumerate(filtered_users):
            if user_data.get('user_id') == user_id:
                user_position = idx + 1
                break
        
        # If user not found in leaderboard (no activity in last 30 days), position is last
        if user_position is None:
            user_position = len(filtered_users) + 1
        
        return {
            'username': username,
            'first_name': first_name,
            'total_points': total_points,
            'referral_points': referral_points,
            'quiz_points': quiz_points,
            'referral_count': referral_count,
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
            logger.info(f"⏳ User {user_id} is rate limited for {activity_type}")
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
            logger.info(f"🚫 User {user_id} reached daily limit for {activity_type} in {channel_id}")
            return True, 0
        
        # Adjust points if would exceed limit
        adjusted_points = min(points, max_points - total_today)
        return False, adjusted_points
        
    except Exception as e:
        logger.error(f"Error checking daily limit: {e}")
        return False, points