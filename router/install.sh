#!/bin/sh
set -e
echo "📡 Keenetic Unified — установка"
[ -z "$ROUTER_NAME" ] && printf "Имя роутера: " && read ROUTER_NAME
[ -z "$SERVER_URL" ] && printf "URL сервера (http://IP:8000): " && read SERVER_URL
[ -z "$TG_TOKEN" ] && printf "Telegram Token (Enter=пропустить): " && read TG_TOKEN
[ -z "$TG_CHAT" ] && printf "Telegram Chat ID (Enter=пропустить): " && read TG_CHAT
[ -z "$ROUTER_NAME" ] || [ -z "$SERVER_URL" ] && echo "❌ Обязательны" && exit 1
mkdir -p /opt/etc /opt/bin /opt/var/log /opt/var/run
echo "$ROUTER_NAME" > /opt/etc/router_name
echo "$SERVER_URL" > /opt/etc/server_url
[ -n "$TG_TOKEN" ] && echo "$TG_TOKEN" > /opt/etc/tg_token
[ -n "$TG_CHAT" ] && echo "$TG_CHAT" > /opt/etc/tg_chat
ip link show | grep -oE '(nwg|tun|wg|ovpn)[0-9]+' | sort -u > /opt/etc/vpn_list 2>/dev/null || true
REPO="https://raw.githubusercontent.com/andrey271192/Keenetic-Unified/main/router"
for f in watchdog.sh watchdog_heartbeat.sh hydra_update.sh send.sh; do curl -fsSL "$REPO/$f" -o "/opt/bin/$f" && chmod +x "/opt/bin/$f"; done
CT="/tmp/cron_ku"; crontab -l 2>/dev/null | grep -v -E "(watchdog|heartbeat|hydra_update)" > "$CT" || true
echo '*/30 * * * * /opt/bin/watchdog.sh >> /opt/var/log/watchdog.log 2>&1' >> "$CT"
echo '* * * * * /opt/bin/watchdog_heartbeat.sh >> /opt/var/log/watchdog.log 2>&1' >> "$CT"
echo '0 2 * * * /opt/bin/hydra_update.sh >> /opt/var/log/hydra_update.log 2>&1' >> "$CT"
crontab "$CT" && rm -f "$CT"
echo "✅ $ROUTER_NAME → $SERVER_URL"
/opt/bin/send.sh "INSTALL" "Установка завершена: $ROUTER_NAME"
