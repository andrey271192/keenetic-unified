# 📡 Keenetic Unified

Система мониторинга и управления роутерами Keenetic и Windows-ПК через веб-интерфейс и Telegram.

- Веб-дашборд: онлайн/офлайн, скорость интернета, watchdog, Neo-статус
- Telegram-бот: SSH-команды, статус, перезагрузка, управление доменами
- HydraRoute Neo: единая конфигурация доменов/IP на все роутеры сразу
- Поддержка 20+ объектов; роутеры регистрируются автоматически

---

## Быстрая установка

### 1. Сервер (Ubuntu 22/24)

```bash
git clone https://github.com/andrey271192/Keenetic-Unified.git /opt/keenetic-unified
cd /opt/keenetic-unified
bash server/install.sh
nano server/.env          # вписать Telegram токен и chat ID
systemctl restart keenetic-unified
```

Сервер поднимается на `http://IP:8000`.

### 2. Роутер (Keenetic + Entware)

```bash
export ROUTER_NAME="имя" SERVER_URL="http://IP:8000" \
  && curl -fsSL https://raw.githubusercontent.com/andrey271192/Keenetic-Unified/main/router/install.sh | sh
```

Роутер появится в дашборде автоматически при первом heartbeat.

### 3. Windows PC

```powershell
.\setup.ps1 -ServerIP "IP" -RouterName "имя" -RouterLanIP "192.168.1.1"
```

Запускает мониторинг скорости (VPN + прямой RU) и доступности сайтов.

---

## Настройки по умолчанию

| Параметр | Значение |
|---|---|
| SSH на роутерах | `root` / `keenetic` |
| Пароль веб-админки | `admin` |
| Порт сервера | `8000` |
| Heartbeat интервал | 60 сек |
| Обновление доменов | раз в сутки + по команде |

Можно задать индивидуальные SSH-логин/пароль на каждый роутер через `/admin`.

---

## Веб-интерфейс

| Страница | Описание |
|---|---|
| `/` | Дашборд — статус всех роутеров, скорость, Neo |
| `/admin` | Управление роутерами (пароль) |
| `/domains` | Конфигурация HydraRoute (домены и IP-группы) |
| `/stats/{name}` | Графики скорости для роутера |

---

## HydraRoute — управление доменами

Страница `/domains` позволяет:

- Просматривать и редактировать группы доменов и IP-адресов
- Включать / отключать группы переключателем
- Быстро добавлять записи в группу
- Импортировать `domain.conf` и `ip.list` с роутера
- **Отправить конфигурацию на все роутеры одной кнопкой**

После любого изменения появляется оранжевый баннер — нажми **"Отправить сейчас"** или кнопку **"Обновить все роутеры"**.

Роутер получает файлы с сервера по HTTP, записывает в `/opt/etc/HydraRoute/` и перезапускает `neo`.

---

## Telegram-бот

```
/status              — статус всех роутеров
/router имя          — подробная информация
/speed имя           — скорость интернета
/neo имя status      — статус Neo
/neo имя restart     — перезапуск Neo
/ssh имя команда     — выполнить SSH-команду
/reboot имя          — перезагрузка роутера
/ping имя            — пинг
/uptime имя          — аптайм
/interfaces имя      — сетевые интерфейсы
/watchdog имя        — статус watchdog
/update имя          — обновить домены на роутере
/update all          — обновить домены на всех роутерах
/events              — последние события
/help                — список команд
```

---

## Структура проекта

```
server/          FastAPI-сервер, Telegram-бот, API
router/          Скрипты для Keenetic (watchdog, heartbeat, hydra_update)
windows/         PowerShell-скрипты для Windows PC
```

---

## Удаление

**Сервер:**
```bash
bash /opt/keenetic-unified/server/uninstall.sh
```

**Роутер:**
```bash
bash /opt/bin/uninstall.sh
```

**Windows:**
```powershell
.\uninstall.ps1
```
