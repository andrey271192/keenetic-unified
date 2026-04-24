#!/usr/bin/env bash
# Заливка сайта ypr1.ru на сервер. Пароль не хранить в репозитории.
# Использование:
#   export SSHPASS='ваш_пароль_root'
#   ./scripts/deploy-ypr1-site.sh
# Либо настройте SSH-ключ и вызовите без SSHPASS.
set -euo pipefail
HOST="${DEPLOY_HOST:-root@62.113.42.63}"
DEST="${DEPLOY_DEST:-/var/www/html/}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FILES=("$ROOT/site/index.html" "$ROOT/site/send_message.php")
if [[ -n "${SSHPASS:-}" ]] && command -v sshpass >/dev/null 2>&1; then
  sshpass -e scp -o StrictHostKeyChecking=no -o ConnectTimeout=20 "${FILES[@]}" "$HOST:$DEST"
else
  scp -o StrictHostKeyChecking=no -o ConnectTimeout=20 "${FILES[@]}" "$HOST:$DEST"
fi
echo "OK: uploaded to $HOST:$DEST"
