# Save this file as import_history.py (Version 2)
import json
import sqlite3
import logging
from datetime import datetime

# --- Configuration ---
JSON_FILE_PATH = 'result.json'
DATABASE_FILE_PATH = 'activity.db'
POINTS_FOR_COMMENT = 5
POINTS_FOR_REACTION = 2


'''
How It Works:
Same post, multiple comments by same user: Only 5 points total

Different posts, comments by same user: 5 points per post

Reactions: Always 1 point each, no limits

Example Scenarios:
User comments 3 times on Post A → gets 5 points total

User comments on Post A and Post B → gets 10 points (5 + 5)

User reacts 5 times to different messages → gets 5 points

This ensures users are rewarded for engaging with different content rather than spamming the same post with multiple comments.

'''


# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- Database Functions ---
def setup_database():
    """Create the database and activity log table if they don't exist."""
    conn = sqlite3.connect(DATABASE_FILE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            activity_type TEXT NOT NULL,
            points INTEGER NOT NULL,
            timestamp DATETIME NOT NULL,
            post_id INTEGER
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database initialized with activity_log table.")


def log_activity(cursor, user_id_str, first_name, activity_type, points, timestamp_str, post_id=None):
    """
    Log a single activity. Now handles non-user IDs by skipping them.
    """
    # Check if the ID is from a user. If not (e.g., 'channel...'), skip it.
    if not user_id_str.startswith('user'):
        return

    try:
        numeric_user_id = int(user_id_str.replace('user', ''))
        username = None  # Username is not in the export, the live bot will add it later.
        timestamp = datetime.fromisoformat(timestamp_str)

        cursor.execute(
            "INSERT INTO activity_log (user_id, username, first_name, activity_type, points, timestamp, post_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (numeric_user_id, username, first_name, activity_type, points, timestamp, post_id)
        )
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not process activity for ID '{user_id_str}': {e}")


# --- Main Importer Logic ---
def run_import():
    """Reads the JSON export and populates the database."""
    setup_database()

    logger.info(f"Opening JSON file: {JSON_FILE_PATH}")
    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Error: The file '{JSON_FILE_PATH}' was not found in this directory.")
        return

    messages = data.get('messages', [])
    if not messages:
        logger.error("No messages found in the JSON file. Was it exported correctly?")
        return

    total_messages = len(messages)
    logger.info(f"Found {total_messages} messages to process.")

    conn = sqlite3.connect(DATABASE_FILE_PATH)
    cursor = conn.cursor()

    try:
        # Track which users have already commented on which posts
        # Structure: {post_id: {user_id1, user_id2, ...}}
        post_comments = {}

        for i, msg in enumerate(messages):
            if msg.get('type') == 'message':
                from_user = msg.get('from')
                from_id = msg.get('from_id')
                timestamp = msg.get('date')
                message_id = msg.get('id')

                # Determine post_id for comment deduplication
                # Use reply_to_message_id if this is a reply, otherwise use the message's own ID
                post_id = msg.get('reply_to_message_id', message_id)

                # Log the Comment activity (if it's from a user)
                if from_user and from_id and from_id.startswith('user'):
                    user_id_str = from_id
                    numeric_user_id = int(user_id_str.replace('user', ''))

                    # Check if this user has already commented on this post
                    if post_id not in post_comments:
                        post_comments[post_id] = set()

                    if numeric_user_id not in post_comments[post_id]:
                        # First comment by this user on this post - award points
                        log_activity(cursor, from_id, from_user, 'comment', POINTS_FOR_COMMENT, timestamp, post_id)
                        post_comments[post_id].add(numeric_user_id)
                    else:
                        # User already commented on this post - no points awarded
                        logger.debug(f"User {numeric_user_id} already commented on post {post_id}, skipping points")

                # Log the Reaction activity (reactions are always counted, no deduplication needed)
                reactions = msg.get('reactions')
                if reactions:
                    for reaction in reactions:
                        peers = reaction.get('peers', [])
                        for peer in peers:
                            peer_id = peer.get('id')
                            peer_name = peer.get('name')
                            # Reactions always have a timestamp from the original message
                            if peer_id and peer_name and peer_id.startswith('user'):
                                log_activity(cursor, peer_id, peer_name, 'reaction', POINTS_FOR_REACTION, timestamp)

            if (i + 1) % 500 == 0:
                logger.info(f"Processed {i + 1}/{total_messages} messages...")

        conn.commit()

        # Log statistics about the import
        total_comments_awarded = sum(len(users) for users in post_comments.values())
        logger.info(f"Successfully imported historical activity from {total_messages} messages!")
        logger.info(f"Total comments awarded points: {total_comments_awarded}")
        logger.info(f"Unique posts with comments: {len(post_comments)}")

    except Exception as e:
        conn.rollback()
        logger.error(f"A critical error occurred during import: {e}", exc_info=True)
    finally:
        conn.close()


if __name__ == '__main__':
    confirm = input("This script will add historical data to 'activity.db'.\n"
                    "It's highly recommended to DELETE the old 'activity.db' file before running.\n"
                    "Are you sure you want to continue? (y/n): ")
    if confirm.lower() == 'y':
        run_import()
    else:
        print("Import cancelled.")