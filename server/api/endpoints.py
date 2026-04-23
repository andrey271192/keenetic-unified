"""API: watchdog (auto-register), sites, speed, status, hydra."""
from datetime import datetime
from fastapi import APIRouter, Request, Header, HTTPException
from fastapi.responses import Response
from ..models import (SitesReport, SitesRecheck, SpeedReport, WatchdogReport, DomainGroup, IpGroup)
from ..database import save_json
from .. import config
from ..services.notifier import notify, events
from ..services.hydra_manager import (load_hydra_config, save_hydra_config, generate_domain_conf, generate_ip_list, get_config_version, parse_domain_conf, parse_ip_list)
router = APIRouter(prefix="/api", tags=["data"])
def _chk(pwd: str):
    if config.ADMIN_PASSWORD and pwd != config.ADMIN_PASSWORD:
        raise HTTPException(401, "Неверный пароль")

@router.get("/auth")
async def auth_check(x_admin_password: str = Header("")):
    _chk(x_admin_password); return {"ok": True}

@router.post("/test_notify")
async def test_notify(x_admin_password: str = Header("")):
    _chk(x_admin_password)
    import asyncio
    from ..services.notifier import send_telegram, _email
    await send_telegram("🔔 <b>Тест уведомлений</b>\n✅ Telegram работает!\nПроверяю email...")
    email_ok = True; email_err = ""
    try:
        await asyncio.to_thread(_email,
            "Keenetic Unified — тест уведомлений",
            "<h2>✅ Email уведомления работают!</h2><p>Тестовое письмо от Keenetic Unified.</p>"
        )
    except Exception as e:
        email_ok = False; email_err = str(e)
    return {"telegram": True, "email": email_ok, "email_error": email_err, "email_to": config.SMTP_TO}

@router.post("/test_sites")
async def test_sites(request: Request, x_admin_password: str = Header("")):
    _chk(x_admin_password)
    from ..services.ssh_client import ssh_exec_verbose
    from ..services.notifier import send_telegram
    b = await request.json()
    sites = b.get("sites", ["www.canva.com", "www.instagram.com", "www.netflix.com", "www.youtube.com"])
    R, _, _, _, _ = _s()
    router_results = []
    for name, rcfg in list(R.items()):
        ip = rcfg.get("ip","") or rcfg.get("wan_ip","")
        if not ip: continue
        user = rcfg.get("user") or config.SSH_USER
        password = rcfg.get("password") or config.SSH_PASS
        # Auto-detect first UP VPN interface (nwg0-3), then check each site through it
        site_checks = "; ".join(
            f'_c=$(curl -s -o /dev/null -w "%{{http_code}}" --connect-timeout 5 --max-time 10 --interface "$VPN_IF" -L https://{s} 2>/dev/null); [ "$_c" != "000" ] && [ -n "$_c" ] && echo "{s}=OK($_c)" || echo "{s}=FAIL"'
            for s in sites
        )
        checks = (
            'VPN_IF=""; '
            'for _i in $(cat /opt/etc/vpn_list 2>/dev/null) nwg0 nwg1 nwg2 nwg3; do '
            '  ip link show "$_i" 2>/dev/null | grep -qi "state UP\\|,UP" && VPN_IF="$_i" && break; '
            'done; '
            '[ -z "$VPN_IF" ] && echo "VPN_IF=none" || echo "VPN_IF=$VPN_IF"; '
            + site_checks
        )
        r = await ssh_exec_verbose(ip, checks, user=user, password=password, timeout=60)
        site_results = {}
        vpn_if = ""
        for line in r["output"].splitlines():
            line = line.strip()
            if line.startswith("VPN_IF="):
                vpn_if = line.split("=",1)[1]
                continue
            for s in sites:
                if line.startswith(s+"="):
                    val = line.split("=",1)[1]
                    site_results[s] = val.startswith("OK")
        if vpn_if:
            router_results[-1]["vpn_if"] = vpn_if
        router_results.append({"router": name, "ok": r["ok"], "sites": site_results, "error": "" if r["ok"] else r["output"][:100]})
    # Send summary to Telegram
    lines = ["🌐 <b>Проверка сайтов с роутеров</b>\n"]
    for rr in router_results:
        if not rr["ok"]:
            lines.append(f"⚠️ <b>{rr['router']}</b>: нет SSH\n{rr['error']}")
            continue
        vpn_label = f" via <code>{rr.get('vpn_if','?')}</code>" if rr.get('vpn_if') and rr.get('vpn_if') != 'none' else " ⚠️ нет VPN-интерфейса"
        site_line = "\n".join(f"  {'✅' if v else '❌'} {k}" for k,v in rr["sites"].items())
        lines.append(f"📡 <b>{rr['router']}</b>{vpn_label}\n{site_line}")
    await send_telegram("\n\n".join(lines))
    return {"results": router_results}

def _s():
    from ..main import routers, sites_status, watchdog_status, speed_history, restart_queue
    return routers, sites_status, watchdog_status, speed_history, restart_queue

@router.post("/watchdog")
async def watchdog_heartbeat(report: WatchdogReport):
    R, _, W, _, _ = _s(); n = report.router.strip().lower(); now = datetime.now().isoformat()
    if n not in R:
        R[n] = {"ip":"","user":"admin","password":"","display_name": report.display_name or n,"web_url":"","online":True,"last_check":now,"wan_ip":report.ip or ""}
    R[n]["online"] = True; R[n]["last_check"] = now
    # WAN IP from heartbeat — save separately, don't overwrite admin-set local IP
    if report.ip: R[n]["wan_ip"] = report.ip
    if report.display_name and not R[n].get("display_name"): R[n]["display_name"] = report.display_name
    save_json(config.ROUTERS_FILE, R)
    prev = W.get(n, {}).get("state")
    W[n] = {"state":report.state,"last_seen":now,"phase":report.phase,"neo_alive":report.neo_alive,"vpn_routes":report.vpn_routes,"detail":report.detail}
    save_json(config.WATCHDOG_FILE, dict(W))
    if prev and prev != report.state:
        em = {"ALERT":"SITE_DOWN","RESTART":"NEO_RESTART","RECOVERY":"NEO_RECOVERY","CRITICAL":"NEO_CRITICAL","DEAD":"WATCHDOG_DEAD","DOMAIN_UPDATE":"DOMAIN_UPDATE"}
        await notify(n, em.get(report.state, report.state), report.detail or report.state, R)
    return {"ok": True}

@router.post("/push_sites")
async def push_sites(report: SitesReport):
    R, S, _, _, Q = _s(); n = report.router.strip().lower(); now = datetime.now().isoformat(); nr = False
    if n not in R: R[n] = {"ip":"","user":"admin","password":"","display_name":n,"web_url":"","online":True,"last_check":now}; save_json(config.ROUTERS_FILE, R)
    # Normalize site names: "youtube" -> "YouTube", "netflix" -> "Netflix"
    normalized = {}
    for site, ok in report.sites.items():
        key = site.capitalize()
        normalized[key] = ok
    for site, ok in normalized.items():
        prev = S.get(n, {}).get(site, {}).get("status")
        if n not in S: S[n] = {}
        S[n][site] = {"status": ok, "last_check": now}
        if prev is not None and prev != ok:
            if ok: await notify(n,"SITE_UP",f"✅ {site}",R)
            else: await notify(n,"SITE_DOWN",f"❌ {site}",R); nr = True
        if not ok and prev is None: nr = True
    save_json(config.SITES_FILE, dict(S))
    if nr: Q[n] = True
    return {"restart_neo": Q.pop(n, False)}

@router.post("/push_sites_recheck")
async def push_sites_recheck(report: SitesRecheck):
    R, S, _, _, _ = _s(); n = report.router.strip().lower(); now = datetime.now().isoformat()
    for site, ok in report.sites.items():
        if n not in S: S[n] = {}
        S[n][site] = {"status": ok, "last_check": now}
    save_json(config.SITES_FILE, dict(S))
    if all(report.sites.values()) and report.after_restart: await notify(n,"NEO_RECOVERY","Сайты восстановлены",R)
    elif not all(report.sites.values()) and report.after_restart: await notify(n,"NEO_CRITICAL","Сайты НЕ восстановлены!",R)
    return {"ok": True}

@router.post("/push_speed")
async def push_speed(report: SpeedReport):
    R, _, _, H, _ = _s(); n = report.router.strip().lower()
    if n not in H: H[n] = []
    H[n].append({"ts":datetime.now().isoformat(),"vpn_down":report.vpn_down,"vpn_up":report.vpn_up,"ru_down":report.ru_down,"ru_up":report.ru_up,"ping":report.ping,"ru_ping":report.ru_ping})
    save_json(config.SPEED_FILE, H)
    if 0 < report.vpn_down < 5: await notify(n,"SPEED_LOW",f"VPN: {report.vpn_down:.1f} Mbps",R)
    return {"ok": True}

@router.get("/status")
async def full_status():
    R, S, W, H, _ = _s()
    return {"routers":R,"sites":dict(S),"watchdog":dict(W),"speed":{k:v[-24:] for k,v in H.items()},"events":events[-30:]}

@router.get("/speed/{name}")
async def router_speed(name: str):
    _, _, _, H, _ = _s(); return H.get(name, [])

@router.get("/events")
async def get_events(limit: int = 50): return events[-limit:]

@router.get("/hydra/domain.conf")
async def hd(): return Response(content=generate_domain_conf(load_hydra_config()),media_type="text/plain")
@router.get("/hydra/ip.list")
async def hi(): return Response(content=generate_ip_list(load_hydra_config()),media_type="text/plain")
@router.get("/hydra/version")
async def hv(): return Response(content=get_config_version(load_hydra_config()),media_type="text/plain")
@router.get("/hydra/config")
async def hc(): return load_hydra_config().model_dump()
@router.post("/hydra/domain-group")
async def hadg(g: DomainGroup, x_admin_password: str = Header("")):
    _chk(x_admin_password); c=load_hydra_config(); c.domain_groups=[x for x in c.domain_groups if x.name!=g.name]; c.domain_groups.append(g); c.version=get_config_version(c); save_hydra_config(c); return {"ok":True,"version":c.version}
@router.post("/hydra/ip-group")
async def haig(g: IpGroup, x_admin_password: str = Header("")):
    _chk(x_admin_password); c=load_hydra_config(); c.ip_groups=[x for x in c.ip_groups if x.name!=g.name]; c.ip_groups.append(g); c.version=get_config_version(c); save_hydra_config(c); return {"ok":True,"version":c.version}
@router.delete("/hydra/domain-group/{name}")
async def hddg(name:str, x_admin_password: str = Header("")):
    _chk(x_admin_password); c=load_hydra_config(); c.domain_groups=[x for x in c.domain_groups if x.name!=name]; c.version=get_config_version(c); save_hydra_config(c); return {"ok":True}
@router.delete("/hydra/ip-group/{name}")
async def hdig(name:str, x_admin_password: str = Header("")):
    _chk(x_admin_password); c=load_hydra_config(); c.ip_groups=[x for x in c.ip_groups if x.name!=name]; c.version=get_config_version(c); save_hydra_config(c); return {"ok":True}
@router.post("/hydra/import")
async def him(request: Request, x_admin_password: str = Header("")):
    _chk(x_admin_password); b=await request.json(); c=load_hydra_config()
    if b.get("domain_conf"): c.domain_groups=parse_domain_conf(b["domain_conf"])
    if b.get("ip_list"): c.ip_groups=parse_ip_list(b["ip_list"])
    c.version=get_config_version(c); save_hydra_config(c)
    return {"ok":True,"domain_groups":len(c.domain_groups),"ip_groups":len(c.ip_groups),"version":c.version}

@router.post("/hydra/push_all")
async def push_all_routers(x_admin_password: str = Header("")):
    _chk(x_admin_password)
    from ..services.ssh_client import ssh_exec
    R, _, _, _, _ = _s()
    # Router fetches files from server via HTTP — avoids SSH command length limits
    cmd = (
        "SERVER=$(cat /opt/etc/server_url 2>/dev/null); "
        "[ -z \"$SERVER\" ] && echo 'NO_SERVER_URL' && exit 1; "
        "HR_DIR=$([ -d /opt/etc/HydraRoute ] && echo /opt/etc/HydraRoute || echo /opt/etc/hydra); "
        "mkdir -p \"$HR_DIR\"; "
        "curl -sf --connect-timeout 15 \"$SERVER/api/hydra/domain.conf\" -o \"$HR_DIR/domain.conf\" || { echo CURL_FAIL; exit 1; }; "
        "curl -sf --connect-timeout 15 \"$SERVER/api/hydra/ip.list\" -o \"$HR_DIR/ip.list\"; "
        "neo restart >/dev/null 2>&1; "
        "echo OK"
    )
    results = []
    ok = failed = 0
    for name, rcfg in list(R.items()):
        ip = rcfg.get("ip","") or rcfg.get("wan_ip","")
        if not ip:
            results.append({"router":name,"status":"skip","message":"нет IP"})
            continue
        user = rcfg.get("user") or "root"
        password = rcfg.get("password") or "keenetic"
        out = await ssh_exec(ip, cmd, user=user, password=password, timeout=60)
        if "OK" in out:
            results.append({"router":name,"status":"ok","message":"обновлено"})
            ok += 1
        else:
            results.append({"router":name,"status":"error","message":out.strip()[:200]})
            failed += 1
    return {"ok":ok,"failed":failed,"results":results}

@router.post("/ssh/all")
async def ssh_all(request: Request, x_admin_password: str = Header("")):
    _chk(x_admin_password)
    from ..services.ssh_client import ssh_exec_verbose
    b = await request.json()
    ssh_cmd = b.get("command","").strip()
    if not ssh_cmd: raise HTTPException(400, "command required")
    R, _, _, _, _ = _s()
    results = []
    ok = failed = 0
    for name, rcfg in list(R.items()):
        ip = rcfg.get("ip","") or rcfg.get("wan_ip","")
        if not ip:
            results.append({"router":name,"status":"skip","exit_code":None,"output":"нет IP","stderr":""})
            continue
        user = rcfg.get("user") or config.SSH_USER
        password = rcfg.get("password") or config.SSH_PASS
        r = await ssh_exec_verbose(ip, ssh_cmd, user=user, password=password, timeout=60)
        results.append({
            "router": name,
            "status": "ok" if r["ok"] else "error",
            "exit_code": r["exit_code"],
            "output": r["output"][:800],
            "stderr": r["stderr"][:200],
        })
        if r["ok"]: ok += 1
        else: failed += 1
    return {"ok":ok,"failed":failed,"command":ssh_cmd,"results":results}
