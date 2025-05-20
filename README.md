# Unknown Chat Bot

A Telegram bot for anonymous chatting with strangers.

## Features

- Random chat matching
- Media and text messages support
- Admin moderation tools
- Chat monitoring and logging
- Admin notifications for bot health monitoring
- Comprehensive error logging and analysis

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

- `/bot_analysis` - Show detailed analysis of waiting users, active chats, and banned users

### Admin Error Management

- `/errors` - Show general error statistics and recent errors
- `/errors dates` - List all dates for which error logs are available
- `/errors YYYY-MM-DD` - Show summary of errors for a specific date
- `/errors YYYY-MM-DD detail` - Show detailed information about recent errors on that date

## Admin Notifications

The bot includes a health monitoring system that automatically notifies admins in these situations:

- When the bot stops unexpectedly due to an error or external signal
- When the bot becomes unresponsive (no activity detected for a configurable period)

This ensures administrators are quickly alerted to any issues so they can take corrective action.

## Error Logging System

The bot includes a comprehensive error logging system that:

- Records all errors with detailed information including stack traces
- Organizes errors by date in JSON format for easy analysis
- Tracks error statistics to identify recurring issues
- Provides in-bot commands for viewing and analyzing errors
- Maintains both a simple log file and structured JSON data
- Offers a decorator for easy error handling integration

## File Structure

- `bot.py` - Main bot code with command handlers
- `chat_manager.py` - Manages chats, users, and ban functionality
- `chat_monitor.py` - Logs chat activity
- `admin_dashboard.py` - Admin console for viewing logs
- `heartbeat_monitor.py` - Monitors bot health and sends admin alerts
- `error_logger.py` - Comprehensive error logging and analysis system
- `users.json` - Stores user data
- `banned_users.json` - Stores banned user data
- `chat_logs/` - Directory containing chat logs
- `logs/` - Directory containing structured error logs
- `error_logs.log` - Simple text log of all errors

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