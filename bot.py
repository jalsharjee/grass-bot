import os
import time
import requests
import logging
from telegram import Bot
from telegram.error import TelegramError
from cryptography.fernet import Fernet

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class GrassBot:
    def __init__(self):
        self.base_url = "https://api.getgrass.io"  # Base URL
        self.auth_token = os.getenv("AUTH_TOKEN")  # Grass API token
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.telegram_channel_id = os.getenv("TELEGRAM_CHANNEL_ID")
        self.encryption_key = os.getenv("ENCRYPTION_KEY").encode()
        self.cipher = Fernet(self.encryption_key)
        self.session = requests.Session()
        self.user_id = None
        self.running = True

        # Validate required env vars
        if not all([self.auth_token, self.telegram_bot_token, self.telegram_chat_id, self.telegram_channel_id]):
            raise ValueError("Missing required environment variables")

        # Set headers
        self.session.headers.update({
            "Authorization": f"Bearer {self.cipher.decrypt(self._encrypt_token(self.auth_token)).decode()}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        })

    def _encrypt_token(self, token: str) -> bytes:
        """Encrypt the auth token."""
        return self.cipher.encrypt(token.encode())

    def send_telegram_message(self, message: str, to_channel: bool = False):
        """Send a message to Telegram chat or channel."""
        bot = Bot(self.telegram_bot_token)
        chat_id = self.telegram_channel_id if to_channel else self.telegram_chat_id
        try:
            bot.send_message(chat_id=chat_id, text=message)
            logger.info(f"Telegram message sent to {'channel' if to_channel else 'chat'}: {message}")
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")

    def sign_in(self) -> bool:
        """Sign in to Grass API."""
        try:
            self.send_telegram_message("Attempting to sign in to Grass API")
            # Replace '/user' with the correct endpoint after testing
            response = self.session.get(f"{self.base_url}/user")
            response.raise_for_status()
            user_data = response.json()
            self.user_id = user_data.get("userId")
            email = user_data.get("email", "unknown")
            self.send_telegram_message(f"Successfully signed in as {email}", to_channel=True)
            logger.info(f"Signed in: user_id={self.user_id}, email={email}")
            return True
        except requests.RequestException as e:
            self.send_telegram_message(f"Sign-in failed: {str(e)}")
            logger.error(f"Sign-in failed: {e}")
            return False

    def get_balance(self):
        """Fetch current Grass points balance."""
        try:
            # Adjust endpoint as needed (e.g., '/points' or '/balance')
            response = self.session.get(f"{self.base_url}/user")  # Temporary, update later
            response.raise_for_status()
            data = response.json()
            balance = data.get("points", 0)  # Adjust key based on API response
            self.send_telegram_message(f"💰 Current Balance: {balance} points", to_channel=True)
            logger.info(f"Balance retrieved: {balance} points")
            return balance
        except requests.RequestException as e:
            self.send_telegram_message(f"Failed to get balance: {e}")
            logger.error(f"Failed to get balance: {e}")
            return None

    def run(self):
        """Main bot loop."""
        self.send_telegram_message("🚜 Auto-Farming Started", to_channel=True)
        while self.running:
            if not self.sign_in():
                logger.warning("Retrying sign-in in 5 minutes")
                time.sleep(300)
                continue

            balance = self.get_balance()
            if balance is not None:
                logger.info("Farming cycle complete")
            else:
                logger.warning("Balance fetch failed, retrying")

            # Sleep for 1 hour (adjust as needed)
            time.sleep(3600)

def main():
    try:
        bot = GrassBot()
        bot.run()
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        time.sleep(300)  # Restart after 5 minutes

if __name__ == "__main__":
    main()