import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


# Environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN_ACTIVITY")
# BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN_SIMPLELEARNINGUZ")
# BOT_TOKEN_WT = os.environ.get("TELEGRAM_BOT_TOKEN_WT")

GROUP_CHAT_ID = int(os.environ.get("GROUP_CHAT_ID_EU", "0"))
GROUP_CHAT_ID_2 = int(os.environ.get("GROUP_CHAT_ID_Muslimbek", "0"))
CHANNEL_USERNAME = "uzbek_europe" 
CHANNEL_USERNAME_2 = "muslimbek_01" 
# Channel identifiers for database
CHANNEL_ID_UZBEK_EUROPE = "uzbek_europe"
CHANNEL_ID_MUSLIMBEK = "muslimbek_01"




PRIVATE_CHANNEL_LINK = os.environ.get("PRIVATE_CHANNEL_LINK", "")

ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "0"))
ADMIN_USER_ID_EU = int(os.environ.get("ADMIN_USER_ID_EU", "0"))
ADMIN_USER_ID_EU_2= int(os.environ.get("ADMIN_USER_ID_EU_2", "0"))
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Bot IDs to filter out
BOT_IDS_TO_REMOVE = [7967610894, 8437026582, 122290051, 999932510]

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


COOLDOWN_SECONDS = {
    'comment': 30,      # 30 seconds between comments
    'reaction': 5,      # 5 seconds between reactions
}


MAX_DAILY_POINTS = {
    'comment': 50,      # Max 50 points from comments per day
    'reaction': 20,     # Max 20 points from reactions per day
}
    


POINTS_FOR_BOOSTING=20

POINTS_FOR_REFERRAL = 5  # Points for successful referral
POINTS_FOR_JOINING = 3    # Points for joining via referral

MAX_REFERRALS_FOR_POINTS = 200
POINTS_FOR_QUIZ = 1 


# Existing activity tracker Supabase
ACTIVITY_SUPABASE_URL = os.getenv("ACTIVITY_SUPABASE_URL")
ACTIVITY_SUPABASE_KEY = os.getenv("ACTIVITY_SUPABASE_KEY")
supabase = create_client(ACTIVITY_SUPABASE_URL, ACTIVITY_SUPABASE_KEY)

# Quiz bot Supabase
QUIZ_SUPABASE_URL = os.getenv("QUIZ_SUPABASE_URL")
QUIZ_SUPABASE_KEY = os.getenv("QUIZ_SUPABASE_KEY")
quiz_supabase = create_client(QUIZ_SUPABASE_URL, QUIZ_SUPABASE_KEY)

