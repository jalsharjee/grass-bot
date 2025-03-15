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
        self.base_url = "https://api.getgrass.io"
        self.auth_token = os.getenv("AUTH_TOKEN")
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.telegram_channel_id = os.getenv("TELEGRAM_CHANNEL_ID")
        self.encryption_key = os.getenv("ENCRYPTION_KEY")

        # Validate environment variables
        required_vars = {
            "AUTH_TOKEN": self.auth_token,
            "TELEGRAM_BOT_TOKEN": self.telegram_bot_token,
            "TELEGRAM_CHAT_ID": self.telegram_chat_id,
            "TELEGRAM_CHANNEL_ID": self.telegram_channel_id,
            "ENCRYPTION_KEY": self.encryption_key
        }
        for name, value in required_vars.items():
            if not value:
                logger.error(f"Missing environment variable: {name}")
                raise ValueError(f"Missing environment variable: {name}")

        # Ensure chat ID is a string (Telegram accepts it as is)
        self.telegram_chat_id = str(self.telegram_chat_id)
        self.telegram_channel_id = str(self.telegram_channel_id)

        # Setup encryption
        try:
            self.cipher = Fernet(self.encryption_key.encode())
        except Exception as e:
            logger.error(f"Invalid ENCRYPTION_KEY: {e}")
            raise ValueError(f"Invalid ENCRYPTION_KEY: {e}")

        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.auth_token}",  # Use raw token for now
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        })
        self.user_id = None
        self.running = True
        logger.info("Bot initialized successfully")

    def send_telegram_message(self, message: str, to_channel: bool = False):
        bot = Bot(self.telegram_bot_token)
        chat_id = self.telegram_channel_id if to_channel else self.telegram_chat_id
        try:
            bot.send_message(chat_id=chat_id, text=message)
            logger.info(f"Telegram message sent to {'channel' if to_channel else 'chat'}: {message}")
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")

    def sign_in(self) -> bool:
        try:
            self.send_telegram_message("Attempting to sign in to Grass API")
            response = self.session.get(f"{self.base_url}/user")  # Update endpoint later
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
        try:
            response = self.session.get(f"{self.base_url}/user")  # Update endpoint later
            response.raise_for_status()
            data = response.json()
            balance = data.get("points", 0)
            self.send_telegram_message(f"💰 Current Balance: {balance} points", to_channel=True)
            logger.info(f"Balance retrieved: {balance} points")
            return balance
        except requests.RequestException as e:
            self.send_telegram_message(f"Failed to get balance: {e}")
            logger.error(f"Failed to get balance: {e}")
            return None

    def run(self):
        self.send_telegram_message("🚜 Auto-Farming Started", to_channel=True)
        while self.running:
            if not self.sign_in():
                logger.warning("Retrying sign-in in 5 minutes")
                time.sleep(300)
                continue
            balance = self.get_balance()
            if balance is not None:
                logger.info("Farming cycle complete")
            time.sleep(3600)  # 1 hour

def main():
    try:
        bot = GrassBot()
        bot.run()
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        time.sleep(300)

if __name__ == "__main__":
    main()