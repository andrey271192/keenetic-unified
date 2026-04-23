"""Keenetic Unified v6.0 — production server.
Run: cd /opt/keenetic-unified && uvicorn server.main:app --host 0.0.0.0 --port 8000
"""
import asyncio, logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from . import config
from .database import load_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("keenetic")

routers: dict = load_json(config.ROUTERS_FILE, {})
sites_status: dict = load_json(config.SITES_FILE, {})
watchdog_status: dict = load_json(config.WATCHDOG_FILE, {})
speed_history: dict = load_json(config.SPEED_FILE, {})
restart_queue: dict = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    from .services.monitor import check_routers_loop, check_watchdog_staleness, cleanup_speed_history
    from .services.telegram_bot import telegram_bot_loop
    logger.info(f"Keenetic Unified v6.0 | {len(routers)} routers | http://{config.HOST}:{config.PORT}")
    tasks = [
        asyncio.create_task(check_routers_loop(routers)),
        asyncio.create_task(check_watchdog_staleness(watchdog_status, routers)),
        asyncio.create_task(cleanup_speed_history(speed_history)),
        asyncio.create_task(telegram_bot_loop()),
    ]
    yield
    for t in tasks: t.cancel()

app = FastAPI(title="Keenetic Unified", version="6.0", lifespan=lifespan)
from .api.routers import router as r1
from .api.endpoints import router as r2
app.include_router(r1); app.include_router(r2)

TPL = Path(__file__).parent / "templates"

@app.get("/", response_class=HTMLResponse)
async def dashboard(): return (TPL/"dashboard.html").read_text(encoding="utf-8")

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(): return (TPL/"admin.html").read_text(encoding="utf-8")

@app.get("/stats/{name}", response_class=HTMLResponse)
async def stats_page(name: str): return (TPL/"stats.html").read_text(encoding="utf-8")

@app.get("/domains", response_class=HTMLResponse)
async def domains_page(): return (TPL/"domains.html").read_text(encoding="utf-8")
