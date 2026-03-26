import pyotp
from SmartApi import SmartConnect
from logzero import logger
from src.config import API_KEY, CLIENT_CODE, CLIENT_PIN, TOTP_CODE

def connect_smartapi() -> SmartConnect:
    """Authenticate with AngleOne SmartAPI and return active client object."""
    if not API_KEY or API_KEY == "YOUR_SMART_API_KEY":
        logger.error("API credentials are not set properly in creds.py")
        return None
        
    try:
        smart_api = SmartConnect(API_KEY)
        totp = pyotp.TOTP(TOTP_CODE).now()
        data = smart_api.generateSession(CLIENT_CODE, CLIENT_PIN, totp)
        if data.get("status") is False:
            logger.error(f"SmartAPI login failed: {data.get('message')}")
            return None
        logger.info("SmartAPI session established successfully.")
        return smart_api
    except Exception as e:
        logger.error(f"Error during SmartAPI login: {e}")
        return None
