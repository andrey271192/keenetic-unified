"""Configuration — all paths Path objects, auto-creates missing files."""
import os, json, logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("keenetic")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

SMTP_USER = os.getenv("SMTP_USER", "keenetic@school29.com")
SMTP_PASS = os.getenv("SMTP_PASS", "kispvgycalrgjfyb")
SMTP_TO = os.getenv("SMTP_TO", "bobyrevad@gmail.com")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# SSH defaults for all routers
SSH_USER = os.getenv("SSH_USER", "root")
SSH_PASS = os.getenv("SSH_PASS", "keenetic")

ROUTERS_FILE = DATA_DIR / "routers.json"
SITES_FILE = DATA_DIR / "sites.json"
WATCHDOG_FILE = DATA_DIR / "watchdog.json"
SPEED_FILE = DATA_DIR / "speed.json"
EVENTS_FILE = DATA_DIR / "events.json"
HYDRA_FILE = DATA_DIR / "hydra_config.json"

_DEFAULTS = {
    ROUTERS_FILE: {}, SITES_FILE: {}, WATCHDOG_FILE: {},
    SPEED_FILE: {}, EVENTS_FILE: [],
    HYDRA_FILE: {"version": "1.0", "domain_groups": [], "ip_groups": []},
}

def ensure_data_files():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for fp, default in _DEFAULTS.items():
        if not fp.exists():
            try:
                fp.write_text(json.dumps(default, ensure_ascii=False, indent=2))
            except Exception as e:
                logger.error(f"Cannot create {fp}: {e}")

ensure_data_files()
