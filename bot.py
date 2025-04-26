# bot.py
import logging
import asyncio
import signal
import threading
import time
import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes,
    CallbackContext
)
from telegram.error import TelegramError, Conflict
from config import BOT_TOKEN
import chat_manager  # Import chat_manager module
from chat_monitor import chat_monitor  # Import the chat monitor

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Admin IDs who are allowed to use broadcast
ADMIN_IDS = [2023022792]  # Admin user ID

# Initialize the app without session_name
app = ApplicationBuilder().token(BOT_TOKEN).build()

# To track start time
start_time = None

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Register or update user in user_stats
    if user_id not in chat_manager.user_stats:
        chat_manager.user_stats[user_id] = {"username": username, "partner": None, "connect_time": time.time()}
    else:
        chat_manager.user_stats[user_id]["username"] = username
    
    await update.message.reply_text(
        "Welcome to Unknown Chat Bot! 👋\n\n"
        "Commands:\n"
        "/chat - Find a random stranger to chat with\n"
        "/leave - Leave current chat\n"
        "/status - Check if you're in a chat\n\n"
        "You can send text, photos, videos, stickers, and video messages!"
    )

# /chat command
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Leave current chat if exists
    if chat_manager.is_chatting(user_id):
        partner = chat_manager.leave_chat(user_id)
        if partner:
            try:
                await context.bot.send_message(partner, "🚫 The stranger left the chat.")
                # Log chat end
                chat_monitor.log_chat_end(user_id, partner, reason="started_new")
            except TelegramError as e:
                logger.error(f"Failed to notify partner {partner}: {e}")
    
    # Remove from waiting queue if already in it
    chat_manager.remove_from_queue(user_id)
    
    # Add to queue
    chat_manager.add_to_queue(user_id, username)
    
    user1, user2 = chat_manager.match_users()
    if user1 and user2:
        try:
            await context.bot.send_message(user1, "🎉 Connected to a stranger. Say hi!")
            await context.bot.send_message(user2, "🎉 Connected to a stranger. Say hi!")
            
            # Get usernames
            user1_name = chat_manager.user_stats[user1].get("username", "Unknown")
            user2_name = chat_manager.user_stats[user2].get("username", "Unknown")
            
            # Log chat start
            chat_monitor.log_chat_start(user1, user2, user1_name, user2_name)
            
            logger.info(f"Matched users: {user1} with {user2}")
        except TelegramError as e:
            logger.error(f"Failed to notify matched users: {e}")
            # If we failed to notify, undo the match
            chat_manager.leave_chat(user1)
            chat_manager.add_to_queue(user1, chat_manager.user_stats[user1].get("username"))
            chat_manager.add_to_queue(user2, chat_manager.user_stats[user2].get("username"))
    else:
        await update.message.reply_text("🔎 Looking for a partner... Please wait.")
        logger.info(f"User {user_id} ({username}) waiting for a partner")

# /leave command
async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner = chat_manager.leave_chat(user_id)
    if partner:
        try:
            await context.bot.send_message(partner, "🚫 The stranger left the chat.")
            await update.message.reply_text("❌ You left the chat.")
            
            # Log chat end
            chat_monitor.log_chat_end(user_id, partner, reason="manual")
            
            logger.info(f"User {user_id} left chat with {partner}")
        except TelegramError as e:
            logger.error(f"Failed to notify partner about leaving: {e}")
            await update.message.reply_text("❌ You left the chat.")
    else:
        # Also remove from waiting queue if they're waiting
        if chat_manager.remove_from_queue(user_id):
            await update.message.reply_text("❌ You left the waiting queue.")
            logger.info(f"User {user_id} left waiting queue")
        else:
            await update.message.reply_text("You are not chatting with anyone right now.")

# /status command
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if chat_manager.is_chatting(user_id):
        await update.message.reply_text("You are currently chatting with a stranger. Use /leave to end the chat.")
    elif user_id in chat_manager.waiting_users:
        await update.message.reply_text("You are in the waiting queue. Use /leave to exit the queue.")
    else:
        await update.message.reply_text("You are not chatting or waiting. Use /chat to find someone.")

# Improved media forwarding with better error handling
async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = chat_manager.get_partner(user_id)
    
    if not partner_id:
        await update.message.reply_text("💬 Use /chat to find someone to talk to.")
        return
    
    # Get usernames
    username = update.effective_user.username or update.effective_user.first_name
    partner_username = chat_manager.user_stats.get(partner_id, {}).get("username", "Unknown")
    
    try:
        # Text messages
        if update.message.text and not update.message.text.startswith('/'):
            await context.bot.send_message(
                partner_id, 
                update.message.text
            )
            
            # Log the text message
            chat_monitor.log_message(
                user_id=user_id,
                partner_id=partner_id,
                message_type="text",
                content=update.message.text,
                username=username,
                partner_username=partner_username
            )
        
        # Photos
        elif update.message.photo:
            # Get the largest photo (best quality)
            photo = update.message.photo[-1]
            await context.bot.send_photo(
                partner_id,
                photo.file_id,
                caption=update.message.caption or ""
            )
            
            # Get file URL for monitoring
            photo_file = await photo.get_file()
            photo_url = photo_file.file_path  # This contains the URL
            
            # Log the photo message
            chat_monitor.log_message(
                user_id=user_id,
                partner_id=partner_id,
                message_type="photo",
                content="",  # Empty content for photo
                media_url=photo_url,
                caption=update.message.caption,
                username=username,
                partner_username=partner_username
            )
        
        # Videos
        elif update.message.video:
            await context.bot.send_video(
                partner_id,
                update.message.video.file_id,
                caption=update.message.caption or "",
                supports_streaming=True
            )
            
            # Get file URL for monitoring
            video_file = await update.message.video.get_file()
            video_url = video_file.file_path
            
            # Log the video message
            chat_monitor.log_message(
                user_id=user_id,
                partner_id=partner_id,
                message_type="video",
                content="",  # Empty content for video
                media_url=video_url,
                caption=update.message.caption,
                username=username,
                partner_username=partner_username
            )
        
        # Stickers
        elif update.message.sticker:
            await context.bot.send_sticker(
                partner_id,
                update.message.sticker.file_id
            )
            
            # Log the sticker message
            sticker_url = None
            try:
                sticker_file = await update.message.sticker.get_file()
                sticker_url = sticker_file.file_path
            except:
                pass
                
            chat_monitor.log_message(
                user_id=user_id,
                partner_id=partner_id,
                message_type="sticker",
                content="",  # Empty content for sticker
                media_url=sticker_url,
                username=username,
                partner_username=partner_username
            )
        
        # Video notes (circular videos)
        elif update.message.video_note:
            await context.bot.send_video_note(
                partner_id,
                update.message.video_note.file_id
            )
            
            # Get file URL for monitoring
            video_note_file = await update.message.video_note.get_file()
            video_note_url = video_note_file.file_path
            
            # Log the video note message
            chat_monitor.log_message(
                user_id=user_id,
                partner_id=partner_id,
                message_type="video_note",
                content="",  # Empty content for video note
                media_url=video_note_url,
                username=username,
                partner_username=partner_username
            )
        
        # Voice notes
        elif update.message.voice:
            await context.bot.send_voice(
                partner_id,
                update.message.voice.file_id,
                caption=update.message.caption or ""
            )
            
            # Get file URL for monitoring
            voice_file = await update.message.voice.get_file()
            voice_url = voice_file.file_path
            
            # Log the voice message
            chat_monitor.log_message(
                user_id=user_id,
                partner_id=partner_id,
                message_type="voice",
                content="",  # Empty content for voice
                media_url=voice_url,
                caption=update.message.caption,
                username=username,
                partner_username=partner_username
            )
        
        # Documents/files
        elif update.message.document:
            await context.bot.send_document(
                partner_id,
                update.message.document.file_id,
                caption=update.message.caption or ""
            )
            
            # Get file URL for monitoring
            doc_file = await update.message.document.get_file()
            doc_url = doc_file.file_path
            
            # Log the document message
            chat_monitor.log_message(
                user_id=user_id,
                partner_id=partner_id,
                message_type="document",
                content=update.message.document.file_name or "",
                media_url=doc_url,
                caption=update.message.caption,
                username=username,
                partner_username=partner_username
            )
        
        # Audio files
        elif update.message.audio:
            await context.bot.send_audio(
                partner_id,
                update.message.audio.file_id,
                caption=update.message.caption or ""
            )
            
            # Get file URL for monitoring
            audio_file = await update.message.audio.get_file()
            audio_url = audio_file.file_path
            
            # Log the audio message
            chat_monitor.log_message(
                user_id=user_id,
                partner_id=partner_id,
                message_type="audio",
                content=update.message.audio.title or "",
                media_url=audio_url,
                caption=update.message.caption,
                username=username,
                partner_username=partner_username
            )
        
        # Animations/GIFs
        elif update.message.animation:
            await context.bot.send_animation(
                partner_id,
                update.message.animation.file_id,
                caption=update.message.caption or ""
            )
            
            # Get file URL for monitoring
            animation_file = await update.message.animation.get_file()
            animation_url = animation_file.file_path
            
            # Log the animation message
            chat_monitor.log_message(
                user_id=user_id,
                partner_id=partner_id,
                message_type="animation",
                content="",  # Empty content for animation
                media_url=animation_url,
                caption=update.message.caption,
                username=username,
                partner_username=partner_username
            )
            
    except TelegramError as e:
        logger.error(f"Failed to forward message: {e}")
        # If we can't send to partner, they may have blocked the bot
        if "blocked" in str(e).lower() or "not found" in str(e).lower():
            await update.message.reply_text("⚠️ Cannot send message. The stranger may have left the chat.")
            # Automatically disconnect if partner is unavailable
            chat_manager.leave_chat(user_id)
            # Log chat end
            chat_monitor.log_chat_end(user_id, partner_id, reason="connection_lost")
        else:
            await update.message.reply_text("⚠️ Failed to send message. Please try again.")

# Error handler for the bot
async def error_handler(update, context):
    """Log the error and send a message to the user if possible."""
    logger.warning(f'Update {update} caused error {context.error}')
    
    # Handle the conflict error specifically
    if isinstance(context.error, Conflict):
        logger.info("Conflict detected, waiting before reconnecting...")
        await asyncio.sleep(5)  # Wait 5 seconds before retry
    
    # For user-facing errors, notify them if possible
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Sorry, I encountered an error processing your request. Please try again later."
            )
        except:
            pass

# Display analytics periodically in terminal
def print_analytics():
    while True:
        try:
            stats = chat_manager.get_stats()
            
            print("\n" + "="*50)
            print(f"📊 BOT ANALYTICS - {datetime.datetime.now().strftime('%H:%M:%S ; %d.%m.%Y')}")
            print(f"🕒 Uptime: {get_uptime()}")
            print(f"👥 Total Users: {stats['total_users']}")
            print(f"⏳ Waiting Users: {stats['waiting_users']}")
            print(f"🔄 Active Chats: {stats['active_chats']}")
            
            if stats['active_chats'] > 0:
                print("\nActive Connections:")
                for user_id, user_data in stats['user_details'].items():
                    if user_data['partner']:
                        partner_id = user_data['partner']
                        partner_name = stats['user_details'].get(partner_id, {}).get('username', 'Unknown')
                        user_name = user_data['username'] or 'Unknown'
                        print(f"  {user_name} (ID: {user_id}) ⟷ {partner_name} (ID: {partner_id})")
            
            print("="*50 + "\n")
            time.sleep(60)  # Update every minute
        except Exception as e:
            logger.error(f"Error in analytics thread: {e}")
            time.sleep(60)  # Continue despite errors

# Function to calculate uptime
def get_uptime():
    now = datetime.datetime.now()
    uptime = now - start_time
    # Format days, hours, minutes, seconds
    days, seconds = uptime.days, uptime.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{days}d {hours}h {minutes}m {seconds}s"

# Graceful shutdown function
def stop_bot(signum, frame):
    stop_time = datetime.datetime.now()
    uptime = get_uptime()
    print(f"Bot Stopped at {stop_time.strftime('%H:%M:%S ; %d.%m.%Y')}")
    print(f"Total Uptime: {uptime}")
    exit(0)

# Attach signals to stop the bot gracefully
signal.signal(signal.SIGINT, stop_bot)   # Ctrl+C
signal.signal(signal.SIGTERM, stop_bot)  # kill command

# Broadcast command - for admin use only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a broadcast message to all users who have used the bot"""
    user_id = update.effective_user.id
    
    # Check if user is authorized to broadcast
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        logger.warning(f"Unauthorized broadcast attempt by user {user_id}")
        return
    
    # Check if message is provided
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>\n\nSend a message to all users.")
        return
    
    # Get the message text
    message_text = ' '.join(context.args)
    
    # Get all users who have interacted with the bot
    all_users = list(chat_manager.user_stats.keys())
    
    if not all_users:
        await update.message.reply_text("No users found in the database.")
        return
    
    # Send initial status
    status_message = await update.message.reply_text(
        f"📣 Broadcasting to {len(all_users)} users...\n"
        f"0% complete (0/{len(all_users)})"
    )
    
    # Counters for successful and failed sends
    successful = 0
    failed = 0
    
    # Send the broadcast message to all users
    for i, user_id in enumerate(all_users):
        try:
            await context.bot.send_message(
                user_id,
                f"📢 *ANNOUNCEMENT*\n\n{message_text}",
                parse_mode='Markdown'
            )
            successful += 1
        except TelegramError as e:
            failed += 1
            logger.error(f"Failed to send broadcast to user {user_id}: {e}")
        
        # Update status every 10 users or at the end
        if (i + 1) % 10 == 0 or i == len(all_users) - 1:
            percent_complete = int((i + 1) / len(all_users) * 100)
            await status_message.edit_text(
                f"📣 Broadcasting to {len(all_users)} users...\n"
                f"{percent_complete}% complete ({i+1}/{len(all_users)})\n"
                f"✅ Successful: {successful}\n"
                f"❌ Failed: {failed}"
            )
            
            # Small delay to avoid hitting rate limits
            await asyncio.sleep(0.1)
    
    # Final report
    await update.message.reply_text(
        f"📣 Broadcast completed!\n"
        f"✅ Successfully sent: {successful}\n"
        f"❌ Failed: {failed}"
    )
    
    logger.info(f"Broadcast completed by admin {user_id}. Successful: {successful}, Failed: {failed}")

# Main run
if __name__ == "__main__":
    # Load users from file if available
    chat_manager.load_users_from_file()
    
    # Start auto-saving users periodically
    chat_manager.auto_save_users()
    
    # Set the start time
    start_time = time.time()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chat", chat))
    app.add_handler(CommandHandler("leave", leave))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("broadcast", broadcast))
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    # Handle all supported message types
    app.add_handler(MessageHandler(
        filters.TEXT | 
        filters.PHOTO | 
        filters.VIDEO | 
        filters.Sticker.ALL | 
        filters.VIDEO_NOTE | 
        filters.VOICE | 
        filters.Document.ALL | 
        filters.AUDIO | 
        filters.ANIMATION,
        forward
    ))
    
    # Analytics thread
    analytics_thread = threading.Thread(target=print_analytics)
    analytics_thread.daemon = True
    analytics_thread.start()
    
    print("Bot started!")
    app.run_polling()