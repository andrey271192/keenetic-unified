"""Background tasks: router check, watchdog staleness, speed cleanup."""
import asyncio, logging
from datetime import datetime, timedelta
from .. import config
from ..database import save_json, load_json
from .keenetic_client import KeeneticClient
from .notifier import notify
logger = logging.getLogger("keenetic")

async def check_routers_loop(routers):
    """HTTP-check only routers NOT covered by an active watchdog heartbeat.
    Routers on remote sites report via watchdog — their online status is owned
    by check_watchdog_staleness, not by direct HTTP reachability from VPS."""
    while True:
        try:
            W = load_json(config.WATCHDOG_FILE, {})
            now = datetime.now()
            for name, cfg in list(routers.items()):
                # If watchdog sent a heartbeat in the last 20 min — skip HTTP check.
                wd_last = W.get(name, {}).get("last_seen")
                if wd_last:
                    try:
                        if (now - datetime.fromisoformat(wd_last)) < timedelta(minutes=20):
                            continue
                    except Exception:
                        pass
                ip = cfg.get("ip", "")
                if not ip: continue
                c = KeeneticClient(f"http://{ip}", cfg.get("user","admin"), cfg.get("password",""))
                online = await c.check_connection()
                prev = cfg.get("online")
                cfg["online"] = online; cfg["last_check"] = now.isoformat()
                if prev is not None and prev != online:
                    if online: await notify(name,"ROUTER_ONLINE","Роутер в сети",routers)
                    else: await notify(name,"ROUTER_OFFLINE","Роутер недоступен!",routers)
            save_json(config.ROUTERS_FILE, routers)
        except Exception as e: logger.error(f"Router check: {e}")
        await asyncio.sleep(120)

async def check_watchdog_staleness(watchdog_status, routers):
    while True:
        await asyncio.sleep(60)
        try:
            now = datetime.now(); changed = False
            for name, ws in list(watchdog_status.items()):
                last = ws.get("last_seen")
                if not last: continue
                try: delta = now - datetime.fromisoformat(last)
                except: continue
                if delta > timedelta(minutes=15) and ws.get("state") not in ("STALE","OFFLINE","DEAD"):
                    ws["state"] = "STALE"; changed = True
                    if name in routers: routers[name]["online"] = False; routers[name]["last_check"] = now.isoformat()
                    await notify(name,"WATCHDOG_STALE",f"Нет heartbeat {int(delta.total_seconds()//60)} мин",routers)
                if delta > timedelta(hours=2) and ws.get("state") != "DEAD":
                    ws["state"] = "DEAD"; changed = True
                    await notify(name,"WATCHDOG_DEAD","Watchdog мёртв >2ч",routers)
            if changed:
                save_json(config.WATCHDOG_FILE, dict(watchdog_status))
                save_json(config.ROUTERS_FILE, routers)
        except Exception as e: logger.error(f"WD check: {e}")

async def cleanup_speed_history(speed_history):
    while True:
        await asyncio.sleep(3600*6)
        try:
            cutoff = (datetime.now()-timedelta(days=7)).isoformat()
            for n in list(speed_history.keys()): speed_history[n]=[r for r in speed_history[n] if r.get("ts","")>cutoff]
            save_json(config.SPEED_FILE, speed_history)
        except Exception as e: logger.error(f"Speed cleanup: {e}")
