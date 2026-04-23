"""Telegram bot — full datacenter control panel.
Commands: /status /router /ssh /neo /reboot /ping /uptime /interfaces
          /watchdog /speed /domains /update /events /help
"""
import asyncio, logging
from datetime import datetime
import httpx
from .. import config
from ..database import load_json, save_json
from .ssh_client import ssh_exec

logger = logging.getLogger("keenetic.tg")
_offset = 0

async def telegram_bot_loop():
    global _offset
    if not config.TELEGRAM_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.info("TG bot disabled"); return
    logger.info("TG bot started")
    while True:
        try:
            async with httpx.AsyncClient(timeout=35) as c:
                r = await c.get(f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/getUpdates",
                    params={"offset": _offset, "timeout": 30})
                if r.status_code != 200: await asyncio.sleep(5); continue
                for upd in r.json().get("result", []):
                    _offset = upd["update_id"] + 1
                    msg = upd.get("message", {}); text = msg.get("text", "").strip()
                    chat_id = msg.get("chat", {}).get("id")
                    if not text or not chat_id or str(chat_id) != str(config.TELEGRAM_CHAT_ID): continue
                    reply = await _handle(text)
                    if reply:
                        # Split long messages
                        for chunk in [reply[i:i+4000] for i in range(0, len(reply), 4000)]:
                            await c.post(f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
                                json={"chat_id": chat_id, "text": chunk, "parse_mode": "HTML"})
        except asyncio.CancelledError: break
        except Exception as e: logger.error(f"TG: {e}"); await asyncio.sleep(10)

def _get_router_ip(name):
    """Returns (ip, display_name, real_key, ssh_user, ssh_pass)."""
    R = load_json(config.ROUTERS_FILE, {})
    r = R.get(name)
    real_name = name
    if not r:
        for k, v in R.items():
            if k.lower() == name.lower():
                r = v; real_name = k; break
    if not r: return None, None, None, None, None
    ip = r.get("ip", "") or r.get("wan_ip", "")
    dn = r.get("display_name") or real_name
    ssh_user = r.get("user") or config.SSH_USER
    ssh_pass = r.get("password") or config.SSH_PASS
    if not ip: return "", dn, real_name, ssh_user, ssh_pass
    return ip, dn, real_name, ssh_user, ssh_pass

async def _handle(text):
    p = text.split(maxsplit=2); cmd = p[0].lower()
    arg1 = p[1].strip() if len(p) > 1 else ""
    arg2 = p[2].strip() if len(p) > 2 else ""

    if cmd in ("/start", "/help"):
        return ("📡 <b>Keenetic Unified — Центр управления</b>\n\n"
            "🔍 <b>Мониторинг:</b>\n"
            "/status — все роутеры\n"
            "/router &lt;имя&gt; — подробно\n"
            "/speed &lt;имя&gt; — скорость\n"
            "/events — последние события\n"
            "/watchdog &lt;имя&gt; — watchdog статус\n\n"
            "🔧 <b>Управление:</b>\n"
            "/ssh &lt;имя&gt; &lt;команда&gt; — SSH команда\n"
            "/ssh all &lt;команда&gt; — SSH на все роутеры\n"
            "/neo &lt;имя&gt; restart — перезапуск neo\n"
            "/neo &lt;имя&gt; status — статус neo\n"
            "/reboot &lt;имя&gt; — перезагрузка роутера\n"
            "/ping &lt;имя&gt; — пинг роутера\n"
            "/uptime &lt;имя&gt; — аптайм\n"
            "/interfaces &lt;имя&gt; — сетевые интерфейсы\n"
            "/update &lt;имя&gt; — обновить домены на роутере\n"
            "/update all — обновить домены на всех роутерах\n"
            "/domains — статус доменов\n\n"
            "⚙️ <b>Настройка:</b>\n"
            "/setip &lt;имя&gt; &lt;IP&gt; — задать IP\n"
            "/setname &lt;имя&gt; &lt;Название&gt; — задать имя\n"
            "/setweb &lt;имя&gt; &lt;URL&gt; — задать web ссылку\n"
            "/delete &lt;имя&gt; — удалить роутер\n\n"
            "🔔 <b>Уведомления:</b>\n"
            "/test — проверить Telegram + Email\n\n"
            "📋 <b>Роутеры:</b>\n"
            + _router_list())

    elif cmd == "/test":
        from .notifier import send_telegram, _email
        import asyncio
        # Test Telegram
        await send_telegram("🔔 <b>Тест уведомлений</b>\n✅ Telegram работает!\n\nПроверяю email...")
        # Test Email
        ok_email = False
        try:
            await asyncio.to_thread(_email,
                "Keenetic Unified — тест уведомлений",
                "<h2>✅ Email уведомления работают!</h2><p>Это тестовое письмо от Keenetic Unified.</p>"
            )
            ok_email = True
        except Exception as e:
            ok_email = False
            logger.error(f"Test email: {e}")
        email_status = f"✅ Email отправлен на {config.SMTP_TO}" if ok_email else f"❌ Email ошибка — проверь SMTP настройки в .env"
        return f"🔔 <b>Результат проверки</b>\n\n✅ Telegram — работает\n{email_status}"

    elif cmd == "/status":
        R = load_json(config.ROUTERS_FILE, {}); W = load_json(config.WATCHDOG_FILE, {})
        S = load_json(config.SITES_FILE, {})
        if not R: return "📡 Нет роутеров"
        lines = [f"📡 <b>Дата-центр ({len(R)} роутеров)</b>\n"]
        on = off = 0
        for n, c in R.items():
            is_on = c.get("online")
            if is_on is True: on += 1; i = "🟢"
            elif is_on is False: off += 1; i = "🔴"
            else: i = "⚪"
            dn = c.get("display_name") or n
            wd = W.get(n, {}).get("state", "—")
            sites_info = S.get(n, {})
            sites_ok = sum(1 for v in sites_info.values() if v.get("status"))
            sites_total = len(sites_info)
            sites_str = f" | Sites {sites_ok}/{sites_total}" if sites_total else ""
            lines.append(f"{i} <b>{dn}</b> ({n}) WD:{wd}{sites_str}")
        lines.insert(1, f"🟢 Online: {on} | 🔴 Offline: {off}\n")
        return "\n".join(lines)

    elif cmd == "/router":
        if not arg1: return "❓ /router имя\n\n" + _router_list()
        R = load_json(config.ROUTERS_FILE, {})
        # Case-insensitive
        c = R.get(arg1); rn = arg1
        if not c:
            for k, v in R.items():
                if k.lower() == arg1.lower(): c = v; rn = k; break
        if not c: return f"❌ '{arg1}' не найден\n\n" + _router_list()
        dn = c.get("display_name") or rn
        i = "🟢 ONLINE" if c.get("online") is True else "🔴 OFFLINE" if c.get("online") is False else "⚪ —"
        W = load_json(config.WATCHDOG_FILE, {}).get(rn, {})
        S = load_json(config.SITES_FILE, {}).get(rn, {})
        SP = load_json(config.SPEED_FILE, {}).get(rn, []); l = SP[-1] if SP else {}
        lines = [f"📡 <b>{dn}</b> ({arg1})", f"Статус: {i}", f"IP: {c.get('ip','—')}"]
        if c.get("web_url"): lines.append(f"Web: {c['web_url']}")
        if W: lines.append(f"Watchdog: {W.get('state','—')} | Neo: {'✅' if W.get('neo_alive') else '❌'} | VPN routes: {W.get('vpn_routes',0)}")
        if S:
            for site, info in S.items():
                si = "✅" if info.get("status") else "❌"
                lines.append(f"  {si} {site}")
        if l:
            lines.append(f"VPN ↓{l.get('vpn_down',0):.0f} ↑{l.get('vpn_up',0):.0f} Ping {l.get('ping',0):.0f}ms")
            lines.append(f"RU  ↓{l.get('ru_down',0):.0f} Ping {l.get('ru_ping',0):.0f}ms")
        lc = c.get("last_check")
        if lc: lines.append(f"Проверка: {lc[:16]}")
        return "\n".join(lines)

    elif cmd == "/ssh":
        if not arg1: return "❓ /ssh &lt;имя|all&gt; &lt;команда&gt;\n\nПример: /ssh andrey opkg update\nМасово: /ssh all opkg update"
        # /ssh all <cmd>
        if arg1.lower() == "all":
            ssh_cmd = arg2 or "uptime"
            from ..main import routers as _all_r
            from .ssh_client import ssh_exec_verbose
            lines = [f"🔧 <b>SSH all</b>: <code>{ssh_cmd}</code>\n"]
            ok = fail = 0
            for rname, rcfg in list(_all_r.items()):
                rip = rcfg.get("ip","") or rcfg.get("wan_ip","")
                if not rip: lines.append(f"⏭ <b>{rname}</b>: нет IP"); continue
                ru = rcfg.get("user") or config.SSH_USER
                rp = rcfg.get("password") or config.SSH_PASS
                r = await ssh_exec_verbose(rip, ssh_cmd, user=ru, password=rp, timeout=60)
                icon = "✅" if r["ok"] else "❌"
                ec = r["exit_code"]
                if r["ok"]: ok += 1
                else: fail += 1
                body = _escape((r["output"] or r["stderr"] or "")[:400])
                lines.append(f"{icon} <b>{rname}</b> <code>exit={ec}</code>\n<pre>{body}</pre>")
            lines.append(f"\nИтого: {ok} ✅  {fail} ❌")
            return "\n".join(lines)
        # /ssh <name> <cmd>
        ip, dn, _, u, p = _get_router_ip(arg1)
        if not ip: return f"❌ '{arg1}' — нет IP. Добавь IP через /admin или watchdog\n\n" + _router_list()
        ssh_cmd = arg2 or "show version"
        result = await ssh_exec(ip, ssh_cmd, user=u, password=p)
        return f"🔧 <b>{dn}</b> ({ip})\n$ {ssh_cmd}\n\n<pre>{_escape(result)}</pre>"

    elif cmd == "/neo":
        if not arg1: return "❓ /neo имя restart|status"
        ip, dn, _, u, p = _get_router_ip(arg1)
        if ip is None: return f"❌ '{arg1}' не найден\n\n" + _router_list()
        if not ip: return f"❌ '{arg1}' — нет IP. Задай через /admin"
        subcmd = arg2 or "status"
        result = await ssh_exec(ip, f"neo {subcmd}", user=u, password=p)
        return f"🔄 <b>{dn}</b> neo {subcmd}\n\n<pre>{_escape(result)}</pre>"

    elif cmd == "/reboot":
        if not arg1: return "❓ /reboot имя"
        ip, dn, _, u, p = _get_router_ip(arg1)
        if ip is None: return f"❌ '{arg1}' не найден\n\n" + _router_list()
        if not ip: return f"❌ '{arg1}' — нет IP. Задай через /admin"
        result = await ssh_exec(ip, "reboot", user=u, password=p)
        return f"♻️ <b>{dn}</b> — перезагрузка отправлена\n\n<pre>{_escape(result)}</pre>"

    elif cmd == "/ping":
        if not arg1: return "❓ /ping имя"
        ip, dn, _, _u, _p = _get_router_ip(arg1)
        if ip is None: return f"❌ '{arg1}' не найден\n\n" + _router_list()
        if not ip: return f"❌ '{arg1}' — нет IP. Задай через /admin"
        try:
            proc = await asyncio.create_subprocess_exec("ping", "-c", "4", "-W", "3", ip,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=20)
            return f"📶 <b>{dn}</b> ({ip})\n\n<pre>{_escape(out.decode())}</pre>"
        except: return f"❌ Ping timeout {ip}"

    elif cmd == "/uptime":
        if not arg1: return "❓ /uptime имя"
        ip, dn, _, u, p = _get_router_ip(arg1)
        if ip is None: return f"❌ '{arg1}' не найден\n\n" + _router_list()
        if not ip: return f"❌ '{arg1}' — нет IP. Задай через /admin"
        result = await ssh_exec(ip, "uptime", user=u, password=p)
        return f"⏱ <b>{dn}</b>\n\n<pre>{_escape(result)}</pre>"

    elif cmd == "/interfaces":
        if not arg1: return "❓ /interfaces имя"
        ip, dn, _, u, p = _get_router_ip(arg1)
        if ip is None: return f"❌ '{arg1}' не найден\n\n" + _router_list()
        if not ip: return f"❌ '{arg1}' — нет IP. Задай через /admin"
        result = await ssh_exec(ip, "ip -br addr show", user=u, password=p)
        return f"🌐 <b>{dn}</b> интерфейсы\n\n<pre>{_escape(result)}</pre>"

    elif cmd == "/speed":
        if not arg1: return "❓ /speed имя"
        H = load_json(config.SPEED_FILE, {})
        rn = _find_router(H, arg1) or arg1.strip().lower()
        SP = H.get(rn, [])
        if not SP: return f"📊 Нет данных для '{arg1}'"
        l = SP[-1]
        return (f"📊 <b>{arg1}</b> — последний замер\n\n"
            f"VPN ↓ {l.get('vpn_down',0):.1f} Mbps\n"
            f"VPN ↑ {l.get('vpn_up',0):.1f} Mbps\n"
            f"VPN Ping: {l.get('ping',0):.0f} ms\n"
            f"RU ↓ {l.get('ru_down',0):.1f} Mbps\n"
            f"RU Ping: {l.get('ru_ping',0):.0f} ms\n"
            f"Время: {l.get('ts','—')[:16]}")

    elif cmd == "/watchdog":
        if not arg1:
            W = load_json(config.WATCHDOG_FILE, {})
            if not W: return "Нет данных watchdog"
            lines = ["🐕 <b>Watchdog статус</b>\n"]
            for n, w in W.items():
                dc = "🟢" if w.get("state")=="OK" else "🔴" if w.get("state") in ("CRITICAL","DEAD") else "🟡"
                lines.append(f"{dc} <b>{n}</b>: {w.get('state','—')} | Neo {'✅' if w.get('neo_alive') else '❌'} | Last: {str(w.get('last_seen','—'))[:16]}")
            return "\n".join(lines)
        WD = load_json(config.WATCHDOG_FILE, {})
        wn = _find_router(WD, arg1) or arg1.strip().lower()
        W = WD.get(wn, {})
        if not W: return f"❌ Нет данных для '{arg1}'"
        return (f"🐕 <b>{wn}</b>\n"
            f"State: {W.get('state','—')}\nPhase: {W.get('phase',0)}\n"
            f"Neo: {'✅' if W.get('neo_alive') else '❌'}\nVPN routes: {W.get('vpn_routes',0)}\n"
            f"Detail: {W.get('detail','—')}\nLast: {str(W.get('last_seen','—'))[:16]}")

    elif cmd == "/events":
        from .notifier import events
        if not events: return "📋 Нет событий"
        lines = ["📋 <b>Последние события</b>\n"]
        for e in events[-15:]:
            t = str(e.get("ts",""))[:16]
            lines.append(f"<code>{t}</code> {e.get('router','')}: {e.get('detail','')}")
        return "\n".join(lines)

    elif cmd == "/domains":
        from .hydra_manager import load_hydra_config, get_config_version
        cfg = load_hydra_config()
        return (f"🌐 <b>Домены HydraRoute</b>\n\n"
            f"Domain groups: {len(cfg.domain_groups)}\n"
            f"IP groups: {len(cfg.ip_groups)}\n"
            f"Version: {get_config_version(cfg)}")

    elif cmd == "/update":
        if not arg1: return "❓ /update имя|all — обновить домены"
        if arg1.lower() == "all":
            R = load_json(config.ROUTERS_FILE, {})
            if not R: return "❌ Нет роутеров"
            lines = ["📋 <b>Обновление доменов на всех роутерах</b>\n"]
            for name, cfg in R.items():
                ip = cfg.get("ip","") or cfg.get("wan_ip","")
                if not ip: lines.append(f"⏭ <b>{name}</b>: нет IP"); continue
                u = cfg.get("user") or config.SSH_USER
                p = cfg.get("password") or config.SSH_PASS
                result = await ssh_exec(ip, "/opt/bin/hydra_update.sh", user=u, password=p, timeout=30)
                lines.append(f"✅ <b>{name}</b>: {result.strip()[:80] or 'ok'}")
            return "\n".join(lines)
        ip, dn, _, u, p = _get_router_ip(arg1)
        if ip is None: return f"❌ '{arg1}' не найден\n\n" + _router_list()
        if not ip: return f"❌ '{arg1}' — нет IP. Задай через /admin"
        result = await ssh_exec(ip, "/opt/bin/hydra_update.sh", user=u, password=p, timeout=30)
        return f"📋 <b>{dn}</b> — обновление доменов\n\n<pre>{_escape(result)}</pre>"

    elif cmd == "/setip":
        if not arg1 or not arg2: return "❓ /setip имя IP\nПример: /setip Andrey 192.168.1.1"
        R = load_json(config.ROUTERS_FILE, {})
        rn = _find_router(R, arg1)
        if not rn: return f"❌ '{arg1}' не найден\n\n" + _router_list()
        R[rn]["ip"] = arg2
        save_json(config.ROUTERS_FILE, R)
        return f"✅ <b>{rn}</b> IP = {arg2}"

    elif cmd == "/setname":
        if not arg1 or not arg2: return "❓ /setname имя Красивое Название"
        R = load_json(config.ROUTERS_FILE, {})
        rn = _find_router(R, arg1)
        if not rn: return f"❌ '{arg1}' не найден\n\n" + _router_list()
        R[rn]["display_name"] = arg2
        save_json(config.ROUTERS_FILE, R)
        return f"✅ <b>{rn}</b> = {arg2}"

    elif cmd == "/setweb":
        if not arg1 or not arg2: return "❓ /setweb имя https://xxx.link"
        R = load_json(config.ROUTERS_FILE, {})
        rn = _find_router(R, arg1)
        if not rn: return f"❌ '{arg1}' не найден\n\n" + _router_list()
        R[rn]["web_url"] = arg2
        save_json(config.ROUTERS_FILE, R)
        return f"✅ <b>{rn}</b> web = {arg2}"

    elif cmd == "/delete":
        if not arg1: return "❓ /delete имя"
        R = load_json(config.ROUTERS_FILE, {})
        rn = _find_router(R, arg1)
        if not rn: return f"❌ '{arg1}' не найден"
        del R[rn]
        save_json(config.ROUTERS_FILE, R)
        return f"🗑 <b>{rn}</b> удалён"

    return ""

def _find_router(R, name):
    """Case-insensitive router name lookup. Returns real key or None."""
    if name in R: return name
    for k in R:
        if k.lower() == name.lower(): return k
    return None

def _router_list():
    R = load_json(config.ROUTERS_FILE, {})
    if not R: return "Нет роутеров"
    return "Доступные: " + ", ".join(f"<code>{n}</code>" for n in R.keys())

def _escape(text):
    if not text: return "(пусто)"
    import re
    text = re.sub(r'\x1b\[[0-9;]*[mGKHF]', '', text)  # strip ANSI escape codes
    return text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")[:3500]
