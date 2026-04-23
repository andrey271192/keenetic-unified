#!/bin/sh
LOCK="/opt/var/run/watchdog.lock"; STATE="/opt/var/run/watchdog_state"
SERVER=$(cat /opt/etc/server_url 2>/dev/null); ROUTER=$(cat /opt/etc/router_name 2>/dev/null || echo "unknown")
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') [$1] $2" >> /opt/var/log/watchdog.log; }
[ -f "$LOCK" ] && kill -0 $(cat "$LOCK") 2>/dev/null && exit 0; echo $$ > "$LOCK"; trap "rm -f $LOCK" EXIT
check_yt() { for i in $(cat /opt/etc/vpn_list 2>/dev/null); do ip link show "$i" up 2>/dev/null | grep -q "UP" && curl -sf --connect-timeout 8 --max-time 15 --interface "$i" "https://www.youtube.com" -o /dev/null 2>/dev/null && return 0; done; curl -sf --connect-timeout 8 --max-time 15 "https://www.youtube.com" -o /dev/null 2>/dev/null; }
check_inet() { ping -c 1 -W 5 8.8.8.8 >/dev/null 2>&1 || ping -c 1 -W 5 1.1.1.1 >/dev/null 2>&1; }
MY_IP=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+\.\d+\.\d+\.\d+' | grep -v 127.0.0.1 | head -1)
report() { echo "$1" > "$STATE"; [ -n "$SERVER" ] && curl -sf -X POST "$SERVER/api/watchdog" -H "Content-Type: application/json" -d "{\"router\":\"$ROUTER\",\"state\":\"$1\",\"detail\":\"$2\",\"phase\":$3,\"neo_alive\":$4,\"vpn_routes\":0,\"ip\":\"$MY_IP\",\"display_name\":\"$ROUTER\"}" 2>/dev/null || true; }
if check_yt; then log "OK" "YouTube OK"; report "OK" "YouTube работает" 0 true; exit 0; fi
if ! check_inet; then log "SKIP" "Нет интернета"; report "SKIP" "Нет интернета" 0 true; exit 0; fi
log "ALERT" "YouTube down"; report "RESTART" "Перезапуск neo" 1 true; neo restart >> /opt/var/log/watchdog.log 2>&1; sleep 300
if check_yt; then report "RECOVERY" "OK после neo" 1 true; exit 0; fi
report "RESTART" "Перезапуск Entware" 2 false; /opt/etc/init.d/rc.unslung restart >> /opt/var/log/watchdog.log 2>&1; sleep 300
if check_yt; then report "RECOVERY" "OK после Entware" 2 true; exit 0; fi
report "CRITICAL" "НЕ восстановлено!" 3 false
