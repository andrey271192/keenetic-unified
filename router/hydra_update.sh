#!/bin/sh
SERVER=$(cat /opt/etc/server_url 2>/dev/null); ROUTER=$(cat /opt/etc/router_name 2>/dev/null || echo "unknown")
LOG="/opt/var/log/hydra_update.log"; DC="/opt/etc/hydra/domain.conf"; IL="/opt/etc/hydra/ip.list"; VF="/opt/etc/hydra/server_version"
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"; }
[ -z "$SERVER" ] && exit 1; CV=$(cat "$VF" 2>/dev/null || echo "none"); NV=$(curl -sf --connect-timeout 10 "$SERVER/api/hydra/version" 2>/dev/null)
[ -z "$NV" ] && exit 0; [ "$CV" = "$NV" ] && exit 0
log "[UPDATE] $CV → $NV"; mkdir -p /opt/etc/hydra; cp "$DC" "${DC}.bak" 2>/dev/null; cp "$IL" "${IL}.bak" 2>/dev/null
ND=$(curl -sf "$SERVER/api/hydra/domain.conf"); NI=$(curl -sf "$SERVER/api/hydra/ip.list")
[ -z "$ND" ] && cp "${DC}.bak" "$DC" 2>/dev/null && exit 1
echo "$ND" > "$DC"; [ -n "$NI" ] && echo "$NI" > "$IL"
neo restart >> "$LOG" 2>&1 && echo "$NV" > "$VF" && log "[OK] v$NV" || { cp "${DC}.bak" "$DC" 2>/dev/null; cp "${IL}.bak" "$IL" 2>/dev/null; neo restart >> "$LOG" 2>&1; }
