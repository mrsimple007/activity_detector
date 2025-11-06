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
    display_name = f"@{username}" if username else first_name
    logger.info(f"📝 Logging activity for user: {display_name} (ID: {user_id})")
    logger.info(f"   Type: {activity_type}, Points: {points}, Post ID: {post_id}")
    
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
            'post_timestamp': post_timestamp.isoformat() if post_timestamp else None
        }
        
        logger.info(f"💾 Inserting into Supabase: {data}")
        supabase.table('activity_log').insert(data).execute()
        logger.info(f"✅ Successfully logged {activity_type} for {display_name} worth {points} points")
    except Exception as e:
        logger.error(f"❌ Error logging activity to Supabase: {e}")

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