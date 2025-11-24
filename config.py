# Telegram bot token (get it from @BotFather)
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"

# Your Telegram numeric user ID (admin)
ADMIN_ID = 123456789

# Cloudflare API base URL
API_URL = "https://api.cloudflare.com/client/v4"

# File name where Cloudflare accounts (API tokens) are stored
ACCOUNTS_FILE = "accounts.json"

# Icons used in the bot UI
ICONS = {
    # Main actions
    "ADD": "➕",
    "EDIT": "✏️",
    "DELETE": "🗑️",
    "BACK": "🔙",
    "REFRESH": "🔄",
    "CANCEL": "❌",
    "CONFIRM": "✅",

    # Main menu
    "ZONES": "🌐",
    "ACCOUNTS": "👤",
    "STATS": "📊",
    "HELP": "ℹ️",
    "LOGOUT": "🚪",

    # Status
    "ACTIVE": "✅",
    "PENDING": "⏳",
    "PROXIED": "☁️",  # CDN ON
    "DNS_ONLY": "➡️",  # CDN OFF
    "SUCCESS": "✅",
    "ERROR": "❌",
    "INFO": "ℹ️",
    "WARNING": "⚠️",

    # DNS record types
    "A": "🇦",
    "AAAA": "🇦",
    "CNAME": "🇨",
    "TXT": "🇹",
    "MX": "🇲",
    "NS": "🇳",

    # Other
    "DEFAULT": "🔹",
    "TARGET": "🎯",
    "NAME": "🏷️",
    "TYPE": "🔹",
    "TTL": "⏱️",
    "KEY": "🔑",
    "SPINNER": "⏳",
}
