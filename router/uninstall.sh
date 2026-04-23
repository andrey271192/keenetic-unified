#!/bin/sh
crontab -l 2>/dev/null | grep -v -E "(watchdog|heartbeat|hydra_update)" | crontab -
rm -f /opt/bin/send.sh /opt/bin/watchdog.sh /opt/bin/watchdog_heartbeat.sh /opt/bin/hydra_update.sh
rm -f /opt/etc/router_name /opt/etc/server_url /opt/etc/vpn_list
echo "✅ Удалено"
