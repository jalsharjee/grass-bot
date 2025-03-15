import requests
import time
import json
import random
import os
from datetime import datetime, timedelta
from typing import Optional
from fake_useragent import UserAgent
from cryptography.fernet import Fernet  # Requires: pip install cryptography
import logging
from threading import Thread

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@YourChannelName")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key())  # Generate or set via env
PROXY = os.getenv("PROXY", "127.0.0.1:8080")
PUBLIC_PROXIES = [
    "http://45.76.215.34:8080",
    "http://103.221.254.102:49617",
    "http://198.199.86.148:8080"
    
]


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class GrassBot:
    def __init__(self, auth_token: str):
        self.base_url = "https://api.getgrass.io"
        self.cipher = Fernet(ENCRYPTION_KEY)
        self.auth_token = self._encrypt_token(auth_token)
        self.primary_proxy = f"http://{PROXY}"
        self.ua = UserAgent()
        self.user_id = None
        self.session_file = "session_snapshot.json"
        self.running = True
        self._initialize_session()
        self._load_session_snapshot()

    def _encrypt_token(self, token: str) -> str:
        """Encrypt the authentication token"""
        return self.cipher.encrypt(token.encode()).decode()

    def _decrypt_token(self) -> str:
        """Decrypt the authentication token"""
        return self.cipher.decrypt(self.auth_token.encode()).decode()

    def _initialize_session(self):
        """Initialize session with proxy and rotating User-Agent"""
        self.session = requests.Session()
        self._update_headers()
        self._set_proxy(self.primary_proxy)

    def _update_headers(self):
        """Rotate User-Agent for each session"""
        self.session.headers.update({
            "Authorization": f"Bearer {self._decrypt_token()}",
            "Content-Type": "application/json",
            "User-Agent": self.ua.random
        })

    def _set_proxy(self, proxy_url: str):
        """Set proxy for the session"""
        proxies = {"http": proxy_url, "https": proxy_url}
        self.session.proxies.update(proxies)
        self.send_telegram_message(f"Using proxy: {proxy_url}")
        logger.info(f"Proxy set to: {proxy_url}")

    def _switch_to_public_proxy(self):
        """Fallback to a random public proxy"""
        available_proxy = random.choice(PUBLIC_PROXIES)
        self._set_proxy(available_proxy)
        return available_proxy

    def _save_session_snapshot(self):
        """Save session state"""
        snapshot = {
            "user_id": self.user_id,
            "proxy": self.session.proxies.get("http"),
            "last_user_agent": self.session.headers.get("User-Agent"),
            "timestamp": int(time.time())
        }
        with open(self.session_file, "w") as f:
            json.dump(snapshot, f)
        self.send_telegram_message("Session snapshot saved")

    def _load_session_snapshot(self):
        """Load session state"""
        try:
            with open(self.session_file, "r") as f:
                snapshot = json.load(f)
                self.user_id = snapshot.get("user_id")
                if snapshot.get("proxy"):
                    self._set_proxy(snapshot["proxy"])
                if snapshot.get("last_user_agent"):
                    self.session.headers["User-Agent"] = snapshot["last_user_agent"]
            self.send_telegram_message("Session snapshot loaded")
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def sign_in(self) -> bool:
        """Verify authentication"""
        try:
            response = self.session.get(f"{self.base_url}/user")
            response.raise_for_status()
            user_data = response.json()
            self.user_id = user_data.get("userId")
            self.send_telegram_message(f"Successfully signed in as {user_data.get('email')}")
            self._save_session_snapshot()
            return True
        except requests.RequestException as e:
            self.send_telegram_message(f"Sign-in failed: {str(e)}")
            logger.error(f"Sign-in failed: {str(e)}")
            self._switch_to_public_proxy()
            return False

    def get_points_balance(self) -> Optional[float]:
        """Retrieve points balance"""
        try:
            self._update_headers()
            response = self.session.get(f"{self.base_url}/user/points")
            response.raise_for_status()
            balance_data = response.json()
            balance = balance_data.get("points", 0.0)
            self.send_telegram_message(f"Points balance retrieved: {balance} points")
            self.send_channel_notification(f"💰 Current Balance: {balance} points")
            logger.info(f"Current balance: {balance} points")
            self._save_session_snapshot()
            return balance
        except requests.RequestException as e:
            self.send_telegram_message(f"Balance retrieval failed: {str(e)}")
            logger.error(f"Balance retrieval failed: {str(e)}")
            self._switch_to_public_proxy()
            return None

    def farm_points(self, source: str, volume: int, duration: int) -> Optional[float]:
        """Farm points"""
        if not self.user_id:
            self.send_telegram_message("Cannot farm points: Not signed in")
            return None

        payload = {
            "userId": self.user_id,
            "trafficSource": source,
            "trafficVolume": volume,
            "duration": duration,
            "timestamp": int(time.time())
        }

        try:
            self._update_headers()
            self.send_telegram_message(f"Farming attempt - Source: {source}, Volume: {volume}, Duration: {duration}s")
            response = self.session.post(f"{self.base_url}/traffic/farm", json=payload)
            response.raise_for_status()
            farm_data = response.json()
            points_earned = farm_data.get("pointsEarned", 0.0)
            self.send_telegram_message(f"Farming successful! Earned: {points_earned} points")
            self.send_channel_notification(f"🌾 Farming Complete\nSource: {source}\nVolume: {volume}\nDuration: {duration}s\nPoints Earned: {points_earned}")
            logger.info(f"Farming result: Earned {points_earned} points")
            self._save_session_snapshot()
            return points_earned
        except requests.RequestException as e:
            self.send_telegram_message(f"Farming error: {str(e)}")
            logger.error(f"Farming error: {str(e)}")
            self._switch_to_public_proxy()
            return None

    def start_farming(self, interval_minutes: int = 60, source: str = "organic", volume: int = 1000, duration: int = 3600):
        """Automate farming for 24 hours with restart"""
        if not self.user_id:
            self.send_telegram_message("Cannot start farming: Not signed in")
            return

        self.send_telegram_message(f"Starting auto-farming with interval: {interval_minutes} minutes")
        self.send_channel_notification(f"🚜 Auto-Farming Started\nInterval: {interval_minutes} minutes")
        start_time = datetime.now()
        cycle_count = 0

        while self.running and (datetime.now() - start_time) < timedelta(hours=24):
            cycle_count += 1
            self.send_telegram_message(f"Starting farming cycle #{cycle_count}")
            
            points_earned = self.farm_points(source, volume, duration)
            balance = self.get_points_balance()
            if balance is not None and points_earned is not None:
                self.send_telegram_message(f"Cycle #{cycle_count} complete - Total balance: {balance} points")
            
            self.send_telegram_message(f"Waiting {interval_minutes} minutes until next cycle...")
            time.sleep(interval_minutes * 60)

        if self.running:
            self.send_telegram_message("24-hour cycle complete, restarting...")
            self.restart()

    def send_telegram_message(self, message: str):
        """Send log message to Telegram chat"""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.warning("Telegram not configured: " + message)
            return

        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"}
            requests.post(url, json=payload, timeout=10).raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")

    def send_channel_notification(self, message: str):
        """Send update to Telegram channel"""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
            logger.warning("Telegram channel not configured: " + message)
            return

        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHANNEL_ID, "text": f"📢 Grass Farming Update\n{message}\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
            requests.post(url, json=payload, timeout=10).raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram channel notification: {str(e)}")

    def restart(self):
        """Restart the bot"""
        self.running = False
        self.session.close()
        logger.info("Restarting bot...")
        self.__init__(self._decrypt_token())
        Thread(target=self.run).start()

    def run(self):
        """Main run loop with error handling"""
        while True:
            try:
                if self.sign_in():
                    self.get_points_balance()
                    self.start_farming()
                else:
                    logger.error("Initial sign-in failed")
                    time.sleep(300)  # Wait 5 minutes before retry
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                self.send_telegram_message(f"Bot crashed: {str(e)}. Restarting in 5 minutes...")
                time.sleep(300)  # Wait 5 minutes before restart
                self.restart()

def main():
    auth_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IkJseGtPeW9QaWIwMlNzUlpGeHBaN2JlSzJOSEJBMSJ9.eyJ1c2VySWQiOiIydUV1QmI5NjhINxwHaUFpTEdmcUJXUUhoT2YiLCJlbWFpbCI6ImFsc2hhcmplZWpAZ21haWwuY29tIiwic2NvcGUiOiJVU0VSIiwiaWF0IjoxNzQxOTMxMTMwLCJuYmYiOjE3NDE5MzExMzAsImV4cCI6MTc3MzAzNTEzMCwiYXVkIjoid3luZC11c2VycyIsImlzcyI6Imh0dHBzOi8vd3luZC5zMy5hbWF6b25hd3MuY29tL3B1YmxpYyJ9.O6sW56gTDc0XW3KD2LiFTREm6v2aZfxN5JelGpP2IC8WhZDQkaIXM2xKRcQPYN6XbG9jeUcfZuV7L8zkMOnZIEt4hwz8fiuWJlVDb6kGAlEBUwYSmaoHEZetKAbrKByxgJkY1xjkK2Nqz_3j3Yc9pDU5U-weIqM-DrWfu2H_hnJ5klZrt3K_JjsDChJF0BWGpD9dZn9ZKd29qjfkFpVcK8mt6IkfuLb3zfRWkmbFkBfdd-_gcBTwXJZQu0cX2XGuQhm2qvnAbJMtypR2XLcHJTRwXpjBeduvlWv2ySkZxFnt_N6Ixm9nGvIJGcY2KvsljagMIhqonO65bHPF1dSUQw"
    bot = GrassBot(auth_token)
    Thread(target=bot.run).start()

if __name__ == "__main__":
    main()