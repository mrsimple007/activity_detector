import asyncio
from telegram import Bot
from telegram.error import TelegramError
import aiohttp
from dotenv import load_dotenv
import os
import logging
from datetime import datetime

load_dotenv(dotenv_path=".env")
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Import from config
from config import (
    BOT_TOKEN,
    supabase,
    ADMIN_USER_ID,
    ADMIN_USER_ID_EU,
    ADMIN_USER_ID_EU_2
)

MAX_CONCURRENT = 30
BATCH_SIZE = 100
DELAY = 1.0

def fetch_users():
    """Fetch all users from uzbek_europe_users table"""
    try:
        response = supabase.table("uzbek_europe_users").select("user_id, first_name, username").execute()
        users = []
        for row in response.data:
            users.append({
                "id": row["user_id"],
                "name": row["first_name"] or "Do'st",
                "username": row.get("username")
            })
        logger.info(f"✅ Fetched {len(users)} users from database")
        return users
    except Exception as e:
        logger.error(f"❌ Error fetching users: {e}")
        return []

def escape_markdown_v2(text):
    """Escape special characters for MarkdownV2"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def generate_message(name):
    """Generate referral check warning message"""
    escaped_name = escape_markdown_v2(name)

    return (
        f"Assalomu alaykum, {escaped_name}\\! 👋\n\n"
        "⚠️ *Muhim eʼlon*\n\n"
        "Soʻnggi paytlarda ayrim foydalanuvchilar *referal ballarni olgandan soʻng* "
        "kanaldan chiqib ketish holatlari kuzatilmoqda\\.\n\n"
        "Shu sababli bugundan boshlab *referal tizimi qatʼiy tekshiriladi* 🔍\n\n"
        "📌 *Eʼtibor bering:*\n"
        "— Agar siz taklif qilgan foydalanuvchi kanallarimizda *qolmagan bo‘lsa*,\n"
        "— unga berilgan referal ballar *avtomatik ravishda kamaytiriladi* ❌\n\n"
        "✅ Referal ballar faqatgina taklif qilingan foydalanuvchi "
        "*kanalga aʼzo bo‘lib turgan taqdirda* saqlanadi\\.\n\n"
        "📢 Iltimos, referallaringizga kanallarda "
        "\\(@Muslimbek\\_01 va @Uzbek\\_Europe\\) "
        "*doimiy aʼzo bo‘lib qolishlarini* eslatib qo‘ying\\.\n\n"
        "Bu choralar konkursda *halollik va adolatni* saqlash uchun joriy qilindi 🤝\n\n"
        "Tushunganingiz uchun rahmat\\! 🚀"
    )



async def send_message_safe(session, bot_token, chat_id, message):
    """Send a single message with error handling"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'MarkdownV2',
        'disable_web_page_preview': True
    }
    
    try:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                return {"success": True, "chat_id": chat_id}
            else:
                error_text = await response.text()
                logger.warning(f"⚠️ Failed to send to {chat_id}: {error_text}")
                return {"success": False, "chat_id": chat_id, "error": error_text}
    except Exception as e:
        logger.error(f"❌ Exception sending to {chat_id}: {e}")
        return {"success": False, "chat_id": chat_id, "error": str(e)}

async def send_batch(batch, bot_token):
    """Send messages to a batch of users"""
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = []
        for user in batch:
            message = generate_message(user["name"])
            task = send_message_safe(session, bot_token, user["id"], message)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

async def send_to_all_users():
    """Send broadcast message to all users"""
    users = fetch_users()
    
    if not users:
        print("❌ No users found")
        return
    
    print(f"\n{'='*60}")
    print(f"📢 STARTING BROADCAST TO {len(users)} USERS")
    print(f"{'='*60}\n")
    
    successful = 0
    failed = 0
    
    start_time = datetime.now()
    
    for i in range(0, len(users), BATCH_SIZE):
        batch = users[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(users) + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} users)...")
        
        try:
            results = await send_batch(batch, BOT_TOKEN)
            
            for result in results:
                if isinstance(result, Exception):
                    failed += 1
                    logger.error(f"Exception in result: {result}")
                    continue
                
                if result["success"]:
                    successful += 1
                else:
                    failed += 1
            
            print(f"✅ Batch {batch_num} complete: {successful} sent, {failed} failed (total so far)")
            
            # Sleep between batches to avoid rate limits
            if i + BATCH_SIZE < len(users):
                await asyncio.sleep(DELAY)
                
        except Exception as e:
            logger.error(f"❌ Error in batch {batch_num}: {e}")
            failed += len(batch)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n{'='*60}")
    print(f"📊 BROADCAST COMPLETED")
    print(f"{'='*60}")
    print(f"✅ Successfully sent: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"⏱️  Duration: {duration:.2f} seconds")
    print(f"{'='*60}\n")

async def send_test_message(user_id):
    """Send test message to a specific user"""
    bot = Bot(token=BOT_TOKEN)
    
    users = fetch_users()
    user = next((u for u in users if u["id"] == user_id), None)
    
    if not user:
        name = "Do'st"
    else:
        name = user["name"]
    
    message = generate_message(name)
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode='MarkdownV2',
            disable_web_page_preview=True
        )
        print(f"✅ Test message sent successfully to {user_id}")
    except TelegramError as e:
        print(f"❌ Failed to send test message: {e}")

async def main():
    users = fetch_users()
    
    print("\n" + "="*60)
    print("🤖 ACTIVITY BOT BROADCAST SYSTEM")
    print("="*60)
    print(f"📊 Total users in database: {len(users)}")
    print("="*60)
    
    print("\n📋 What would you like to do?")
    print("1. Send broadcast to ALL users")
    print("2. Send test message to specific user")
    print("3. Send test message to admin")
    print("4. Exit")
    
    choice = input("\n👉 Enter your choice (1-4): ").strip()
    
    if choice == "1":
        print(f"\n⚠️  WARNING: You are about to send a message to {len(users)} users!")
        confirm = input("Type 'YES' to confirm: ").strip()
        if confirm == "YES":
            print("\n🚀 Starting broadcast...")
            await send_to_all_users()
        else:
            print("❌ Broadcast cancelled")
    
    elif choice == "2":
        test_user_id = input("\n👉 Enter user ID: ").strip()
        try:
            test_user_id = int(test_user_id)
            await send_test_message(test_user_id)
        except ValueError:
            print("❌ Invalid user ID format")
    
    elif choice == "3":
        admin_ids = [ADMIN_USER_ID, ADMIN_USER_ID_EU, ADMIN_USER_ID_EU_2]
        print(f"\n📋 Available admin IDs: {admin_ids}")
        
        admin_choice = input("👉 Enter admin number (1-3) or specific ID: ").strip()
        
        try:
            if admin_choice in ["1", "2", "3"]:
                admin_id = admin_ids[int(admin_choice) - 1]
            else:
                admin_id = int(admin_choice)
            
            await send_test_message(admin_id)
        except (ValueError, IndexError):
            print("❌ Invalid admin selection")
    
    elif choice == "4":
        print("\n👋 Goodbye!")
    
    else:
        print("\n❌ Invalid choice")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Broadcast interrupted by user")
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        logger.error(f"Main error: {e}", exc_info=True)
