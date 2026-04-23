# 📡 Keenetic Unified

Система мониторинга и управления роутерами Keenetic и Windows-ПК через веб-интерфейс и Telegram.

- Веб-дашборд: онлайн/офлайн, скорость интернета, watchdog, Neo-статус
- Telegram-бот: SSH-команды, статус, перезагрузка, управление доменами
- HydraRoute Neo: единая конфигурация доменов/IP на все роутеры сразу
- Массовые SSH-команды через веб и Telegram на все роутеры одновременно
- Авторизация по паролю — все страницы и операции защищены
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
| Пароль веб-интерфейса | `admin` (задаётся в `.env` через `ADMIN_PASSWORD`) |
| Порт сервера | `8000` |
| Heartbeat интервал | 60 сек |
| Обновление доменов | раз в сутки + по команде |

Индивидуальные SSH-логин/пароль на каждый роутер задаются через `/admin`.

---

## Авторизация

При открытии любой страницы появляется экран входа. Пароль проверяется на сервере через `/api/auth`. После входа сессия хранится в браузере до закрытия вкладки. Кнопка **"Выйти"** сбрасывает сессию.

Все операции записи (домены, роутеры, SSH) требуют заголовок `X-Admin-Password`.

Сменить пароль — в файле `server/.env`:
```
ADMIN_PASSWORD=новый_пароль
```

---

## Веб-интерфейс

Единый nav на всех страницах: **📊 Дашборд · 🌐 Домены · ⚙ Управление**

| Страница | Описание |
|---|---|
| `/` | Дашборд — статус всех роутеров, скорость, Neo, события |
| `/domains` | Конфигурация HydraRoute — домены и IP-группы |
| `/admin` | Управление роутерами + массовый SSH |
| `/stats/{name}` | Графики скорости для роутера |

---

## HydraRoute — управление доменами

Страница `/domains` позволяет:

- Просматривать и редактировать группы доменов и IP-адресов
- Включать / отключать группы переключателем
- Быстро добавлять записи в группу
- Импортировать `domain.conf` и `ip.list` с роутера
- **Отправить конфигурацию на все роутеры одной кнопкой**

После любого изменения появляется оранжевый баннер — нажми **"Отправить сейчас"**.

Роутер получает файлы с сервера по HTTP (`curl`), записывает в `/opt/etc/HydraRoute/` и перезапускает `neo`. Не зависит от версии скриптов на роутере.

---

## Массовый SSH

### Через веб (⚙ Управление)

Секция "SSH — выполнить на всех роутерах":
- Поле ввода команды + кнопка ▶ Выполнить
- Быстрые кнопки: `opkg update`, `opkg upgrade`, `uptime`, `neo status`, `hydra log`
- Результат по каждому роутеру: имя хоста, время, вывод, exit-код, stderr

### Через Telegram

```
/ssh all opkg update       — на все роутеры
/ssh all neo status        — статус neo везде
/ssh имя команда           — на конкретный роутер
```

Каждый ответ содержит `[hostname] время`, полный вывод и `exit=N` — сразу видно выполнилась ли команда.

---

## Telegram-бот

```
/status              — статус всех роутеров
/router имя          — подробная информация
/speed имя           — скорость интернета
/neo имя status      — статус Neo
/neo имя restart     — перезапуск Neo
/ssh имя команда     — SSH на один роутер
/ssh all команда     — SSH на все роутеры
/reboot имя          — перезагрузка роутера
/ping имя            — пинг
/uptime имя          — аптайм
/interfaces имя      — сетевые интерфейсы
/watchdog имя        — статус watchdog
/update имя          — обновить домены HydraRoute на роутере
/update all          — обновить домены на всех роутерах
/events              — последние события
/help                — список команд
```

---

## Структура проекта

```
server/
  main.py              — FastAPI приложение, роуты страниц
  config.py            — конфигурация из .env
  api/
    endpoints.py       — API: watchdog, sites, speed, hydra, ssh/all
    routers.py         — CRUD роутеров (с паролем)
  services/
    monitor.py         — фоновый мониторинг роутеров
    telegram_bot.py    — Telegram бот
    ssh_client.py      — SSH клиент (ssh_exec, ssh_exec_verbose)
    hydra_manager.py   — парсинг/генерация domain.conf + ip.list
    notifier.py        — уведомления (Telegram + email)
  templates/
    dashboard.html     — дашборд
    domains.html       — управление HydraRoute
    admin.html         — управление роутерами + массовый SSH
    stats.html         — графики скорости

router/
  install.sh           — установка на роутер (одной командой)
  watchdog.sh          — мониторинг интернета и Neo
  watchdog_heartbeat.sh — отправка heartbeat на сервер
  hydra_update.sh      — обновление HydraRoute конфига с сервера

windows/
  setup.ps1            — установка клиента на Windows
  speedtest_client.ps1 — замер скорости VPN + прямой RU
```

---

## Обновление сервера

```bash
cd /opt/keenetic-unified && git pull && systemctl restart keenetic-unified
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
