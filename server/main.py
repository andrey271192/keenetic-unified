"""Keenetic Unified v6.0 — production server.
Run: cd /opt/keenetic-unified && uvicorn server.main:app --host 0.0.0.0 --port 8000

Автор: GitHub / Boosty / Telegram (см. author_brand.py, username — AUTHOR_TELEGRAM_USERNAME в .env).
"""
import asyncio, logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from . import config
from .database import load_json
from .author_brand import inject_brand_html

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
    logger.info(
        "Author strip: https://github.com/andrey271192 · boosty · t.me/%s",
        config.AUTHOR_TELEGRAM_USERNAME,
    )
    tasks = [
        asyncio.create_task(check_routers_loop(routers)),
        asyncio.create_task(check_watchdog_staleness(watchdog_status, routers)),
        asyncio.create_task(cleanup_speed_history(speed_history)),
        asyncio.create_task(telegram_bot_loop()),
    ]
    yield
    for t in tasks: t.cancel()

_app_desc = (
    f"Автор: GitHub andrey271192, Boosty, t.me/{config.AUTHOR_TELEGRAM_USERNAME}"
)
app = FastAPI(
    title="Keenetic Unified",
    version="6.0",
    lifespan=lifespan,
    description=_app_desc,
)
from .api.routers import router as r1
from .api.endpoints import router as r2
app.include_router(r1); app.include_router(r2)

TPL = Path(__file__).parent / "templates"


def _read_tpl(name: str) -> str:
    raw = (TPL / name).read_text(encoding="utf-8")
    return inject_brand_html(raw, config.AUTHOR_TELEGRAM_USERNAME)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return _read_tpl("dashboard.html")


@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    return _read_tpl("admin.html")


@app.get("/stats/{name}", response_class=HTMLResponse)
async def stats_page(name: str):
    return _read_tpl("stats.html")


@app.get("/domains", response_class=HTMLResponse)
async def domains_page():
    return _read_tpl("domains.html")
