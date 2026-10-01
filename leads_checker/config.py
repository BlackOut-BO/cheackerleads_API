"""Конфигурация приложения"""
import os
from dotenv import load_dotenv

load_dotenv()

# Пароль для доступа к боту
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "default_password_change_me")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Abstract API (Email Reputation)
ABSTRACT_API_KEY = os.getenv("ABSTRACT_API_KEY")
ABSTRACT_API_URL = "https://emailreputation.abstractapi.com/v1/"

# ipdata.co (IP)
IPDATA_API_KEY = os.getenv("IPDATA_API_KEY")
IPDATA_API_URL = "https://api.ipdata.co/"

# numverify (Phone)
NUMVERIFY_API_KEY = os.getenv("NUMVERIFY_API_KEY")
NUMVERIFY_API_URL = "http://apilayer.net/api/validate"

# RapidAPI
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_BASE_URL = "https://rapidapi.com"

# RapidAPI Hosts
WHATSAPP_API_HOST = os.getenv("WHATSAPP_API_HOST", "whatsapp-number-validator3.p.rapidapi.com")
FACEBOOK_API_HOST = os.getenv("FACEBOOK_API_HOST", "facebook-checker.p.rapidapi.com")
GOOGLE_API_HOST = os.getenv("GOOGLE_API_HOST", "google-checker.p.rapidapi.com")
INSTAGRAM_API_HOST = os.getenv("INSTAGRAM_API_HOST", "instagram-checker.p.rapidapi.com")
SNAPCHAT_API_HOST = os.getenv("SNAPCHAT_API_HOST", "snapchat-checker.p.rapidapi.com")
X_API_HOST = os.getenv("X_API_HOST", "x-checker.p.rapidapi.com")

# Альтернативные API для WhatsApp (не через RapidAPI)
CHECKNUMBER_API_KEY = os.getenv("CHECKNUMBER_API_KEY", "")  # CheckNumber.ai API key
IDENFY_API_KEY = os.getenv("IDENFY_API_KEY", "")  # iDenfy API key

# Опции проверки
ENABLE_WHATSAPP_CHECK = os.getenv("ENABLE_WHATSAPP_CHECK", "true").lower() == "true"
WHATSAPP_API_PROVIDER = os.getenv("WHATSAPP_API_PROVIDER", "checknumber").lower()  # Только checknumber (RapidAPI и iDenfy удалены)

# Risk thresholds
RISKY_THRESHOLD = 50
SPAM_THRESHOLD = 75

# Risk weights for aggregation
IP_WEIGHT = 0.4
EMAIL_WEIGHT = 0.4
PHONE_WEIGHT = 0.2

# Proxy
PROXY_URL = os.getenv("PROXY_URL", "")  # Proxy URL для HTTP запросов (например: socks5://user:pass@host:port)
