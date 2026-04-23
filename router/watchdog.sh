#!/bin/sh
LOCK="/opt/var/run/watchdog.lock"; STATE="/opt/var/run/watchdog_state"
FAIL_COUNT_FILE="/opt/var/run/watchdog_fail_count"
SERVER=$(cat /opt/etc/server_url 2>/dev/null); ROUTER=$(cat /opt/etc/router_name 2>/dev/null || echo "unknown")
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') [$1] $2" >> /opt/var/log/watchdog.log; }
[ -f "$LOCK" ] && kill -0 $(cat "$LOCK") 2>/dev/null && exit 0; echo $$ > "$LOCK"; trap "rm -f $LOCK" EXIT

# Check if HydraRoute Neo is running
check_neo() {
  neo status 2>/dev/null | grep -qiE "running|alive"
}

# Check if at least one nwg/tun/wg VPN interface is UP
check_vpn_iface() {
  for i in nwg0 nwg1 nwg2 nwg3 tun0 wg0; do
    ip link show "$i" 2>/dev/null | grep -q "UP" && return 0
  done
  return 1
}

# Collect status summary
probe_status() {
  NEO_S="stopped"; VPN_IFS=""
  neo status 2>/dev/null | grep -qiE "running|alive" && NEO_S="running"
  for i in nwg0 nwg1 nwg2 nwg3 tun0 wg0; do
    ip link show "$i" 2>/dev/null | grep -q "UP" && VPN_IFS="$VPN_IFS $i"
  done
  [ -z "$VPN_IFS" ] && VPN_IFS="none"
  echo "neo=$NEO_S vpn=$VPN_IFS"
}

check_inet() { ping -c 1 -W 5 8.8.8.8 >/dev/null 2>&1 || ping -c 1 -W 5 1.1.1.1 >/dev/null 2>&1 || curl -sf --max-time 5 https://dns.google >/dev/null 2>&1; }
MY_IP=$(curl -sf -4 --max-time 5 https://ifconfig.me 2>/dev/null || curl -sf -4 --max-time 5 https://api.ipify.org 2>/dev/null || ip -4 addr show | grep -oP '(?<=inet\s)\d+\.\d+\.\d+\.\d+' | grep -v 127.0.0.1 | head -1)
report() { echo "$1" > "$STATE"; [ -n "$SERVER" ] && curl -sf -X POST "$SERVER/api/watchdog" -H "Content-Type: application/json" -d "{\"router\":\"$ROUTER\",\"state\":\"$1\",\"detail\":\"$2\",\"phase\":$3,\"neo_alive\":$4,\"vpn_routes\":0,\"ip\":\"$MY_IP\",\"display_name\":\"$ROUTER\"}" 2>/dev/null || true; }

# Everything is healthy — reset fail counter and exit
if check_neo && check_vpn_iface; then
  DETAIL=$(probe_status)
  log "OK" "$DETAIL"
  report "OK" "$DETAIL" 0 true
  rm -f "$FAIL_COUNT_FILE"
  exit 0
fi

# No internet at all — skip without alarming
if ! check_inet; then
  log "SKIP" "Нет интернета"
  report "SKIP" "Нет интернета" 0 true
  exit 0
fi

# --- Problem detected ---
DETAIL=$(probe_status)
log "ALERT" "$DETAIL"

# Phase 1: restart Neo
log "ACTION" "Перезапускаем neo..."
report "RESTART" "Перезапуск neo | $DETAIL" 1 false
neo restart >> /opt/var/log/watchdog.log 2>&1
sleep 60

if check_neo && check_vpn_iface; then
  DETAIL=$(probe_status)
  log "RECOVERY" "Восстановлено после neo restart | $DETAIL"
  report "RECOVERY" "✅ Восстановлено после neo restart | $DETAIL" 1 true
  rm -f "$FAIL_COUNT_FILE"
  exit 0
fi

# Phase 2: restart Entware
DETAIL=$(probe_status)
log "ACTION" "Перезапускаем Entware..."
report "RESTART" "Перезапуск Entware | $DETAIL" 2 false
/opt/etc/init.d/rc.unslung restart >> /opt/var/log/watchdog.log 2>&1
sleep 120

if check_neo && check_vpn_iface; then
  DETAIL=$(probe_status)
  log "RECOVERY" "Восстановлено после Entware restart | $DETAIL"
  report "RECOVERY" "✅ Восстановлено после Entware restart | $DETAIL" 2 true
  rm -f "$FAIL_COUNT_FILE"
  exit 0
fi

# Phase 3: still broken
DETAIL=$(probe_status)
log "CRITICAL" "НЕ восстановлено | $DETAIL"
report "CRITICAL" "🚨 НЕ восстановлено после 2 попыток | $DETAIL" 3 false
