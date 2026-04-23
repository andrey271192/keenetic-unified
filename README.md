# 📡 Keenetic Unified v6.0

## Быстрая установка (3 шага)

### 1. Сервер (Ubuntu)
```bash
git clone https://github.com/andrey271192/Keenetic-Unified.git /opt/keenetic-unified
cd /opt/keenetic-unified
bash server/install.sh
nano server/.env   # вписать ТОЛЬКО Telegram токен
systemctl restart keenetic-unified
```

### 2. Роутер (Keenetic + Entware)
```bash
export ROUTER_NAME="andrey" SERVER_URL="http://IP:8000" \
  && curl -fsSL https://raw.githubusercontent.com/andrey271192/Keenetic-Unified/main/router/install.sh | sh
```

### 3. Windows PC
```powershell
.\setup.ps1 -ServerIP "IP" -RouterName "andrey" -RouterIP "192.168.1.1"
```

## Что уже настроено по умолчанию
- SMTP: keenetic@school29.com (все уведомления дублируются на почту)
- SSH: root / keenetic (для всех роутеров)
- Пароль админки: admin
- Роутеры появляются автоматически при первом heartbeat

## Страницы
- `/` — дашборд (без пароля, только просмотр)
- `/admin` — управление (с паролем)
- `/stats/{name}` — графики скорости

## Telegram бот
```
/status           — все роутеры
/router имя       — подробно
/ssh имя команда  — выполнить SSH (ответ приходит!)
/neo имя restart  — перезапуск neo
/neo имя status   — статус neo
/reboot имя       — перезагрузка
/ping имя         — пинг
/uptime имя       — аптайм
/interfaces имя   — интерфейсы
/speed имя        — скорость
/watchdog имя     — watchdog
/update имя       — обновить домены
/domains          — статус доменов
/events           — последние события
```

## Удаление

### Сервер
```bash
bash /opt/keenetic-unified/server/uninstall.sh
```

### Роутер
```bash
bash /opt/bin/uninstall.sh
```

### Windows
```powershell
.\uninstall.ps1
```

## Windows установка
```powershell
.\setup.ps1 -ServerIP "212.118.42.105" -RouterName "andrey" -RouterLanIP "192.168.1.1"
```
