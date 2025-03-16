import requests
from telegram import Bot
import time
import random
import os
from cryptography.fernet import Fernet

# Constants
BASE_URL = "https://api.getgrass.io"
TELEGRAM_BOT_TOKEN = "7591472038:AAFDV7boZpL4-zfkwGzigoK0uPBppLHK0Ys"  # Replace with your Telegram bot token
TELEGRAM_CHAT_ID = "@GrassFarmingUpdates"     # Replace with your Telegram channel username or chat ID

# Proxy settings
# Proxy settings
PRIMARY_PROXY = ""  # No primary proxy
PUBLIC_PROXIES = [
    "http://97.70.7.157:80",
    "http://71.14.218.2:8080",
    "http://184.169.154.119:80"
]

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
]

# Encryption key (generate once and store securely)
ENCRYPTION_KEY = b'EZ9g8UuodmukSJdg8padybtzpMchvh7nTMsL7upuehc='  # Replace with your actual encryption key
cipher_suite = Fernet(ENCRYPTION_KEY)

# Encrypted token (replace with your encrypted token)
ENCRYPTED_AUTH_TOKEN = b'gAAAAABn1ix2ZhuicboHRxZD_WRr8cbKHnQNmq2RqrKHX--NS3-vNrfEH6n6i8WDc3IgwvyyOfsidxAHn5QGJk1geAbBRFt0zIjbDj_--8_lGm0ialiPpNrjETaTaGProXBNuL9PU8J5OlYcAol-g7ra1TMM8dd1BMDaa7hMK7MTJR5w4erOUnVvjK6B03qR3B1cibrX_1hfAtXXSNCHCosSkSFZso0RvgtZTnhfKxvS9fv1zLGycQ0FjFHWm_PTkWfc_g5aWLO89ObkeIOOit6Xy69zYQQV-5nhP2wv8LeJkFPuOz2TJiXSHB-fueFQMWtclIWZxFm3LNP0ucS2zjtPIV9hrEDDHazK2D6FpbOLPA3IkvJ_ajpLVkLceD0ML_FjpPyt-b-aaT-ciZje7MrBGIO6AwJfvQZkjFFhXLOm3LSlp_089acrZzDc9in0n1UD5j1DzHmq00KhtDrO--YvTDt0ZWOFIdc9eUZbp_NpG8Qy9Kq_Q1n1OYJ3b9wFYrnjyUSJFqmWf2gbv-8QFWVisRCHoXM7ce8l5lKWPyr-OuUtfBj7VwEIyoJFFX4M8GCw7ZnH1oZzvkClYejYyAPS_g2fb7voQlJmAm2zOfQatiSi6Alg3G1CFVjfVSJihOsB2W7ewpYZ9GCWJXDEBrBsiCHebQjbyjTpDTWYrtqOc2YElDsOqznkUqqRwSrgGe1UmdP3rP4TqFhuBuf9f5DmBldzq14ZDC_Qb-4SgIpyZGpxdGr9DldxEOht2_lraTFIp10gTMD7k-Wf34Hcy0J4pqphsnavHKO3lqizkZX17yWlJ7oM2qJdTgLYFqpUuajnCCqsVNUD-lEtN-MUaZg0nUXj0Vzt54HVF8pnuCAWzCEg6R_w1GkJnnxn0WIqSzhnSqrIQ1lFGBImo2C-sBmTfIAd_AB8gfTBKUAAgf179j2nuwVjMlW7pb2elvyYDF7DfCr57dWBVUs5FE0Oo86MAWogPGhBL6_Q6wk-TAcV3EVjCykR6Tc='

# Decrypt the token
def decrypt_token(encrypted_token):
    return cipher_suite.decrypt(encrypted_token).decode()

AUTH_TOKEN = decrypt_token(ENCRYPTED_AUTH_TOKEN)

# Session management
def create_session(proxy=None):
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": random.choice(USER_AGENTS)
    })
    if proxy:
        session.proxies.update({"http": proxy, "https": proxy})
    return session

# Proxy fallback mechanism
def get_proxy():
    try:
        test_url = "https://api.getgrass.io/health"
        response = requests.get(test_url, proxies={"http": PRIMARY_PROXY, "https": PRIMARY_PROXY}, timeout=5)
        if response.status_code == 200:
            print("Primary proxy is working.")
            return PRIMARY_PROXY
    except Exception:
        print("Primary proxy is unavailable. Falling back to a public proxy.")
    return random.choice(PUBLIC_PROXIES)

# Enhanced request function
def send_request(method, endpoint, data=None):
    proxy = get_proxy()
    session = create_session(proxy)
    try:
        url = f"{BASE_URL}{endpoint}"
        if method.upper() == "GET":
            response = session.get(url)
        elif method.upper() == "POST":
            response = session.post(url, json=data)
        else:
            raise ValueError("Unsupported HTTP method.")
        if response.status_code in [200, 201]:
            print(f"Request successful via proxy: {proxy}")
            return response
        else:
            print(f"Request failed with status code: {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        print(f"Error occurred while sending request via proxy: {proxy}, Error: {e}")
        return None

# Farm points
def farm_points(source, volume, duration):
    endpoint = "/traffic/farm"
    payload = {"source": source, "volume": volume, "duration": duration}
    response = send_request("POST", endpoint, data=payload)
    if response:
        result = response.json()
        earned_points = result.get("earnedPoints", 0)
        print(f"Successfully farmed {earned_points} points!")
        notify_farming_progress(source, volume, duration, earned_points)
        return result
    else:
        print("Failed to farm points.")
        send_telegram_message("⚠️ Farming session failed. Retrying in 5 minutes...")
        return None

# Check balance
def check_balance():
    response = send_request("GET", "/user/points")
    if response:
        points_data = response.json()
        points = points_data.get("points", 0)
        print(f"Current balance: {points} points")
        notify_current_balance(points)
        return points
    return None

# Telegram notifications
def send_telegram_message(message):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("Telegram message sent successfully!")
        return True
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
        return False

def notify_farming_progress(source, volume, duration, earned_points):
    message = (
        f"🌾 *Farming Progress Update* 🌾\n\n"
        f"Source: `{source}`\n"
        f"Volume: `{volume}`\n"
        f"Duration: `{duration} minutes`\n"
        f"Earned Points: `{earned_points}`\n"
    )
    send_telegram_message(message)

def notify_current_balance(balance):
    message = (
        f"💰 *Current Point Balance* 💰\n\n"
        f"Balance: `{balance} points`\n"
    )
    send_telegram_message(message)

# Auto-farming with continuous operation
def auto_farm():
    source = "social_media"
    volume = 100
    duration = 10
    while True:
        try:
            print(f"Starting farming session: Source={source}, Volume={volume}, Duration={duration} minutes")
            farm_points(source, volume, duration)
            if random.randint(1, 3) == 3:
                check_balance()
            time.sleep(300)  # Farm every 5 minutes
        except Exception as e:
            print(f"Critical error: {e}. Restarting in 1 minute...")
            send_telegram_message(f"⚠️ Critical error: {e}. Restarting in 1 minute...")
            time.sleep(60)

# Main function
def main():
    print("Starting auto-farming...")
    while True:
        try:
            auto_farm()
        except Exception as e:
            print(f"Main loop error: {e}. Restarting in 1 minute...")
            send_telegram_message(f"⚠️ Main loop error: {e}. Restarting in 1 minute...")
            time.sleep(60)

if __name__ == "__main__":
    main()