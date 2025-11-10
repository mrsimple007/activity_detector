import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


# Environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROUP_CHAT_ID = int(os.environ.get("GROUP_CHAT_ID_EU", "0"))

# GROUP_CHAT_ID = int(os.environ.get("GROUP_CHAT_ID", "0"))
# BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN_SIMPLELEARNINGUZ")

# ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "0"))
ADMIN_USER_ID_EU = int(os.environ.get("ADMIN_USER_ID_EU", "0"))
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Bot IDs to filter out
BOT_IDS_TO_REMOVE = [7967610894]

# Scoring System with time-based multipliers
POINTS_FOR_COMMENT_EARLY = 10  # Within 48 hours
POINTS_FOR_COMMENT_LATE = 3    # After 48 hours
POINTS_FOR_REACTION_EARLY = 3  # Within 48 hours
POINTS_FOR_REACTION_LATE = 1   # After 48 hours
EARLY_WINDOW_HOURS = 48

# Contest Settings
FIRST_COMMENT_POINTS = 15
SECOND_COMMENT_POINTS = 14
THIRD_COMMENT_POINTS = 13
OTHER_COMMENT_POINTS = 10


POINTS_FOR_REFERRAL = 5  # Points for successful referral
POINTS_FOR_JOINING = 3    # Points for joining via referral
CHANNEL_USERNAME = "uzbek_europe" 

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)