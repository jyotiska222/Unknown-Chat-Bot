import time
import threading
import logging
import datetime
import pytz
from telegram import Bot
from config import BOT_TOKEN

# Configure logger for the heartbeat monitor
heartbeat_logger = logging.getLogger(__name__)
heartbeat_logger.setLevel(logging.INFO)
if not heartbeat_logger.handlers:
    handler = logging.FileHandler("heartbeat_monitor.log")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    heartbeat_logger.addHandler(handler)

class HeartbeatMonitor:
    """
    Class to monitor the bot's heartbeat and notify admins if the bot becomes unresponsive.
    """
    def __init__(self, admin_ids, check_interval=60, allowed_missed_beats=3):
        self.admin_ids = admin_ids
        self.check_interval = check_interval  # seconds between heartbeat checks
        self.allowed_missed_beats = allowed_missed_beats  # number of missed beats before alert
        self.last_heartbeat = time.time()
        self.monitoring = False
        self.monitor_thread = None
        self.timezone = pytz.timezone('Asia/Kolkata')  # Same timezone as in bot.py
        self.bot = Bot(token=BOT_TOKEN)
        self.alert_sent = False  # Flag to prevent multiple alerts

    def start_monitoring(self):
        """Start the heartbeat monitoring thread"""
        if not self.monitoring:
            self.monitoring = True
            self.last_heartbeat = time.time()
            self.alert_sent = False
            self.monitor_thread = threading.Thread(target=self._monitor_heartbeat)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            heartbeat_logger.info("Heartbeat monitoring started")

    def stop_monitoring(self):
        """Stop the heartbeat monitoring thread"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(1.0)  # Wait for thread to finish with timeout
        heartbeat_logger.info("Heartbeat monitoring stopped")

    def update_heartbeat(self):
        """Update the timestamp of the last heartbeat"""
        self.last_heartbeat = time.time()
        self.alert_sent = False  # Reset alert flag when bot is responsive again

    def _monitor_heartbeat(self):
        """Internal method to check heartbeat and alert admins if necessary"""
        while self.monitoring:
            time.sleep(self.check_interval)
            
            current_time = time.time()
            time_since_last_beat = current_time - self.last_heartbeat
            
            # If the time since the last heartbeat exceeds the threshold, notify admins
            if time_since_last_beat > (self.check_interval * self.allowed_missed_beats) and not self.alert_sent:
                self._notify_admins_unresponsive(time_since_last_beat)
                self.alert_sent = True  # Set flag to prevent multiple alerts
            
            heartbeat_logger.debug(f"Heartbeat check: {time_since_last_beat:.1f}s since last beat")

    def _notify_admins_unresponsive(self, time_since_last_beat):
        """Send alert to admins that the bot is unresponsive"""
        current_time = datetime.datetime.now(self.timezone).strftime("%Y-%m-%d %H:%M:%S %Z")
        
        alert_message = (
            f"⚠️ BOT UNRESPONSIVE ALERT ⚠️\n\n"
            f"The bot has been unresponsive for {time_since_last_beat:.1f} seconds.\n"
            f"Timestamp: {current_time}\n"
            f"Please check the server and restart the bot if necessary."
        )
        
        for admin_id in self.admin_ids:
            try:
                self.bot.send_message(chat_id=admin_id, text=alert_message)
                heartbeat_logger.info(f"Sent unresponsive alert to admin {admin_id}")
            except Exception as e:
                heartbeat_logger.error(f"Failed to notify admin {admin_id} about unresponsive bot: {e}")

# Create a singleton instance that will be imported by other modules
heartbeat_monitor = None 