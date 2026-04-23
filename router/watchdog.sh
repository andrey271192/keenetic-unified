#!/bin/sh
LOCK="/opt/var/run/watchdog.lock"; STATE="/opt/var/run/watchdog_state"
SERVER=$(cat /opt/etc/server_url 2>/dev/null); ROUTER=$(cat /opt/etc/router_name 2>/dev/null || echo "unknown")
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') [$1] $2" >> /opt/var/log/watchdog.log; }
[ -f "$LOCK" ] && kill -0 $(cat "$LOCK") 2>/dev/null && exit 0; echo $$ > "$LOCK"; trap "rm -f $LOCK" EXIT

# HTTP status check — returns exit 0 if HTTP code != 000 (any response = reachable)
# Tries through VPN interfaces first, then direct
check_tcp() {
  HOST="$1"
  for i in $(cat /opt/etc/vpn_list 2>/dev/null); do
    ip link show "$i" up 2>/dev/null | grep -q "UP" || continue
    _c=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 8 --max-time 15 --interface "$i" -L "https://$HOST" 2>/dev/null)
    [ "$_c" != "000" ] && [ -n "$_c" ] && return 0
  done
  _c=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 8 --max-time 15 -L "https://$HOST" 2>/dev/null)
  [ "$_c" != "000" ] && [ -n "$_c" ]
}

# Check VPN: canva.com + instagram.com — both blocked in Russia without VPN
# Passes if ANY one is reachable via TCP
check_vpn() {
  check_tcp "www.canva.com"     && return 0
  check_tcp "www.instagram.com" && return 0
  return 1
}

# Probe each site for detailed reporting
probe_sites() {
  RESULT=""
  check_tcp "www.canva.com"     && RESULT="$RESULT canva=OK"     || RESULT="$RESULT canva=FAIL"
  check_tcp "www.instagram.com" && RESULT="$RESULT instagram=OK" || RESULT="$RESULT instagram=FAIL"
  echo "$RESULT"
}

check_inet() { ping -c 1 -W 5 8.8.8.8 >/dev/null 2>&1 || ping -c 1 -W 5 1.1.1.1 >/dev/null 2>&1 || curl -sf --max-time 5 https://dns.google >/dev/null 2>&1; }
MY_IP=$(curl -sf -4 --max-time 5 https://ifconfig.me 2>/dev/null || curl -sf -4 --max-time 5 https://api.ipify.org 2>/dev/null || ip -4 addr show | grep -oP '(?<=inet\s)\d+\.\d+\.\d+\.\d+' | grep -v 127.0.0.1 | head -1)
report() { echo "$1" > "$STATE"; [ -n "$SERVER" ] && curl -sf -X POST "$SERVER/api/watchdog" -H "Content-Type: application/json" -d "{\"router\":\"$ROUTER\",\"state\":\"$1\",\"detail\":\"$2\",\"phase\":$3,\"neo_alive\":$4,\"vpn_routes\":0,\"ip\":\"$MY_IP\",\"display_name\":\"$ROUTER\"}" 2>/dev/null || true; }

if check_vpn; then
  DETAIL=$(probe_sites)
  log "OK" "$DETAIL"
  report "OK" "$DETAIL" 0 true
  exit 0
fi
if ! check_inet; then log "SKIP" "Нет интернета"; report "SKIP" "Нет интернета" 0 true; exit 0; fi

DETAIL=$(probe_sites)
log "ALERT" "$DETAIL"
report "RESTART" "Перезапуск neo |$DETAIL" 1 true
neo restart >> /opt/var/log/watchdog.log 2>&1; sleep 300
if check_vpn; then DETAIL=$(probe_sites); report "RECOVERY" "OK после neo |$DETAIL" 1 true; exit 0; fi
report "RESTART" "Перезапуск Entware" 2 false
/opt/etc/init.d/rc.unslung restart >> /opt/var/log/watchdog.log 2>&1; sleep 300
if check_vpn; then DETAIL=$(probe_sites); report "RECOVERY" "OK после Entware |$DETAIL" 2 true; exit 0; fi
report "CRITICAL" "НЕ восстановлено! |$(probe_sites)" 3 false
