import logging
import os
import asyncio
from datetime import datetime, timezone
from supabase import create_client
from telegram import Bot
from telegram.error import TelegramError, Forbidden, BadRequest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SUPABASE_URL = os.environ.get("QUIZ_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("QUIZ_SUPABASE_KEY")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN_SIMPLELEARNINGUZ") 

# Verify environment variables are loaded
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE credentials. Check your .env file!")
if not BOT_TOKEN:
    raise ValueError("Missing BOT_TOKEN. Check your .env file!")

logger.info(f"✅ Loaded SUPABASE_URL: {SUPABASE_URL[:20]}...")
logger.info(f"✅ Loaded BOT_TOKEN: {BOT_TOKEN[:20]}...")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

REQUIRED_CHANNELS = [
    '@SimpleLearnUz',
    '@uzbek_europe',
    '@Muslimbek_01'
]

PENALTY_AMOUNT = 300000  # 3,000 UZS in kopecks (3000 * 100)
CUTOFF_DATE = datetime(2024, 11, 7, tzinfo=timezone.utc)

async def check_channel_membership(bot: Bot, user_id: int) -> bool:
    """Check if user is in at least one required channel"""
    for channel_id in REQUIRED_CHANNELS:
        try:
            chat_member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            
            # If user is a member of any channel, return True
            if chat_member.status not in ['left', 'kicked']:
                logger.info(f"✅ User {user_id} is still in {channel_id}")
                return True
                
        except (Forbidden, BadRequest) as e:
            logger.debug(f"User {user_id} not accessible in {channel_id}: {e}")
            continue
        except TelegramError as e:
            logger.error(f"Telegram error checking {user_id} in {channel_id}: {e}")
            continue
    
    logger.warning(f"❌ User {user_id} is NOT in any required channel")
    return False

async def get_referrals_after_date(inviter_id: int):
    """Get all referrals for a user after the cutoff date"""
    try:
        response = supabase.table('simplequizzer_users') \
            .select('user_id, created_at') \
            .eq('invited_by', str(inviter_id)) \
            .gte('created_at', CUTOFF_DATE.isoformat()) \
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error getting referrals for user {inviter_id}: {e}")
        return []

async def update_user_balance(user_id: int, penalty: int):
    """Deduct penalty from user balance"""
    try:
        # Get current balance
        response = supabase.table('simplequizzer_users') \
            .select('balance') \
            .eq('user_id', str(user_id)) \
            .execute()
        
        if not response.data:
            logger.error(f"User {user_id} not found")
            return False
        
        current_balance = response.data[0].get('balance', 0)
        new_balance = current_balance - penalty
        
        # Update balance (can go negative)
        supabase.table('simplequizzer_users') \
            .update({'balance': new_balance}) \
            .eq('user_id', str(user_id)) \
            .execute()
        
        logger.info(f"💰 User {user_id}: {current_balance} → {new_balance} (-{penalty})")
        return True
        
    except Exception as e:
        logger.error(f"Error updating balance for user {user_id}: {e}")
        return False

async def check_and_fix_referrals():
    """Main function to check all users and fix balances"""
    bot = Bot(token=BOT_TOKEN)
    
    # Get all users who have invited someone after Nov 7
    try:
        response = supabase.table('simplequizzer_users') \
            .select('user_id') \
            .not_.is_('invited_by', 'null') \
            .execute()
        
        # Get unique inviters
        all_users = response.data if response.data else []
        inviters = set()
        
        for user in all_users:
            invited_by = user.get('invited_by')
            if invited_by:
                inviters.add(int(invited_by))
        
        logger.info(f"📊 Found {len(inviters)} users who have invited others")
        
        total_penalties = 0
        total_users_penalized = 0
        
        for inviter_id in inviters:
            logger.info(f"\n🔍 Checking inviter: {inviter_id}")
            
            # Get their referrals after Nov 7
            referrals = await get_referrals_after_date(inviter_id)
            
            if not referrals:
                logger.info(f"   No referrals after {CUTOFF_DATE.date()}")
                continue
            
            logger.info(f"   Found {len(referrals)} referrals after {CUTOFF_DATE.date()}")
            
            invalid_referrals = 0
            
            # Check each referral
            for referral in referrals:
                referral_user_id = int(referral['user_id'])
                
                # Check if referral is still in at least one channel
                is_still_member = await check_channel_membership(bot, referral_user_id)
                
                if not is_still_member:
                    invalid_referrals += 1
                    logger.warning(f"   ⚠️  Referral {referral_user_id} left all channels!")
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
            
            # Apply penalties if there are invalid referrals
            if invalid_referrals > 0:
                total_penalty = invalid_referrals * PENALTY_AMOUNT
                logger.warning(f"   💸 Penalizing user {inviter_id}: {invalid_referrals} invalid referrals × {PENALTY_AMOUNT} = {total_penalty}")
                
                success = await update_user_balance(inviter_id, total_penalty)
                
                if success:
                    total_penalties += total_penalty
                    total_users_penalized += 1
        
        logger.info(f"\n✅ SUMMARY:")
        logger.info(f"   Total users penalized: {total_users_penalized}")
        logger.info(f"   Total penalties applied: {total_penalties} kopecks ({total_penalties / 100} UZS)")
        
    except Exception as e:
        logger.error(f"Error in main check: {e}")
    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(check_and_fix_referrals())