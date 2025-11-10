import logging
from datetime import datetime, timedelta, timezone
from config import (
    supabase, 
    POINTS_FOR_COMMENT_EARLY, 
    POINTS_FOR_COMMENT_LATE,
    POINTS_FOR_REACTION_EARLY,
    POINTS_FOR_REACTION_LATE,
    EARLY_WINDOW_HOURS
)
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def calculate_points(activity_type: str, post_timestamp: datetime) -> int:
    """Calculate points based on activity type and time since post"""
    logger.info(f"📊 Calculating points for activity_type='{activity_type}'")
    
    now = datetime.now(timezone.utc)
    time_diff = now - post_timestamp
    hours_elapsed = time_diff.total_seconds() / 3600
    is_early = hours_elapsed < EARLY_WINDOW_HOURS
    
    logger.info(f"⏱️  Time since post: {hours_elapsed:.2f} hours (Early: {is_early})")
    
    if activity_type == 'comment':
        points = POINTS_FOR_COMMENT_EARLY if is_early else POINTS_FOR_COMMENT_LATE
        logger.info(f"💬 Comment points awarded: {points}")
        return points
    elif activity_type == 'reaction':
        points = POINTS_FOR_REACTION_EARLY if is_early else POINTS_FOR_REACTION_LATE
        logger.info(f"❤️  Reaction points awarded: {points}")
        return points
    
    logger.warning(f"⚠️  Unknown activity type: {activity_type}, returning 0 points")
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


def log_activity(user_id: int, username: str, first_name: str, activity_type: str, points: int, post_id: int = None, post_timestamp: datetime = None):
    """Log user activity to Supabase"""
    display_name = f"@{username}" if username else (first_name or f"User {user_id}")
    logger.info(f"📝 Logging activity for user: {display_name} (ID: {user_id})")
    logger.info(f"   Type: {activity_type}, Points: {points}, Post ID: {post_id}")
    
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # For referral activities, ensure we fetch the referrer's info from database
        if activity_type == 'referral' and (not username or not first_name):
            try:
                # Try to get user info from existing activity_log
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
            'post_id': post_id,
            'post_timestamp': post_timestamp.isoformat() if post_timestamp else None
        }
        
        logger.info(f"💾 Inserting into Supabase: {data}")
        result = supabase.table('activity_log').insert(data).execute()
        logger.info(f"✅ Successfully logged {activity_type} for {display_name} worth {points} points. Row ID: {result.data[0].get('id') if result.data else 'N/A'}")
    except Exception as e:
        logger.error(f"❌ Error logging activity to Supabase: {e}")
        logger.error(f"❌ Failed data: user_id={user_id}, activity_type={activity_type}, points={points}")

        
def get_leaderboard(days: int = None, limit: int = 20):
    """Get leaderboard from Supabase"""
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
            logger.info(f"📊 Top {len(sorted_users)} users selected for leaderboard")
        
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