# Unknown Chat Bot

A Telegram bot for anonymous chatting with strangers.

## Features

- Random chat matching
- Media and text messages support
- Admin moderation tools
- Chat monitoring and logging

## Admin Commands

The bot includes several admin commands for moderating conversations and managing users:

### Admin User Management

- `/ban <user_id> <duration_hours> [reason]` - Ban a user for a specified duration in hours
  - Example: `/ban 123456789 24 Inappropriate behavior`
  - This will ban the user for 24 hours with the reason "Inappropriate behavior"

- `/unban <user_id>` - Remove a ban from a user
  - Example: `/unban 123456789`

- `/bannedlist` - Show all currently banned users with their ban details

### Admin Chat Management

- `/endchat <user_id> [reason]` - Forcefully end a chat between users
  - Example: `/endchat 123456789 Violation of terms`
  - This will end the chat for the specified user and their partner

- `/broadcast <message>` - Send a message to all users who have used the bot
  - Example: `/broadcast The bot will be down for maintenance from 10PM to 11PM`

## File Structure

- `bot.py` - Main bot code with command handlers
- `chat_manager.py` - Manages chats, users, and ban functionality
- `chat_monitor.py` - Logs chat activity
- `admin_dashboard.py` - Admin console for viewing logs
- `users.json` - Stores user data
- `banned_users.json` - Stores banned user data
- `chat_logs/` - Directory containing chat logs

## Setup

1. Install requirements: `pip install python-telegram-bot tabulate`
2. Set your bot token in `config.py`
3. Run the bot: `python bot.py`

## Admin Dashboard

Run the admin dashboard to view chat logs:

```bash
python admin_dashboard.py
```

Dashboard commands:
- `--action summary` - Show chat summary
- `--action view-chat` - View specific chat
- `--action list-dates` - List available log dates
- `--action search-media` - Search for media
- `--action search-user` - Search for user activity
- `--action flag-content` - Flag potentially inappropriate content 