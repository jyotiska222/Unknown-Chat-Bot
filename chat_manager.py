# chat_manager.py
import time
import json
import os
import threading
import datetime
import pytz
from collections import deque

# Set timezone - use UTC for production environments for consistency
TIMEZONE = pytz.timezone('UTC')  # Change to your timezone if needed, e.g., 'America/New_York'

def get_localized_time():
    """Get current time in the specified timezone"""
    return datetime.datetime.now(TIMEZONE)

def datetime_to_timestamp(dt):
    """Convert datetime to timestamp for consistent storage"""
    return dt.timestamp()

waiting_users = deque()  # Changed to deque for efficient pop operations
active_chats = {}  # {user_id: partner_id}
user_stats = {}  # {user_id: {"connect_time": timestamp, "username": username, "partner": partner_id, "gender": gender, "interest": interest}}
banned_users = {}  # {user_id: {"until": timestamp, "reason": reason}}

def add_to_queue(user_id, username=None, gender=None, interest=None):
    # Check if user is banned
    if is_banned(user_id):
        return False
        
    if user_id not in waiting_users and user_id not in active_chats:
        waiting_users.append(user_id)
        
        # If user already exists in user_stats, update fields but don't overwrite existing ones
        if user_id in user_stats:
            user_stats[user_id]["partner"] = None
            user_stats[user_id]["connect_time"] = time.time()
            if username:
                user_stats[user_id]["username"] = username
            if gender is not None:
                user_stats[user_id]["gender"] = gender
            if interest is not None:
                user_stats[user_id]["interest"] = interest
        else:
            # Create new user entry
            user_stats[user_id] = {
                "username": username, 
                "partner": None, 
                "connect_time": time.time(),
                "gender": gender,
                "interest": interest
            }
        return True
    return False

def match_users():
    if len(waiting_users) >= 2:
        user1 = waiting_users.popleft()
        user2 = waiting_users.popleft()
        active_chats[user1] = user2
        active_chats[user2] = user1
        
        # Update stats
        user_stats[user1]["partner"] = user2
        user_stats[user2]["partner"] = user1
        user_stats[user1]["connect_time"] = time.time()
        user_stats[user2]["connect_time"] = time.time()
        
        return user1, user2
    return None, None

def get_partner(user_id):
    return active_chats.get(user_id)

def leave_chat(user_id):
    partner = active_chats.pop(user_id, None)
    if partner:
        active_chats.pop(partner, None)
        
        # Update stats
        if user_id in user_stats:
            user_stats[user_id]["partner"] = None
        if partner in user_stats:
            user_stats[partner]["partner"] = None
            
        return partner
    return None

def is_chatting(user_id):
    return user_id in active_chats

def get_stats():
    waiting_count = len(waiting_users)
    active_count = len(active_chats) // 2  # Divide by 2 because each chat has 2 entries
    total_users = len(user_stats)
    banned_count = len(banned_users)
    
    return {
        "waiting_users": waiting_count,
        "active_chats": active_count,
        "total_users": total_users,
        "banned_users": banned_count,
        "user_details": user_stats
    }

def remove_from_queue(user_id):
    if user_id in waiting_users:
        waiting_users.remove(user_id)
        return True
    return False

def save_users_to_file(filename="users.json"):
    """Save all known users to a file"""
    try:
        with open(filename, 'w') as f:
            # Convert user_ids to strings since JSON doesn't support integer keys
            serializable_stats = {str(uid): data for uid, data in user_stats.items()}
            json.dump(serializable_stats, f)
        return True
    except Exception as e:
        print(f"Error saving users to file: {e}")
        return False

def load_users_from_file(filename="users.json"):
    """Load known users from a file"""
    global user_stats
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                loaded_stats = json.load(f)
                # Convert keys back to integers and merge with existing stats
                for user_id_str, data in loaded_stats.items():
                    try:
                        user_id = int(user_id_str)
                        if user_id not in user_stats:
                            user_stats[user_id] = data
                    except ValueError:
                        # Skip entries with non-integer user IDs
                        continue
            return True
        except json.JSONDecodeError as e:
            print(f"Error decoding users file: {e}")
            return False
    return False

def auto_save_users(interval=300):  # Save every 5 minutes
    """Periodically save users to file"""
    save_users_to_file()
    # Schedule next save
    timer = threading.Timer(interval, auto_save_users, args=[interval])
    timer.daemon = True  # Make sure the thread doesn't block program exit
    timer.start()

# Ban functionality
def ban_user(user_id, duration_hours=24, reason="Violation of terms"):
    """
    Ban a user for a specified duration in hours
    Returns True if user was banned, False otherwise
    """
    if not user_id:
        return False
        
    # Remove from active chat if they're in one
    leave_chat(user_id)
    
    # Remove from waiting queue if they're in it
    remove_from_queue(user_id)
    
    # Set ban expiry time using timezone-aware datetime
    current_time = get_localized_time()
    ban_until = current_time + datetime.timedelta(hours=duration_hours)
    
    banned_users[user_id] = {
        "until": datetime_to_timestamp(ban_until),
        "reason": reason,
        "banned_at": datetime_to_timestamp(current_time)
    }
    
    # Save banned users to file
    save_banned_users()
    
    return True

def unban_user(user_id):
    """
    Unban a user
    Returns True if user was unbanned, False otherwise
    """
    if user_id in banned_users:
        del banned_users[user_id]
        save_banned_users()
        return True
    return False

def is_banned(user_id):
    """
    Check if a user is banned
    Returns ban info if banned, None otherwise
    """
    if user_id in banned_users:
        ban_info = banned_users[user_id]
        # Check if ban has expired using timezone-aware comparison
        current_time = datetime_to_timestamp(get_localized_time())
        if current_time > ban_info["until"]:
            unban_user(user_id)
            return None
        return ban_info
    return None

def get_banned_users():
    """Return a copy of the banned users dict"""
    # Clean up expired bans first
    current_time = datetime_to_timestamp(get_localized_time())
    expired_bans = [user_id for user_id, ban_info in banned_users.items() 
                    if current_time > ban_info["until"]]
    
    for user_id in expired_bans:
        unban_user(user_id)
        
    return banned_users.copy()

def save_banned_users(filename="banned_users.json"):
    """Save banned users to a file"""
    try:
        with open(filename, 'w') as f:
            # Convert user_ids to strings since JSON doesn't support integer keys
            serializable_bans = {str(uid): data for uid, data in banned_users.items()}
            json.dump(serializable_bans, f)
        return True
    except Exception as e:
        print(f"Error saving banned users to file: {e}")
        return False

def load_banned_users(filename="banned_users.json"):
    """Load banned users from a file"""
    global banned_users
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                loaded_bans = json.load(f)
                # Convert keys back to integers
                for user_id_str, data in loaded_bans.items():
                    try:
                        user_id = int(user_id_str)
                        banned_users[user_id] = data
                    except ValueError:
                        # Skip entries with non-integer user IDs
                        continue
                        
            # Clean up expired bans
            current_time = datetime_to_timestamp(get_localized_time())
            expired_bans = [user_id for user_id, ban_info in banned_users.items() 
                            if current_time > ban_info["until"]]
            
            for user_id in expired_bans:
                del banned_users[user_id]
                
            return True
        except json.JSONDecodeError as e:
            print(f"Error decoding banned users file: {e}")
            return False
    return False

def auto_save_banned_users(interval=300):  # Save every 5 minutes
    """Periodically save banned users to file"""
    save_banned_users()
    # Schedule next save
    timer = threading.Timer(interval, auto_save_banned_users, args=[interval])
    timer.daemon = True  # Make sure the thread doesn't block program exit
    timer.start()