import os
import sys

# Update path to import creds
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

try:
    import creds
    API_KEY = creds.api_key
    CLIENT_CODE = creds.client_code
    CLIENT_PIN = creds.client_pin
    TOTP_CODE = creds.totp_code

    TELEGRAM_BOT_TOKEN = creds.telegram_bot_token
    TELEGRAM_CHAT_ID = creds.telegram_chat_id
    
    ANTHROPIC_API_KEY = getattr(creds, 'anthropic_api_key', '')
except ImportError:
    print("Warning: creds.py not found or invalid.")
    API_KEY = CLIENT_CODE = CLIENT_PIN = TOTP_CODE = ""
    TELEGRAM_BOT_TOKEN = TELEGRAM_CHAT_ID = ""
    ANTHROPIC_API_KEY = ""

# Trading settings
DRY_RUN = True
POLL_INTERVAL = 60
INTERVAL = "FIVE_MINUTE"

LOG_DIR = os.path.join(parent_dir, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
