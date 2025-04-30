# bot.py
import logging
import asyncio
import signal
import threading
import time
import datetime
import pytz  # For proper timezone handling
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CommandHandler, 
    MessageHandler, 
    Filters, 
    CallbackContext,
    ConversationHandler
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

# Define conversation states
GENDER, INTEREST, MATCHING = range(3)

# Admin IDs who are allowed to use broadcast
ADMIN_IDS = [2023022792, 6261300717]  # Admin user IDs

# Initialize the updater and dispatcher
updater = Updater(token=BOT_TOKEN)
dispatcher = updater.dispatcher

# To track start time
start_time = None

# Set timezone - use UTC for production environments for consistency
TIMEZONE = pytz.timezone('Asia/Kolkata')  # Indian Standard Time (IST)

def get_localized_time(timestamp=None):
    """Get timezone-aware datetime object or convert timestamp to local time"""
    if timestamp is None:
        # Current time
        return datetime.datetime.now(TIMEZONE)
    else:
        # Convert timestamp to datetime
        dt = datetime.datetime.fromtimestamp(timestamp)
        return TIMEZONE.localize(dt)

def format_datetime(dt):
    """Format datetime object to string"""
    return dt.strftime('%Y-%m-%d %H:%M:%S %Z')

# /start command
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Check if user is banned
    ban_info = chat_manager.is_banned(user_id)
    if ban_info:
        ban_duration = format_datetime(get_localized_time(ban_info["until"]))
        update.message.reply_text(
            f"⛔ You are currently banned from using this bot.\n"
            f"Reason: {ban_info['reason']}\n"
            f"Ban expires: {ban_duration}"
        )
        return
    
    # Register or update user in user_stats
    if user_id not in chat_manager.user_stats:
        chat_manager.user_stats[user_id] = {"username": username, "partner": None, "connect_time": time.time()}
    else:
        chat_manager.user_stats[user_id]["username"] = username
    
    update.message.reply_text(
        "Welcome to Unknown Chat Bot! 👋\n\n"
        "Commands:\n"
        "/chat - Find a random stranger to chat with\n"
        "/leave - Leave current chat\n"
        "/status - Check if you're in a chat\n\n"
        "You can send text, photos, videos, stickers, and video messages!"
    )

# /chat command updated to start preference conversation
def chat(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Check if user is banned
    ban_info = chat_manager.is_banned(user_id)
    if ban_info:
        ban_duration = format_datetime(get_localized_time(ban_info["until"]))
        update.message.reply_text(
            f"⛔ You are currently banned from using this bot.\n"
            f"Reason: {ban_info['reason']}\n"
            f"Ban expires: {ban_duration}"
        )
        return ConversationHandler.END
    
    # Leave current chat if exists
    if chat_manager.is_chatting(user_id):
        partner = chat_manager.leave_chat(user_id)
        if partner:
            try:
                context.bot.send_message(partner, "🚫 The stranger left the chat.")
                # Log chat end
                chat_monitor.log_chat_end(user_id, partner, reason="started_new")
            except TelegramError as e:
                logger.error(f"Failed to notify partner {partner}: {e}")
    
    # Remove from waiting queue if already in it
    chat_manager.remove_from_queue(user_id)
    
    # Check if the user already has gender and interest info
    user_info = chat_manager.user_stats.get(user_id, {})
    has_gender = "gender" in user_info and user_info["gender"] is not None
    has_interest = "interest" in user_info and user_info["interest"] is not None
    
    if has_gender and has_interest:
        # User already has preferences set, add them to queue
        gender = user_info["gender"]
        interest = user_info["interest"]
        chat_manager.add_to_queue(user_id, username, gender, interest)
        update.message.reply_text(
            # f"📝 Your preferences:\n"
            # f"Gender: {format_gender(gender)}\n"
            # f"Interested in: {format_gender(interest)}\n\n"
            f"🔎 Looking for a partner... Please wait."
        )
        logger.info(f"User {user_id} ({username}) waiting for a partner with preferences: gender={gender}, interest={interest}")
        return check_match(update, context)
    else:
        # Ask for gender first
        reply_keyboard = [['M', 'F', 'O']]
        update.message.reply_text(
            '📝 Please select your gender:\n\n'
            'M - Male ♂️\n'
            'F - Female ♀️\n'
            'O - Other ⚧️\n\n'
            'This will help us to improve your experience in this bot 🤖',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return GENDER

def gender_selection(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    gender = update.message.text.upper()
    
    if gender not in ['M', 'F', 'O']:
        update.message.reply_text(
            '⚠️ Please select a valid option:\n\n'
            'M - Male ♂️\n'
            'F - Female ♀️\n'
            'O - Other ⚧️\n\n'
            'This will help us to improve your experience in this bot 🤖'
        )
        return GENDER
    
    # Save gender to context for later use
    context.user_data['gender'] = gender
    
    # Ask for interest next
    reply_keyboard = [['M', 'F', 'O']]
    update.message.reply_text(
        '📝 Please select who you want to chat with:\n\n'
        'M - Male ♂️\n'
        'F - Female ♀️\n'
        'O - Other/Anyone 🤖\n\n'
        'This will help us to improve your experience in this bot 🤖',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return INTEREST

def interest_selection(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    interest = update.message.text.upper()
    
    if interest not in ['M', 'F', 'O']:
        update.message.reply_text(
            '⚠️ Please select a valid option:\n\n'
            'M - Male ♂️\n'
            'F - Female ♀️\n'
            'O - Other/Anyone 🤖\n\n'
            'This will help us to improve your experience in this bot 🤖',
        )
        return INTEREST
    
    # Get gender from context
    gender = context.user_data.get('gender')
    
    # Add user to queue with preferences
    chat_manager.add_to_queue(user_id, username, gender, interest)
    
    # Remove keyboard and confirm preferences
    update.message.reply_text(
        # f"📝 Your preferences have been saved:\n"
        # f"Gender: {format_gender(gender)}\n"
        # f"Interested in: {format_gender(interest)}\n\n"
        f"🔎 Looking for a partner... Please wait.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    logger.info(f"User {user_id} ({username}) waiting for a partner with preferences: gender={gender}, interest={interest}")
    
    return check_match(update, context)

def format_gender(code):
    """Convert gender code to readable format"""
    if code == 'M':
        return 'Male'
    elif code == 'F':
        return 'Female'
    else:
        return 'Other'

def check_match(update: Update, context: CallbackContext):
    """Check if a match is available and connect users"""
    user_id = update.effective_user.id
    
    # Try to match users (this doesn't consider preferences as requested)
    user1, user2 = chat_manager.match_users()
    
    if user1 and user2:
        try:
            context.bot.send_message(user1, "🎉 Connected to a stranger. Say hi! 💬\n\nType /leave to end this chat.\nType /chat to find a new partner.\n\n💫 Share our bot to get a better user experience: https://t.me/unknwn_chat_bot")
            context.bot.send_message(user2, "🎉 Connected to a stranger. Say hi! 💬\n\nType /leave to end this chat.\nType /chat to find a new partner.\n\n💫 Share our bot to get a better user experience: https://t.me/unknwn_chat_bot")
            
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
            chat_manager.add_to_queue(
                user1, 
                chat_manager.user_stats[user1].get("username"),
                chat_manager.user_stats[user1].get("gender"),
                chat_manager.user_stats[user1].get("interest")
            )
            chat_manager.add_to_queue(
                user2, 
                chat_manager.user_stats[user2].get("username"),
                chat_manager.user_stats[user2].get("gender"),
                chat_manager.user_stats[user2].get("interest")
            )
    
    return ConversationHandler.END

# /leave command
def leave(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    partner = chat_manager.leave_chat(user_id)
    if partner:
        try:
            context.bot.send_message(partner, "🚫 The stranger left the chat.")
            update.message.reply_text("❌ You left the chat.")
            
            # Log chat end
            chat_monitor.log_chat_end(user_id, partner, reason="manual")
            
            logger.info(f"User {user_id} left chat with {partner}")
        except TelegramError as e:
            logger.error(f"Failed to notify partner about leaving: {e}")
            update.message.reply_text("❌ You left the chat.")
    else:
        # Also remove from waiting queue if they're waiting
        if chat_manager.remove_from_queue(user_id):
            update.message.reply_text("❌ You left the waiting queue.")
            logger.info(f"User {user_id} left waiting queue")
        else:
            update.message.reply_text("You are not chatting with anyone right now.")

# /status command
def status(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    # Check if user is banned
    ban_info = chat_manager.is_banned(user_id)
    if ban_info:
        ban_duration = format_datetime(get_localized_time(ban_info["until"]))
        update.message.reply_text(
            f"⛔ You are currently banned from using this bot.\n"
            f"Reason: {ban_info['reason']}\n"
            f"Ban expires: {ban_duration}"
        )
        return
    
    if chat_manager.is_chatting(user_id):
        update.message.reply_text("You are currently chatting with a stranger. Use /leave to end the chat.")
    elif user_id in chat_manager.waiting_users:
        update.message.reply_text("You are in the waiting queue. Use /leave to exit the queue.")
    else:
        update.message.reply_text("You are not chatting or waiting. Use /chat to find someone.")

# Improved media forwarding with better error handling
def forward(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    # Check if user is banned
    ban_info = chat_manager.is_banned(user_id)
    if ban_info:
        ban_duration = format_datetime(get_localized_time(ban_info["until"]))
        update.message.reply_text(
            f"⛔ You are currently banned from using this bot.\n"
            f"Reason: {ban_info['reason']}\n"
            f"Ban expires: {ban_duration}"
        )
        return
    
    partner_id = chat_manager.get_partner(user_id)
    
    if not partner_id:
        update.message.reply_text("💬 Use /chat to find someone to talk to.")
        return
    
    # Get usernames
    username = update.effective_user.username or update.effective_user.first_name
    partner_username = chat_manager.user_stats.get(partner_id, {}).get("username", "Unknown")
    
    try:
        # Text messages
        if update.message.text and not update.message.text.startswith('/'):
            context.bot.send_message(
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
            context.bot.send_photo(
                partner_id,
                photo.file_id,
                caption=update.message.caption or ""
            )
            
            # Get file URL for monitoring
            photo_file = photo.get_file()
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
            context.bot.send_video(
                partner_id,
                update.message.video.file_id,
                caption=update.message.caption or ""
            )
            
            # Get file URL for monitoring
            video_file = update.message.video.get_file()
            video_url = video_file.file_path
            
            # Log the video message
            chat_monitor.log_message(
                user_id=user_id,
                partner_id=partner_id,
                message_type="video",
                content="",
                media_url=video_url,
                caption=update.message.caption,
                username=username,
                partner_username=partner_username
            )
        
        # Stickers
        elif update.message.sticker:
            context.bot.send_sticker(
                partner_id,
                update.message.sticker.file_id
            )
            
            # Log the sticker message
            sticker_url = None
            try:
                sticker_file = update.message.sticker.get_file()
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
            context.bot.send_video_note(
                partner_id,
                update.message.video_note.file_id
            )
            
            # Get file URL for monitoring
            video_note_file = update.message.video_note.get_file()
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
            context.bot.send_voice(
                partner_id,
                update.message.voice.file_id,
                caption=update.message.caption or ""
            )
            
            # Get file URL for monitoring
            voice_file = update.message.voice.get_file()
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
            context.bot.send_document(
                partner_id,
                update.message.document.file_id,
                caption=update.message.caption or ""
            )
            
            # Get file URL for monitoring
            doc_file = update.message.document.get_file()
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
            context.bot.send_audio(
                partner_id,
                update.message.audio.file_id,
                caption=update.message.caption or ""
            )
            
            # Get file URL for monitoring
            audio_file = update.message.audio.get_file()
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
            context.bot.send_animation(
                partner_id,
                update.message.animation.file_id,
                caption=update.message.caption or ""
            )
            
            # Get file URL for monitoring
            animation_file = update.message.animation.get_file()
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
        update.message.reply_text("⚠️ Failed to send your message.")
        
        # Check if the partner's chat is still valid
        if "blocked" in str(e).lower() or "not found" in str(e).lower() or "deactivated" in str(e).lower():
            # Partner has blocked the bot or deleted their account
            partner = chat_manager.leave_chat(user_id)
            if partner:
                update.message.reply_text("❌ Chat ended because the stranger is no longer available.")
                # Log chat end
                chat_monitor.log_chat_end(user_id, partner, reason="partner_unavailable")

# Admin commands
def admin_end_chat(update: Update, context: CallbackContext):
    """Admin command to forcefully end a chat between users"""
    user_id = update.effective_user.id
    
    # Check if user is an admin
    if user_id not in ADMIN_IDS:
        update.message.reply_text("⛔ You are not authorized to use this command.")
        logger.warning(f"Unauthorized admin_end_chat attempt by user {user_id}")
        return
    
    # Check if target user ID is provided
    if not context.args or len(context.args) < 1:
        update.message.reply_text("Usage: /endchat <user_id> [reason]")
        return
    
    try:
        target_user_id = int(context.args[0])
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Admin action"
        
        # Check if user is in a chat
        if not chat_manager.is_chatting(target_user_id):
            update.message.reply_text(f"User {target_user_id} is not currently in a chat.")
            return
        
        # Get partner before ending chat
        partner_id = chat_manager.get_partner(target_user_id)
        
        # End the chat
        if chat_manager.admin_end_chat(target_user_id, reason=reason):
            # Notify users
            try:
                context.bot.send_message(
                    target_user_id, 
                    f"⛔ Your chat has been ended by an admin.\nReason: {reason}"
                )
                
                if partner_id:
                    context.bot.send_message(
                        partner_id, 
                        f"⛔ Your chat has been ended by an admin.\nReason: {reason}"
                    )
                
            # Log chat end
                if partner_id:
                    chat_monitor.log_chat_end(target_user_id, partner_id, reason=f"admin_action: {reason}")
                
                update.message.reply_text(f"✅ Successfully ended chat for user {target_user_id}")
                logger.info(f"Admin {user_id} ended chat for user {target_user_id}. Reason: {reason}")
                
            except TelegramError as e:
                update.message.reply_text(f"✅ Chat ended but failed to notify users: {e}")
                logger.error(f"Failed to notify users about admin ending chat: {e}")
        else:
            update.message.reply_text(f"❌ Failed to end chat for user {target_user_id}")
    
    except ValueError:
        update.message.reply_text("❌ Invalid user ID. Please provide a valid numeric user ID.")

def admin_ban_user(update: Update, context: CallbackContext):
    """Admin command to ban a user for a specified duration"""
    user_id = update.effective_user.id
    
    # Check if user is an admin
    if user_id not in ADMIN_IDS:
        update.message.reply_text("⛔ You are not authorized to use this command.")
        logger.warning(f"Unauthorized admin_ban_user attempt by user {user_id}")
        return
    
    # Check if enough arguments are provided
    if not context.args or len(context.args) < 2:
        update.message.reply_text(
            "Usage: /ban <user_id> <duration_hours> [reason]\n\n"
            "Example: /ban 123456789 24 Inappropriate behavior"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        duration_hours = float(context.args[1])
        reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Violation of terms"
        
        # Ban the user
        if chat_manager.ban_user(target_user_id, duration_hours, reason):
            # Get username for logging
            username = chat_manager.user_stats.get(target_user_id, {}).get("username", "Unknown")
            
            # Format ban duration for display
            ban_until = time.time() + (duration_hours * 3600)
            ban_until_str = format_datetime(get_localized_time(ban_until))
            
            # Notify the user
            try:
                context.bot.send_message(
                    target_user_id, 
                    f"⛔ You have been banned from using this bot.\n"
                    f"Reason: {reason}\n"
                    f"Duration: {duration_hours} hours\n"
                    f"Ban expires: {ban_until_str}"
                )
            except TelegramError as e:
                logger.error(f"Failed to notify user {target_user_id} about ban: {e}")
            
            update.message.reply_text(
                f"✅ User {target_user_id} ({username}) has been banned for {duration_hours} hours.\n"
                f"Reason: {reason}\n"
                f"Ban expires: {ban_until_str}"
            )
            
            logger.info(f"Admin {user_id} banned user {target_user_id} ({username}) for {duration_hours} hours. Reason: {reason}")
        else:
            update.message.reply_text(f"❌ Failed to ban user {target_user_id}")
    
    except ValueError:
        update.message.reply_text("❌ Invalid user ID or duration. Please provide valid numeric values.")

def admin_unban_user(update: Update, context: CallbackContext):
    """Admin command to unban a user"""
    user_id = update.effective_user.id
    
    # Check if user is an admin
    if user_id not in ADMIN_IDS:
        update.message.reply_text("⛔ You are not authorized to use this command.")
        logger.warning(f"Unauthorized admin_unban_user attempt by user {user_id}")
        return
    
    # Check if target user ID is provided
    if not context.args or len(context.args) < 1:
        update.message.reply_text("Usage: /unban <user_id>")
        return
    
    try:
        target_user_id = int(context.args[0])
        
        # Check if user is banned
        if not chat_manager.is_banned(target_user_id):
            update.message.reply_text(f"User {target_user_id} is not currently banned.")
            return
        
        # Unban the user
        if chat_manager.unban_user(target_user_id):
            # Get username for logging
            username = chat_manager.user_stats.get(target_user_id, {}).get("username", "Unknown")
            
            # Notify the user
            try:
                context.bot.send_message(
                    target_user_id, 
                    f"✅ Your ban has been lifted. You can now use the bot again."
                )
            except TelegramError as e:
                logger.error(f"Failed to notify user {target_user_id} about unban: {e}")
            
            update.message.reply_text(f"✅ User {target_user_id} ({username}) has been unbanned.")
            logger.info(f"Admin {user_id} unbanned user {target_user_id} ({username})")
        else:
            update.message.reply_text(f"❌ Failed to unban user {target_user_id}")
    
    except ValueError:
        update.message.reply_text("❌ Invalid user ID. Please provide a valid numeric user ID.")

def admin_list_banned(update: Update, context: CallbackContext):
    """Admin command to list all banned users"""
    user_id = update.effective_user.id
    
    # Check if user is an admin
    if user_id not in ADMIN_IDS:
        update.message.reply_text("⛔ You are not authorized to use this command.")
        logger.warning(f"Unauthorized admin_list_banned attempt by user {user_id}")
        return
    
    # Get all banned users
    banned_users = chat_manager.get_banned_users()
    
    if not banned_users:
        update.message.reply_text("✅ No users are currently banned.")
        return
    
    # Format the list of banned users
    current_time = time.time()
    banned_list = []
    
    for banned_id, ban_info in banned_users.items():
        # Get username
        username = chat_manager.user_stats.get(int(banned_id), {}).get("username", "Unknown")
        
        # Calculate remaining time
        remaining_seconds = ban_info["until"] - current_time
        if remaining_seconds <= 0:
            remaining_time = "Expired"
        else:
            remaining_hours = remaining_seconds / 3600
            if remaining_hours >= 24:
                remaining_days = remaining_hours / 24
                remaining_time = f"{remaining_days:.1f} days"
            else:
                remaining_time = f"{remaining_hours:.1f} hours"
        
        # Format ban expiry time
        ban_until = format_datetime(get_localized_time(ban_info["until"]))
        
        banned_list.append(
            f"• {banned_id} ({username})\n"
            f"  Reason: {ban_info.get('reason', 'Unknown')}\n"
            f"  Expires: {ban_until}\n"
            f"  Remaining: {remaining_time}\n"
        )
    
    # Create the message
    message = f"📋 Banned Users ({len(banned_users)}):\n\n" + "\n".join(banned_list)
    
    # Send the message (split if needed)
    if len(message) <= 4096:
        update.message.reply_text(message)
    else:
        # Split into chunks of max 4000 characters
        chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
        for i, chunk in enumerate(chunks):
            update.message.reply_text(f"Part {i+1}/{len(chunks)}:\n\n{chunk}")

def admin_bot_analysis(update: Update, context: CallbackContext):
    """Admin command to show detailed bot analysis including waiting users, active chats, and banned users"""
    user_id = update.effective_user.id
    
    # Check if user is an admin
    if user_id not in ADMIN_IDS:
        update.message.reply_text("⛔ You are not authorized to use this command.")
        logger.warning(f"Unauthorized admin_bot_analysis attempt by user {user_id}")
        return
    
    # Get current time for calculations
    current_time = time.time()
    
    # ===== WAITING USERS =====
    waiting_list = []
    for waiting_id in chat_manager.waiting_users:
        username = chat_manager.user_stats.get(waiting_id, {}).get("username", "Unknown")
        gender = chat_manager.user_stats.get(waiting_id, {}).get("gender", "?")
        interest = chat_manager.user_stats.get(waiting_id, {}).get("interest", "?")
        
        # Calculate waiting time if available
        if waiting_id in chat_manager.user_stats and "connect_time" in chat_manager.user_stats[waiting_id]:
            waiting_since = chat_manager.user_stats[waiting_id]["connect_time"]
            waiting_minutes = (current_time - waiting_since) / 60
            waiting_list.append(
                f"• {waiting_id} ({username}) - waiting for {waiting_minutes:.1f} minutes\n"
                f"  Gender: {format_gender(gender)}, Interested in: {format_gender(interest)}"
            )
        else:
            waiting_list.append(
                f"• {waiting_id} ({username})\n"
                f"  Gender: {format_gender(gender)}, Interested in: {format_gender(interest)}"
            )
    
    # ===== ACTIVE CHATS =====
    active_chats = {}
    for user_id, partner_id in chat_manager.active_chats.items():
        # Only process each pair once
        if user_id < partner_id:
            user_name = chat_manager.user_stats.get(user_id, {}).get("username", "Unknown")
            partner_name = chat_manager.user_stats.get(partner_id, {}).get("username", "Unknown")
            
            # Get gender and interest info
            user_gender = chat_manager.user_stats.get(user_id, {}).get("gender", "?")
            user_interest = chat_manager.user_stats.get(user_id, {}).get("interest", "?")
            partner_gender = chat_manager.user_stats.get(partner_id, {}).get("gender", "?")
            partner_interest = chat_manager.user_stats.get(partner_id, {}).get("interest", "?")
            
            # Calculate chat duration if available
            chat_duration = "Unknown"
            if user_id in chat_manager.user_stats and "connect_time" in chat_manager.user_stats[user_id]:
                chat_since = chat_manager.user_stats[user_id]["connect_time"]
                chat_minutes = (current_time - chat_since) / 60
                if chat_minutes < 60:
                    chat_duration = f"{chat_minutes:.1f} minutes"
                else:
                    chat_hours = chat_minutes / 60
                    chat_duration = f"{chat_hours:.1f} hours"
            
            active_chats[f"{user_id}_{partner_id}"] = (
                f"• {user_id} ({user_name}) ↔️ {partner_id} ({partner_name})\n"
                f"  Duration: {chat_duration}\n"
                f"  User 1: Gender {format_gender(user_gender)}, Interest: {format_gender(user_interest)}\n"
                f"  User 2: Gender {format_gender(partner_gender)}, Interest: {format_gender(partner_interest)}"
            )
    
    # ===== BANNED USERS =====
    banned_list = []
    banned_users = chat_manager.get_banned_users()
    
    for banned_id, ban_info in banned_users.items():
        username = chat_manager.user_stats.get(int(banned_id), {}).get("username", "Unknown")
        gender = chat_manager.user_stats.get(int(banned_id), {}).get("gender", "?")
        interest = chat_manager.user_stats.get(int(banned_id), {}).get("interest", "?")
        
        # Calculate remaining time
        remaining_seconds = ban_info["until"] - current_time
        if remaining_seconds <= 0:
            remaining_time = "Expired"
        else:
            remaining_hours = remaining_seconds / 3600
            if remaining_hours >= 24:
                remaining_days = remaining_hours / 24
                remaining_time = f"{remaining_days:.1f} days"
            else:
                remaining_time = f"{remaining_hours:.1f} hours"
        
        banned_list.append(
            f"• {banned_id} ({username}) - {remaining_time} remaining\n"
            f"  Gender: {format_gender(gender)}, Interest: {format_gender(interest)}"
        )
    
    # ===== CREATE REPORT =====
    report = [
        "📊 BOT ANALYSIS REPORT 📊",
        "="*30,
        "",
        f"🕓 Report time: {format_datetime(get_localized_time())}",
        f"⏱️ Bot uptime: {get_uptime()}",
        "",
        f"👥 WAITING USERS ({len(waiting_list)}):",
        "="*20
    ]
    
    if waiting_list:
        report.extend(waiting_list)
    else:
        report.append("No users waiting")
    
    report.extend([
        "",
        f"🔄 ACTIVE CHATS ({len(active_chats)}):",
        "="*20
    ])
    
    if active_chats:
        report.extend(active_chats.values())
    else:
        report.append("No active chats")
    
    report.extend([
        "",
        f"⛔ BANNED USERS ({len(banned_list)}):",
        "="*20
    ])
    
    if banned_list:
        report.extend(banned_list)
    else:
        report.append("No banned users")
    
    # Join all parts of the report
    full_report = "\n".join(report)
    
    # Send the report (split if needed)
    if len(full_report) <= 4096:
        update.message.reply_text(full_report)
    else:
        # Split into chunks of max 4000 characters
        chunks = [full_report[i:i+4000] for i in range(0, len(full_report), 4000)]
        for i, chunk in enumerate(chunks):
            update.message.reply_text(f"Part {i+1}/{len(chunks)}:\n\n{chunk}")
    
    logger.info(f"Bot analysis report generated for admin {user_id}")

def error_handler(update, context):
    """Log Errors caused by Updates."""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        # Notify user of error
        if update and update.effective_message:
            update.effective_message.reply_text(
                "Sorry, something went wrong. Please try again later."
            )
    except:
        pass

def print_analytics():
    """Print basic analytics to console every minute"""
    while True:
        stats = chat_manager.get_stats()
        
        print("\n==== BOT ANALYTICS ====")
        print(f"Time: {format_datetime(get_localized_time())}")
        print(f"Uptime: {get_uptime()}")
        print(f"Waiting Users: {stats['waiting_users']}")
        print(f"Active Chats: {stats['active_chats']}")
        print(f"Total Users: {stats['total_users']}")
        print(f"Banned Users: {stats['banned_users']}")
        print("========================\n")
        
        time.sleep(60)  # Update every minute

def get_uptime():
    """Get bot uptime in human-readable format"""
    if start_time:
        uptime = get_localized_time() - start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m {seconds}s"
    return "Unknown"

def stop_bot(signum, frame):
    """Handle signals to stop the bot gracefully"""
    print("\nStopping bot...")
    
    # Save user data before exit
    chat_manager.save_users_to_file()
    chat_manager.save_banned_users()
    
    print("User data saved. Exiting...")
    exit(0)

# Attach signals to stop the bot gracefully
signal.signal(signal.SIGINT, stop_bot)   # Ctrl+C
signal.signal(signal.SIGTERM, stop_bot)  # kill command

# Broadcast command - for admin use only
def broadcast(update: Update, context: CallbackContext):
    """Send a broadcast message to all users who have used the bot"""
    user_id = update.effective_user.id
    
    # Check if user is authorized to broadcast
    if user_id not in ADMIN_IDS:
        update.message.reply_text("⛔ You are not authorized to use this command.")
        logger.warning(f"Unauthorized broadcast attempt by user {user_id}")
        return
    
    # Check if message is provided
    if not context.args:
        update.message.reply_text("Usage: /broadcast <message>\n\nSend a message to all users.")
        return
    
    # Get the message text
    message_text = ' '.join(context.args)
    
    # Get all users who have interacted with the bot
    all_users = list(chat_manager.user_stats.keys())
    
    if not all_users:
        update.message.reply_text("No users found in the database.")
        return
    
    # Send initial status
    status_message = update.message.reply_text(
        f"📣 Broadcasting to {len(all_users)} users...\n"
        f"0% complete (0/{len(all_users)})"
    )
    
    # Counters for successful and failed sends
    successful = 0
    failed = 0
    
    # Send message to each user with progress updates
    for i, uid in enumerate(all_users):
        try:
            context.bot.send_message(
                uid, 
                f"📢 ANNOUNCEMENT from Unknown Chat Bot:\n\n{message_text}"
            )
            successful += 1
        except TelegramError as e:
            logger.error(f"Failed to broadcast to user {uid}: {e}")
            failed += 1
        
        # Update status every 10 users or at the end
        if (i + 1) % 10 == 0 or i == len(all_users) - 1:
            progress = ((i + 1) / len(all_users)) * 100
            try:
                context.bot.edit_message_text(
                    chat_id=status_message.chat_id,
                    message_id=status_message.message_id,
                    text=f"📣 Broadcasting to {len(all_users)} users...\n"
                         f"{progress:.1f}% complete ({i+1}/{len(all_users)})\n"
                         f"Successful: {successful}\n"
                         f"Failed: {failed}"
                )
            except TelegramError as e:
                logger.error(f"Failed to update broadcast status: {e}")
    
    # Final status update
    update.message.reply_text(
        f"✅ Broadcast complete!\n"
        f"Total users: {len(all_users)}\n"
        f"Successful: {successful}\n"
        f"Failed: {failed}"
    )
    logger.info(f"Broadcast by admin {user_id} complete. Success: {successful}, Failed: {failed}")

# Main run
if __name__ == "__main__":
    # Load users from file if available
    chat_manager.load_users_from_file()
    
    # Load banned users from file if available
    chat_manager.load_banned_users()
    
    # Start auto-saving users periodically
    chat_manager.auto_save_users()
    chat_manager.auto_save_banned_users()
    
    # Set the start time
    start_time = get_localized_time()
    
    # Create the conversation handler for chat preferences
    chat_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('chat', chat)],
        states={
            GENDER: [MessageHandler(Filters.text & ~Filters.command, gender_selection)],
            INTEREST: [MessageHandler(Filters.text & ~Filters.command, interest_selection)],
            MATCHING: [MessageHandler(Filters.text & ~Filters.command, check_match)]
        },
        fallbacks=[CommandHandler('leave', leave)]
    )
    
    # Command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(chat_conv_handler)  # Use the conversation handler instead of a simple command
    dispatcher.add_handler(CommandHandler("leave", leave))
    dispatcher.add_handler(CommandHandler("status", status))
    dispatcher.add_handler(CommandHandler("broadcast", broadcast))
    
    # Admin command handlers
    dispatcher.add_handler(CommandHandler("ban", admin_ban_user))
    dispatcher.add_handler(CommandHandler("unban", admin_unban_user))
    dispatcher.add_handler(CommandHandler("bannedlist", admin_list_banned))
    dispatcher.add_handler(CommandHandler("endchat", admin_end_chat))
    dispatcher.add_handler(CommandHandler("bot_analysis", admin_bot_analysis))
    
    # Add error handler
    dispatcher.add_error_handler(error_handler)
    
    # Handle all supported message types
    dispatcher.add_handler(MessageHandler(
        Filters.text & ~Filters.command | 
        Filters.photo | 
        Filters.video | 
        Filters.sticker | 
        Filters.video_note | 
        Filters.voice | 
        Filters.document | 
        Filters.audio | 
        Filters.animation,
        forward
    ))
    
    # Analytics thread
    analytics_thread = threading.Thread(target=print_analytics)
    analytics_thread.daemon = True
    analytics_thread.start()
    
    print("Bot started!")
    updater.start_polling()
    updater.idle()