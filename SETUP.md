# Setup Guide for Unknown Chat Bot

This document provides detailed setup instructions for the Unknown Chat Bot project.

## Quick Start (After Cloning Repository)

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Bot Token**:
   Open `config.py` and replace the placeholder with your Telegram bot token:
   ```python
   BOT_TOKEN = "your_bot_token_here"
   ```
   (You can get a token by talking to [@BotFather](https://t.me/BotFather) on Telegram)

3. **Configure your timezone** (optional, default is UTC):
   - Edit the `TIMEZONE` constant in `bot.py`, `chat_manager.py`, `chat_monitor.py`, and `heartbeat_monitor.py`
   - Example for Eastern Time:
   ```python
   TIMEZONE = pytz.timezone('America/New_York')
   ```

4. **Add Your Admin ID**:
   Open `bot.py` and add your Telegram user ID to the `ADMIN_IDS` list around line 28:
   ```python
   ADMIN_IDS = [your_user_id_here]  # Replace with your user ID
   ```
   (You can get your user ID by sending a message to [@userinfobot](https://t.me/userinfobot))
   
   Note: These admin IDs will also receive automatic notifications about bot health.

5. **Configure Heartbeat Monitoring** (optional):
   You can adjust the heartbeat monitoring settings in `bot.py`:
   ```python
   # Find this line in the main section:
   heartbeat_monitor.heartbeat_monitor = heartbeat_monitor.HeartbeatMonitor(ADMIN_IDS)
   
   # You can customize it with additional parameters:
   heartbeat_monitor.heartbeat_monitor = heartbeat_monitor.HeartbeatMonitor(
       ADMIN_IDS,
       check_interval=60,  # Check every 60 seconds (default)
       allowed_missed_beats=3  # Alert after 3 missed checks (default)
   )
   ```

6. **Create Chat Logs Directory**:
   ```bash
   mkdir chat_logs
   ```

7. **Run the Bot**:
   ```bash
   python bot.py
   ```
   - The bot should display startup information in the console
   - If running for the first time, user data JSON files will be created automatically

## Environment Setup

### Python Version Requirements

This bot is designed to work with Python 3.11.x (recommended). Python 3.11.9 has been tested and confirmed working.

1. **Install Python 3.11**:
   Download and install from [python.org](https://www.python.org/downloads/)

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Troubleshooting

### Common Issues

1. **Conflict Error: "terminated by other getUpdates request"**
   - This usually means another instance of the bot is already running
   - Check if you have multiple instances by running `ps aux | grep bot.py` (Linux/Mac) or check Task Manager (Windows)
   - Kill any existing bot processes before starting a new one

2. **Missing Modules**:
   - If you see errors about missing modules, check that all dependencies are installed:
     ```bash
     pip install -r requirements.txt --force-reinstall
     ```

3. **Telegram API Issues**:
   - If you experience connection issues to Telegram, ensure your internet connection is stable
   - Check that your bot token is valid and correctly configured in `config.py`

4. **Authentication Issues**:
   - Make sure your bot token is valid and hasn't been revoked
   - Try creating a new bot with [@BotFather](https://t.me/BotFather) if necessary

## Admin Dashboard Usage

The admin dashboard provides tools for monitoring and moderating chats:

```bash
python admin_dashboard.py --action summary
```

Available actions:
- `summary` - Show chat summary
- `view-chat` - View specific chat
- `list-dates` - List available log dates
- `search-media` - Search for media
- `search-user` - Search for user activity
- `flag-content` - Flag potentially inappropriate content

## Features

### User Matching

When a user starts a chat with the `/chat` command:

1. The bot will ask for their gender (Male, Female, or Other)
2. The bot will ask for their interest (Male, Female, or Other/Anyone)
3. This information is saved to their user profile
4. When they use `/chat` again in the future, their preferences will be remembered
5. New users are automatically asked for these preferences before being matched

Note: While the preferences are collected and stored, they do not affect the matching algorithm.

## Admin Commands (in Telegram)

Once your bot is running, you can use these admin commands on Telegram:

- `/ban <user_id> <duration_hours> [reason]` - Ban a user temporarily
- `/unban <user_id>` - Remove a ban from a user
- `/bannedlist` - List all currently banned users
- `/endchat <user_id> [reason]` - Forcefully end a chat
- `/broadcast <message>` - Send a message to all users
- `/bot_analysis` - Show detailed analysis of waiting users, active chats, and banned users with remaining ban times

### Admin Notifications

The bot includes an automatic admin notification system that alerts all users in the `ADMIN_IDS` list when:

1. **Unexpected Shutdown**: 
   - When the bot stops due to an error or external signal (not Ctrl+C)
   - Includes timestamp and error details/stack trace
   
2. **Unresponsive Bot**: 
   - When the bot is still running but hasn't processed any commands for a configurable period
   - Default is 3 missed heartbeat checks (configurable)
   - Ensures you're notified if the bot is running but frozen or unresponsive

Notification logs are saved to:
- `chat_monitor.log` - For regular bot activity
- `heartbeat_monitor.log` - For heartbeat activity and alerts

## Deployment Tips

For running the bot in production:

1. **Using systemd (Linux)**:
   Create a service file at `/etc/systemd/system/telegrambot.service`:
   ```
   [Unit]
   Description=Telegram Unknown Chat Bot
   After=network.target

   [Service]
   User=your_username
   WorkingDirectory=/path/to/Unknown-Chat-Bot
   ExecStart=/usr/bin/python3 bot.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

   Then enable and start the service:
   ```bash
   sudo systemctl enable telegrambot
   sudo systemctl start telegrambot
   ```

2. **Using screen/tmux**:
   ```bash
   screen -S telegrambot
   python bot.py
   # Press Ctrl+A then D to detach
   ```

   To reattach:
   ```bash
   screen -r telegrambot
   ```

3. **Running as a Windows service**:
   Use NSSM (Non-Sucking Service Manager) to create a Windows service. 