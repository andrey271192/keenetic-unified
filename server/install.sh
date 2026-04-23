#!/bin/bash
set -e
DIR="/opt/keenetic-unified"
echo "📡 Keenetic Unified v6.0"
apt-get update -qq && apt-get install -y python3 python3-pip python3-venv git curl sshpass
if [ -d "$DIR" ]; then cd "$DIR" && git pull; else git clone https://github.com/andrey271192/Keenetic-Unified.git "$DIR" && cd "$DIR"; fi
python3 -m venv venv && source venv/bin/activate && pip install -q -r server/requirements.txt
if [ ! -f server/.env ]; then
    cp server/.env.example server/.env
    echo ""
    echo "⚠️  ОБЯЗАТЕЛЬНО заполни Telegram токен:"
    echo "   nano $DIR/server/.env"
    echo "   (SMTP уже настроен, пароль admin)"
    echo ""
fi
cp keenetic-unified.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable keenetic-unified && systemctl restart keenetic-unified
echo "✅ http://$(hostname -I | awk '{print $1}'):8000"
echo "   Логи: journalctl -u keenetic-unified -f"
