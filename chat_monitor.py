import os
import json
import logging
import datetime
from typing import Optional, Dict, Any, List

# Configure logger for the monitor
monitor_logger = logging.getLogger(__name__)
monitor_logger.setLevel(logging.INFO)
if not monitor_logger.handlers:
    handler = logging.FileHandler("chat_monitor.log")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    monitor_logger.addHandler(handler)

class ChatMonitor:
    """
    Class to monitor and store chat messages for safety and moderation purposes.
    """
    def __init__(self, storage_dir: str = "chat_logs"):
        self.storage_dir = storage_dir
        self._ensure_storage_exists()
        self.current_day_file = None
        self.current_day = None
        self._initialize_day_file()
    
    def _ensure_storage_exists(self):
        """Create storage directory if it doesn't exist"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
            monitor_logger.info(f"Created chat logs directory: {self.storage_dir}")
    
    def _initialize_day_file(self):
        """Initialize the log file for the current day"""
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        if self.current_day != today:
            self.current_day = today
            self.current_day_file = os.path.join(self.storage_dir, f"chat_logs_{today}.json")
            
            # Check if file exists, if not create it with empty structure
            if not os.path.exists(self.current_day_file):
                with open(self.current_day_file, 'w') as f:
                    json.dump({
                        "created_at": datetime.datetime.now().isoformat(),
                        "chats": {}
                    }, f, indent=2)
                monitor_logger.info(f"Created new log file: {self.current_day_file}")
    
    def _read_logs(self) -> Dict[str, Any]:
        """Read the current day's logs"""
        self._initialize_day_file()  # Ensure we're using the right file
        try:
            with open(self.current_day_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # If file is corrupted or doesn't exist, create a new one
            log_data = {
                "created_at": datetime.datetime.now().isoformat(),
                "chats": {}
            }
            with open(self.current_day_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            return log_data
    
    def _write_logs(self, log_data: Dict[str, Any]):
        """Write logs back to file"""
        with open(self.current_day_file, 'w') as f:
            json.dump(log_data, f, indent=2)
    
    def log_message(self, 
                    user_id: int, 
                    partner_id: int, 
                    message_type: str, 
                    content: str, 
                    media_url: Optional[str] = None, 
                    caption: Optional[str] = None,
                    username: Optional[str] = None,
                    partner_username: Optional[str] = None):
        """
        Log a message between two users
        
        Args:
            user_id: ID of the sender
            partner_id: ID of the receiver
            message_type: Type of message (text, photo, video, etc.)
            content: Text content of the message
            media_url: URL of any media (if applicable)
            caption: Caption of media (if applicable)
            username: Username of sender (if available)
            partner_username: Username of receiver (if available)
        """
        # Generate a unique chat ID from the two user IDs (sorted to keep consistency)
        chat_id = f"{min(user_id, partner_id)}_{max(user_id, partner_id)}"
        
        timestamp = datetime.datetime.now().isoformat()
        
        message_data = {
            "timestamp": timestamp,
            "sender_id": user_id,
            "sender_username": username,
            "receiver_id": partner_id,
            "receiver_username": partner_username,
            "message_type": message_type,
            "content": content
        }
        
        # Add media data if available
        if media_url:
            message_data["media_url"] = media_url
        if caption:
            message_data["caption"] = caption
            
        try:
            log_data = self._read_logs()
            
            # Initialize chat entry if it doesn't exist
            if chat_id not in log_data["chats"]:
                log_data["chats"][chat_id] = {
                    "users": [
                        {"id": user_id, "username": username},
                        {"id": partner_id, "username": partner_username}
                    ],
                    "messages": []
                }
            
            # Add the message to the chat
            log_data["chats"][chat_id]["messages"].append(message_data)
            
            # Write back to file
            self._write_logs(log_data)
            
            monitor_logger.info(f"Logged {message_type} message from {user_id} to {partner_id}")
        except Exception as e:
            monitor_logger.error(f"Failed to log message: {e}")
    
    def log_chat_start(self, user1_id: int, user2_id: int, user1_name: Optional[str] = None, user2_name: Optional[str] = None):
        """Log when a chat is started between two users"""
        # Generate a unique chat ID from the two user IDs (sorted to keep consistency)
        chat_id = f"{min(user1_id, user2_id)}_{max(user1_id, user2_id)}"
        timestamp = datetime.datetime.now().isoformat()
        
        try:
            log_data = self._read_logs()
            
            # Initialize or update chat entry
            log_data["chats"][chat_id] = {
                "users": [
                    {"id": user1_id, "username": user1_name},
                    {"id": user2_id, "username": user2_name}
                ],
                "started_at": timestamp,
                "messages": []
            }
            
            # Write back to file
            self._write_logs(log_data)
            
            monitor_logger.info(f"Chat started between {user1_id} and {user2_id}")
        except Exception as e:
            monitor_logger.error(f"Failed to log chat start: {e}")
    
    def log_chat_end(self, user_id: int, partner_id: int, reason: str = "manual"):
        """Log when a chat ends"""
        # Generate a unique chat ID from the two user IDs (sorted to keep consistency)
        chat_id = f"{min(user_id, partner_id)}_{max(user_id, partner_id)}"
        timestamp = datetime.datetime.now().isoformat()
        
        try:
            log_data = self._read_logs()
            
            # Update chat entry if it exists
            if chat_id in log_data["chats"]:
                log_data["chats"][chat_id]["ended_at"] = timestamp
                log_data["chats"][chat_id]["end_reason"] = reason
                log_data["chats"][chat_id]["ended_by"] = user_id
                
                # Write back to file
                self._write_logs(log_data)
                
                monitor_logger.info(f"Chat ended between {user_id} and {partner_id}, reason: {reason}")
            else:
                monitor_logger.warning(f"Attempted to end non-existent chat between {user_id} and {partner_id}")
        except Exception as e:
            monitor_logger.error(f"Failed to log chat end: {e}")

    def get_recent_chats(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent chats"""
        try:
            log_data = self._read_logs()
            chats = list(log_data["chats"].values())
            
            # Sort by start time (most recent first)
            chats.sort(key=lambda x: x.get("started_at", ""), reverse=True)
            
            return chats[:limit]
        except Exception as e:
            monitor_logger.error(f"Failed to get recent chats: {e}")
            return []

# Create a singleton instance
chat_monitor = ChatMonitor() 