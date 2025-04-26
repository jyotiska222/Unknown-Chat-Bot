# chat_manager.py
import time
import json
import os
import threading
from collections import deque

waiting_users = deque()  # Changed to deque for efficient pop operations
active_chats = {}  # {user_id: partner_id}
user_stats = {}  # {user_id: {"connect_time": timestamp, "username": username, "partner": partner_id}}

def add_to_queue(user_id, username=None):
    if user_id not in waiting_users and user_id not in active_chats:
        waiting_users.append(user_id)
        user_stats[user_id] = {"username": username, "partner": None, "connect_time": time.time()}
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
    
    return {
        "waiting_users": waiting_count,
        "active_chats": active_count,
        "total_users": total_users,
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