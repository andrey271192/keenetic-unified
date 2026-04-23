#!/bin/sh
TITLE="$1"; MSG="$2"
ROUTER=$(cat /opt/etc/router_name 2>/dev/null || echo "unknown")
SERVER=$(cat /opt/etc/server_url 2>/dev/null)
TG_TOKEN=$(cat /opt/etc/tg_token 2>/dev/null)
TG_CHAT=$(cat /opt/etc/tg_chat 2>/dev/null)
FULL="[$ROUTER] $TITLE: $MSG"

# Telegram напрямую с роутера
if [ -n "$TG_TOKEN" ] && [ -n "$TG_CHAT" ]; then
    SENT=0
    for iface in $(cat /opt/etc/vpn_list 2>/dev/null); do
        ip link show "$iface" up 2>/dev/null | grep -q "UP" && \
        curl -sf --interface "$iface" --connect-timeout 10 \
            -X POST "https://api.telegram.org/bot$TG_TOKEN/sendMessage" \
            -d "chat_id=$TG_CHAT" -d "text=$FULL" >/dev/null 2>&1 && SENT=1 && break
    done
    [ "$SENT" -eq 0 ] && curl -sf --connect-timeout 10 \
        -X POST "https://api.telegram.org/bot$TG_TOKEN/sendMessage" \
        -d "chat_id=$TG_CHAT" -d "text=$FULL" >/dev/null 2>&1
fi

# На сервер
[ -n "$SERVER" ] && curl -sf -X POST "$SERVER/api/watchdog" \
    -H "Content-Type: application/json" \
    -d "{\"router\":\"$ROUTER\",\"state\":\"$TITLE\",\"detail\":\"$MSG\"}" 2>/dev/null || true

echo "$(date '+%Y-%m-%d %H:%M:%S') $FULL" >> /opt/var/log/send.log
