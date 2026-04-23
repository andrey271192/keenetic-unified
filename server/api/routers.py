"""Router CRUD — password protected."""
from fastapi import APIRouter, Header, HTTPException
from ..models import RouterConfig
from ..database import save_json
from .. import config
router = APIRouter(prefix="/api", tags=["routers"])
def _r():
    from ..main import routers
    return routers

@router.get("/routers")
async def list_routers(): return _r()

@router.post("/routers/{name}")
async def add_router(name: str, cfg: RouterConfig, x_admin_password: str = Header("")):
    if config.ADMIN_PASSWORD and x_admin_password != config.ADMIN_PASSWORD:
        raise HTTPException(401, "Wrong password")
    r = _r(); r[name] = {**cfg.model_dump(), "online": None, "last_check": None}
    save_json(config.ROUTERS_FILE, r); return {"ok": True}

@router.delete("/routers/{name}")
async def delete_router(name: str, x_admin_password: str = Header("")):
    if config.ADMIN_PASSWORD and x_admin_password != config.ADMIN_PASSWORD:
        raise HTTPException(401, "Wrong password")
    r = _r(); r.pop(name, None); save_json(config.ROUTERS_FILE, r); return {"ok": True}
