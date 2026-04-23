#!/bin/bash
echo "Removing Keenetic Unified from server..."
systemctl stop keenetic-unified 2>/dev/null
systemctl disable keenetic-unified 2>/dev/null
rm -f /etc/systemd/system/keenetic-unified.service
systemctl daemon-reload
rm -rf /opt/keenetic-unified
echo "Done"
