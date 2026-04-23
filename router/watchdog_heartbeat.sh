#!/bin/sh
SERVER=$(cat /opt/etc/server_url 2>/dev/null); ROUTER=$(cat /opt/etc/router_name 2>/dev/null || echo "unknown")
STATE=$(cat /opt/var/run/watchdog_state 2>/dev/null || echo "UNKNOWN")
NEO=$(neo status 2>/dev/null | grep -qiE "running|alive" && echo "true" || echo "false")
VPN=$(ip rule show 2>/dev/null | grep -c "fwmark" || echo "0")
MY_IP=$(curl -sf --max-time 5 https://ifconfig.me 2>/dev/null || curl -sf --max-time 5 https://api.ipify.org 2>/dev/null || ip -4 addr show | grep -oP '(?<=inet\s)\d+\.\d+\.\d+\.\d+' | grep -v 127.0.0.1 | head -1)
[ -n "$SERVER" ] && curl -sf -X POST "$SERVER/api/watchdog" -H "Content-Type: application/json" -d "{\"router\":\"$ROUTER\",\"state\":\"$STATE\",\"detail\":\"Heartbeat\",\"neo_alive\":$NEO,\"vpn_routes\":$VPN,\"ip\":\"$MY_IP\",\"display_name\":\"$ROUTER\"}" 2>/dev/null || true
