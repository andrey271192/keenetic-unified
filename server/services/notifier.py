"""Notifications: Telegram + Email (async). Email goes to SMTP by default."""
import asyncio, logging, smtplib
from datetime import datetime
from email.mime.text import MIMEText
import httpx
from .. import config
from ..database import save_json, load_json

logger = logging.getLogger("keenetic")
events: list = load_json(config.EVENTS_FILE, [])

# Per-router incident tracker: {router: {incident_group: count}}
# Incident resets when a RECOVERY event arrives.
_incident_count: dict = {}

# Events that signal the START of an incident (limited to 3 notifications)
_INCIDENT_EVENTS = {"NEO_RESTART", "NEO_CRITICAL", "WATCHDOG_STALE", "WATCHDOG_DEAD", "SITE_DOWN", "SPEED_LOW"}
# Events that CLOSE an incident and reset the counter for that router
_RECOVERY_EVENTS = {"ROUTER_ONLINE", "NEO_RECOVERY"}

MAX_INCIDENT_NOTIFY = 3

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
    now = datetime.now()

    # Recovery events reset the incident counter
    if event in _RECOVERY_EVENTS:
        _incident_count.pop(router, None)

    # Incident events are limited to MAX_INCIDENT_NOTIFY per open incident
    if event in _INCIDENT_EVENTS:
        count = _incident_count.get(router, 0) + 1
        _incident_count[router] = count
        if count > MAX_INCIDENT_NOTIFY:
            logger.info(f"Notify suppressed (incident #{count}>{MAX_INCIDENT_NOTIFY}): {router}|{event}")
            return
        # Add count suffix so user sees "1/3", "2/3", "3/3"
        detail = f"{detail} [{count}/{MAX_INCIDENT_NOTIFY}]"

    ts = now.isoformat()
    events.append({"ts": ts, "router": router, "event": event, "detail": detail})
    if len(events) > 500: events[:] = events[-500:]
    save_json(config.EVENTS_FILE, events)

    emoji = EMOJI.get(event, "ℹ️")
    dn = router
    if routers and router in routers: dn = routers[router].get("display_name") or router
    msg = f"{emoji} <b>{dn}</b>\n{detail}"
    await send_telegram(msg)
    await asyncio.to_thread(_email, f"Keenetic: {event} — {dn}", f"<p>{msg}</p>")
    logger.info(f"Notify: {router}|{event}|{detail}")
