import os
import json
import datetime
import argparse
from tabulate import tabulate
from typing import Dict, Any, List, Tuple

class ChatMonitorDashboard:
    """
    Admin dashboard to view chat logs and monitor user activity
    """
    def __init__(self, logs_dir: str = "chat_logs"):
        self.logs_dir = logs_dir
        self._check_logs_dir()
    
    def _check_logs_dir(self):
        """Verify the logs directory exists"""
        if not os.path.exists(self.logs_dir):
            print(f"Error: Log directory '{self.logs_dir}' does not exist.")
            exit(1)
    
    def _get_log_files(self) -> List[str]:
        """Get all log files sorted by date (newest first)"""
        files = [f for f in os.listdir(self.logs_dir) if f.startswith("chat_logs_") and f.endswith(".json")]
        # Sort by date in filename (format: chat_logs_YYYY-MM-DD.json)
        files.sort(reverse=True)
        return files
    
    def _read_logs(self, filename: str) -> Dict[str, Any]:
        """Read a specific log file"""
        filepath = os.path.join(self.logs_dir, filename)
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error reading log file {filename}: {e}")
            return {"created_at": "", "chats": {}}
    
    def list_log_dates(self):
        """List all available log dates"""
        files = self._get_log_files()
        if not files:
            print("No log files found.")
            return
        
        dates = [f.replace("chat_logs_", "").replace(".json", "") for f in files]
        
        print("\n=== Available Log Dates ===")
        for i, date in enumerate(dates, 1):
            print(f"{i}. {date}")
        print("")
    
    def show_summary(self, days: int = 1):
        """Show summary of recent chat activity"""
        files = self._get_log_files()[:days]  # Get only specified number of days
        
        if not files:
            print("No log files found.")
            return
        
        total_chats = 0
        total_messages = 0
        user_activity = {}  # {user_id: message_count}
        media_counts = {
            "text": 0, "photo": 0, "video": 0, "sticker": 0,
            "voice": 0, "document": 0, "audio": 0, "animation": 0,
            "video_note": 0
        }
        
        for file in files:
            logs = self._read_logs(file)
            date = file.replace("chat_logs_", "").replace(".json", "")
            
            chats_count = len(logs["chats"])
            messages_count = sum(len(chat.get("messages", [])) for chat in logs["chats"].values())
            
            total_chats += chats_count
            total_messages += messages_count
            
            # Count messages by type
            for chat in logs["chats"].values():
                for msg in chat.get("messages", []):
                    msg_type = msg.get("message_type", "text")
                    media_counts[msg_type] = media_counts.get(msg_type, 0) + 1
                    
                    # Track user activity
                    sender_id = msg.get("sender_id")
                    if sender_id:
                        user_activity[sender_id] = user_activity.get(sender_id, 0) + 1
            
            print(f"\n=== Summary for {date} ===")
            print(f"Total Chats: {chats_count}")
            print(f"Total Messages: {messages_count}")
        
        print("\n=== Overall Summary ===")
        print(f"Days analyzed: {len(files)}")
        print(f"Total Chats: {total_chats}")
        print(f"Total Messages: {total_messages}")
        
        print("\n=== Message Types ===")
        print(tabulate(
            [(msg_type.capitalize(), count, f"{count/total_messages*100:.1f}%") 
             for msg_type, count in media_counts.items() if count > 0],
            headers=["Type", "Count", "Percentage"],
            tablefmt="simple"
        ))
        
        print("\n=== Most Active Users ===")
        top_users = sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10]
        print(tabulate(
            [(user_id, count, f"{count/total_messages*100:.1f}%") for user_id, count in top_users],
            headers=["User ID", "Messages", "Percentage"],
            tablefmt="simple"
        ))
    
    def view_chat(self, chat_id: str = None, date: str = None):
        """View a specific chat's messages"""
        if date is None:
            # Use most recent log file
            files = self._get_log_files()
            if not files:
                print("No log files found.")
                return
            date_file = files[0]
        else:
            date_file = f"chat_logs_{date}.json"
            if not os.path.exists(os.path.join(self.logs_dir, date_file)):
                print(f"No logs found for date {date}")
                return
        
        logs = self._read_logs(date_file)
        
        if chat_id is None:
            # List all chats for the day
            print(f"\n=== Chats on {date_file.replace('chat_logs_', '').replace('.json', '')} ===")
            
            chat_list = []
            for cid, chat in logs["chats"].items():
                user1 = chat.get("users", [{}])[0].get("username", "Unknown")
                user2 = chat.get("users", [{}])[1].get("username", "Unknown") if len(chat.get("users", [])) > 1 else "Unknown"
                msg_count = len(chat.get("messages", []))
                chat_list.append((cid, f"{user1} & {user2}", msg_count))
            
            print(tabulate(
                chat_list,
                headers=["Chat ID", "Users", "Messages"],
                tablefmt="simple"
            ))
            
            # Prompt for chat selection
            selected_chat = input("\nEnter Chat ID to view (or press Enter to return): ")
            if not selected_chat:
                return
            chat_id = selected_chat
        
        # View the selected chat
        if chat_id not in logs["chats"]:
            print(f"Chat ID {chat_id} not found in logs.")
            return
        
        chat = logs["chats"][chat_id]
        user1 = chat.get("users", [{}])[0]
        user2 = chat.get("users", [{}])[1] if len(chat.get("users", [])) > 1 else {"id": "unknown", "username": "Unknown"}
        
        print(f"\n=== Chat between {user1.get('username', user1.get('id', 'Unknown'))} and {user2.get('username', user2.get('id', 'Unknown'))} ===")
        
        if chat.get("started_at"):
            print(f"Started: {chat['started_at']}")
        if chat.get("ended_at"):
            print(f"Ended: {chat['ended_at']} (Reason: {chat.get('end_reason', 'unknown')})")
        
        print("\n=== Messages ===")
        
        for i, msg in enumerate(chat.get("messages", []), 1):
            sender_id = msg.get("sender_id", "unknown")
            sender_name = msg.get("sender_username", sender_id)
            timestamp = msg.get("timestamp", "")
            msg_type = msg.get("message_type", "text")
            
            content = ""
            if msg_type == "text":
                content = msg.get("content", "")
            elif msg_type in ["photo", "video", "document", "voice", "audio", "animation", "video_note"]:
                media_url = msg.get("media_url", "No URL available")
                caption = msg.get("caption", "")
                content = f"[{msg_type.upper()}] URL: {media_url}"
                if caption:
                    content += f"\nCaption: {caption}"
            elif msg_type == "sticker":
                content = f"[STICKER]"
                if msg.get("media_url"):
                    content += f" URL: {msg.get('media_url')}"
            
            print(f"{i}. [{timestamp}] {sender_name}: {content}")
            if i < len(chat.get("messages", [])):
                print("---")
    
    def search_media(self, days: int = 7):
        """Search for media shared in chats"""
        files = self._get_log_files()[:days]
        
        if not files:
            print("No log files found.")
            return
        
        media_files = []
        
        for file in files:
            logs = self._read_logs(file)
            date = file.replace("chat_logs_", "").replace(".json", "")
            
            for chat_id, chat in logs["chats"].items():
                for msg in chat.get("messages", []):
                    if msg.get("message_type") in ["photo", "video", "document", "voice", "audio", "animation", "video_note"]:
                        if msg.get("media_url"):
                            media_files.append({
                                "date": date,
                                "chat_id": chat_id,
                                "sender": msg.get("sender_username", msg.get("sender_id", "Unknown")),
                                "type": msg.get("message_type"),
                                "url": msg.get("media_url"),
                                "caption": msg.get("caption", "")
                            })

        # Print media files
        print(f"\n=== Media Files (Last {days} days) ===")
        
        if not media_files:
            print("No media files found.")
            return
        
        print(tabulate(
            [(m["date"], m["sender"], m["type"], m["url"][:50] + "..." if len(m["url"]) > 50 else m["url"]) 
             for m in media_files],
            headers=["Date", "Sender", "Type", "URL"],
            tablefmt="simple"
        ))
        
        # Export option
        export = input("\nExport media list to CSV? (y/n): ").lower()
        if export == 'y':
            export_file = f"media_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(export_file, 'w') as f:
                f.write("date,chat_id,sender,type,url,caption\n")
                for m in media_files:
                    f.write(f"{m['date']},{m['chat_id']},{m['sender']},{m['type']},{m['url']},{m['caption']}\n")
            print(f"Exported to {export_file}")
    
    def search_user(self, user_id: str = None, username: str = None, days: int = 30):
        """Search for a user's activity"""
        if not user_id and not username:
            user_input = input("Enter user ID or username to search: ")
            if user_input.isdigit():
                user_id = user_input
            else:
                username = user_input
        
        files = self._get_log_files()[:days]
        
        if not files:
            print("No log files found.")
            return
        
        found = False
        user_chats = []
        messages_sent = 0
        media_sent = 0
        
        for file in files:
            logs = self._read_logs(file)
            date = file.replace("chat_logs_", "").replace(".json", "")
            
            for chat_id, chat in logs["chats"].items():
                # Check if user is in this chat
                user_in_chat = False
                found_user_id = None
                
                for user in chat.get("users", []):
                    if user_id and str(user.get("id", "")) == str(user_id):
                        user_in_chat = True
                        found_user_id = user.get("id")
                        found = True
                        break
                    elif username and username.lower() == str(user.get("username", "")).lower():
                        user_in_chat = True
                        found_user_id = user.get("id")
                        user_id = found_user_id  # Use this for subsequent searches
                        found = True
                        break
                
                if user_in_chat and found_user_id:
                    # Count messages
                    user_messages = 0
                    user_media = 0
                    
                    for msg in chat.get("messages", []):
                        if str(msg.get("sender_id", "")) == str(found_user_id):
                            user_messages += 1
                            if msg.get("message_type") != "text":
                                user_media += 1
                    
                    # Find partner in chat
                    partner = None
                    for user in chat.get("users", []):
                        if str(user.get("id", "")) != str(found_user_id):
                            partner = user.get("username", user.get("id", "Unknown"))
                            break
                    
                    started = chat.get("started_at", "Unknown")
                    ended = chat.get("ended_at", "Ongoing")
                    
                    user_chats.append({
                        "date": date,
                        "chat_id": chat_id,
                        "partner": partner,
                        "messages": user_messages,
                        "media": user_media,
                        "started": started,
                        "ended": ended
                    })
                    
                    messages_sent += user_messages
                    media_sent += user_media
        
        if not found:
            print(f"User {'ID: ' + user_id if user_id else 'username: ' + username} not found in the logs.")
            return
        
        # Print user activity summary
        print(f"\n=== Activity Summary for User {'ID: ' + user_id if user_id else 'username: ' + username} ===")
        print(f"Total Chats: {len(user_chats)}")
        print(f"Total Messages Sent: {messages_sent}")
        print(f"Media Files Sent: {media_sent}")
        
        # Print chat history
        print("\n=== Chat History ===")
        print(tabulate(
            [(c["date"], c["partner"], c["messages"], c["media"]) for c in user_chats],
            headers=["Date", "Partner", "Messages", "Media"],
            tablefmt="simple"
        ))
        
        # View specific chat option
        view_chat = input("\nView a specific chat? Enter date and chat ID (e.g. '2025-04-26 123_456') or press Enter to exit: ")
        if view_chat:
            try:
                date, chat_id = view_chat.split()
                self.view_chat(chat_id, date)
            except:
                print("Invalid format. Expected: 'YYYY-MM-DD chat_id'")
    
    def flag_inappropriate_content(self, days: int = 7):
        """
        Search for potentially inappropriate content based on keywords
        """
        # Keywords that might indicate inappropriate content
        keywords = [
            # "porn", "nude", "naked", "sex", "explicit", "illegal", "drugs", 
            "weapon", "abuse", "terrorist", "bomb", "kill", "threat"
        ]
        
        files = self._get_log_files()[:days]
        
        if not files:
            print("No log files found.")
            return
        
        flagged_messages = []
        
        for file in files:
            logs = self._read_logs(file)
            date = file.replace("chat_logs_", "").replace(".json", "")
            
            for chat_id, chat in logs["chats"].items():
                for msg in chat.get("messages", []):
                    content = msg.get("content", "").lower()
                    caption = msg.get("caption", "").lower()
                    
                    for keyword in keywords:
                        if keyword in content or keyword in caption:
                            flagged_messages.append({
                                "date": date,
                                "chat_id": chat_id,
                                "sender": msg.get("sender_username", msg.get("sender_id", "Unknown")),
                                "type": msg.get("message_type"),
                                "content": content if content else f"[{msg.get('message_type', 'unknown').upper()}]",
                                "keyword": keyword
                            })
        
        # Print flagged messages
        print(f"\n=== Flagged Content (Last {days} days) ===")
        
        if not flagged_messages:
            print("No flagged content found.")
            return
        
        print(tabulate(
            [(m["date"], m["sender"], m["type"], m["keyword"], m["content"][:50] + "..." if len(m["content"]) > 50 else m["content"]) 
             for m in flagged_messages],
            headers=["Date", "Sender", "Type", "Keyword", "Content"],
            tablefmt="simple"
        ))
        
        # Export option
        export = input("\nExport flagged content to CSV? (y/n): ").lower()
        if export == 'y':
            export_file = f"flagged_content_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(export_file, 'w') as f:
                f.write("date,chat_id,sender,type,keyword,content\n")
                for m in flagged_messages:
                    # Escape commas in content
                    content = f'"{m["content"]}"' if "," in m["content"] else m["content"]
                    f.write(f"{m['date']},{m['chat_id']},{m['sender']},{m['type']},{m['keyword']},{content}\n")
            print(f"Exported to {export_file}")


def main():
    parser = argparse.ArgumentParser(description="Chat Monitor Admin Dashboard")
    parser.add_argument("--logs-dir", default="chat_logs", help="Directory containing log files")
    parser.add_argument("--action", choices=["summary", "view-chat", "list-dates", "search-media", "search-user", "flag-content"], 
                        default="summary", help="Action to perform")
    parser.add_argument("--days", type=int, default=1, help="Number of days to analyze")
    parser.add_argument("--date", help="Specific date to analyze (YYYY-MM-DD)")
    parser.add_argument("--chat-id", help="Specific chat ID to view")
    parser.add_argument("--user-id", help="User ID to search")
    parser.add_argument("--username", help="Username to search")
    
    args = parser.parse_args()
    
    dashboard = ChatMonitorDashboard(args.logs_dir)
    
    if args.action == "summary":
        dashboard.show_summary(args.days)
    elif args.action == "view-chat":
        dashboard.view_chat(args.chat_id, args.date)
    elif args.action == "list-dates":
        dashboard.list_log_dates()
    elif args.action == "search-media":
        dashboard.search_media(args.days)
    elif args.action == "search-user":
        dashboard.search_user(args.user_id, args.username, args.days)
    elif args.action == "flag-content":
        dashboard.flag_inappropriate_content(args.days)

if __name__ == "__main__":
    main() 