"""Notifications: Telegram + Email (async). Email goes to SMTP by default."""
import asyncio, logging, smtplib
from datetime import datetime
from email.mime.text import MIMEText
import httpx
from .. import config
from ..database import save_json, load_json

logger = logging.getLogger("keenetic")
events: list = load_json(config.EVENTS_FILE, [])
# key -> last notification datetime; avoids duplicate bursts within cooldown window
_last: dict = {}
# events that should always fire on state-change (no cooldown needed — already gated upstream)
_NO_COOLDOWN = {"ROUTER_ONLINE", "ROUTER_OFFLINE", "NEO_RECOVERY", "NEO_CRITICAL"}
_COOLDOWN_SEC = 300  # 5 min cooldown for repeated identical alerts
EMOJI = {"SITE_DOWN":"❌","SITE_UP":"✅","NEO_RESTART":"🔄","NEO_RECOVERY":"✅",
    "NEO_CRITICAL":"🚨","WATCHDOG_DEAD":"💀","WATCHDOG_STALE":"⚠️",
    "ROUTER_OFFLINE":"📡❌","ROUTER_ONLINE":"📡✅","SPEED_LOW":"🐌","DOMAIN_UPDATE":"📋"}

async def send_telegram(msg):
    if not config.TELEGRAM_TOKEN: return
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            await c.post(f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id":config.TELEGRAM_CHAT_ID,"text":msg,"parse_mode":"HTML"})
    except Exception as e: logger.error(f"TG: {e}")

def _email(subj, body):
    if not config.SMTP_USER: return
    try:
        m = MIMEText(body, "html"); m["Subject"] = subj; m["From"] = config.SMTP_USER; m["To"] = config.SMTP_TO
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as s:
            s.starttls(); s.login(config.SMTP_USER, config.SMTP_PASS); s.send_message(m)
    except Exception as e: logger.error(f"Email: {e}")

async def notify(router, event, detail, routers=None):
    key = f"{router}:{event}"
    now = datetime.now()
    if event not in _NO_COOLDOWN:
        last_ts = _last.get(key)
        if last_ts and (now - last_ts).total_seconds() < _COOLDOWN_SEC:
            return
    _last[key] = now
    ts = datetime.now().isoformat()
    events.append({"ts": ts, "router": router, "event": event, "detail": detail})
    if len(events) > 500: events[:] = events[-500:]
    save_json(config.EVENTS_FILE, events)
    emoji = EMOJI.get(event, "ℹ️")
    dn = router
    if routers and router in routers: dn = routers[router].get("display_name") or router
    msg = f"{emoji} <b>{dn}</b>\n{detail}"
    await send_telegram(msg)
    # Email дублирует ВСЕ уведомления
    await asyncio.to_thread(_email, f"Keenetic: {event} — {dn}", f"<p>{msg}</p>")
    logger.info(f"Notify: {router}|{event}|{detail}")
