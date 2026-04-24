# 📦 Установка сайта ЦБ МО | Орион — Полная инструкция

## Что нового в этой версии

| Функция | Описание |
|---|---|
| 📊 Вкладка «Дашборд» | Все калькуляторы, курсы, календарь (как раньше) |
| 📁 Вкладка «Файлы» | Файловый менеджер с загрузкой в Google Drive |
| 🤖 Вкладка «Помощник» | Быстрый доступ к ИИ-бухгалтеру Орион |
| 🔐 PIN-защита | Загрузка и удаление файлов — только по PIN `271192` |
| 📤 Drag & Drop | Перетаскивайте файлы прямо в браузер |
| 📈 Прогресс загрузки | Прогресс-бар при загрузке файлов |

---

## Структура файлов

```
site/
├── index.html              ← Главная страница (с вкладками + файловым менеджером)
├── upload_file.php         ← Загрузка файла в Google Drive
├── list_files.php          ← Список файлов из Google Drive
├── delete_file.php         ← Удаление файла из Google Drive
├── google_drive_init.php   ← Настройки Google Drive (FOLDER_IDs, PIN)
├── send_message.php        ← Форма поддержки → Telegram
├── telegram_webhook.php    ← Webhook от Telegram (ответы оператора)
├── get_replies.php         ← Polling ответов оператора
├── reply.php               ← Ответ пользователя оператору
├── composer.json           ← Зависимости PHP (google/apiclient)
├── .gitignore              ← Исключает ключи и vendor из Git
├── keys/
│   └── google-drive-key.json  ← ❗ Ключ сервисного аккаунта (НЕ в Git!)
└── uploads/                ← Временные файлы (автоматически)
```

---

## 🚀 Установка за 5 шагов

### Шаг 1: Загрузить файлы на сервер

Загрузите через FTP/SFTP или через панель хостинга все файлы в корень домена (`public_html/`):

```
/public_html/
├── index.html
├── upload_file.php
├── list_files.php
├── delete_file.php
├── google_drive_init.php
├── send_message.php
├── telegram_webhook.php
├── get_replies.php
├── reply.php
├── composer.json
└── keys/           ← папку создать вручную
```

---

### Шаг 2: Установить зависимости PHP (Google API)

Подключитесь к серверу по SSH:

```bash
ssh root@ypr1.ru
cd /путь/к/сайту
```

Установите Composer (если нет):
```bash
curl -sS https://getcomposer.org/installer | php
php composer.phar install
```

ИЛИ через готовый composer.phar (он уже есть в оригинальном архиве):
```bash
php composer.phar install
```

Это создаст папку `vendor/` с библиотекой `google/apiclient`.

---

### Шаг 3: Настроить Google Drive API

#### 3.1. Создать проект в Google Cloud Console

1. Перейдите на [console.cloud.google.com](https://console.cloud.google.com)
2. Нажмите «Создать проект» → введите название, например `CBMO-Files`
3. Выберите созданный проект

#### 3.2. Включить Google Drive API

1. В меню слева → **API и сервисы** → **Библиотека**
2. Найдите **Google Drive API** → нажмите **Включить**

#### 3.3. Создать сервисный аккаунт

1. В меню слева → **API и сервисы** → **Учётные данные**
2. Нажмите **+ Создать учётные данные** → **Сервисный аккаунт**
3. Введите имя, например `cbmo-drive-service`
4. Нажмите **Создать и продолжить** → **Готово**

#### 3.4. Скачать JSON ключ

1. В списке сервисных аккаунтов нажмите на созданный аккаунт
2. Вкладка **Ключи** → **Добавить ключ** → **Создать новый ключ**
3. Выберите **JSON** → **Создать**
4. Скачается файл `project-name-xxxxx.json`
5. **Переименуйте** его в `google-drive-key.json`
6. **Загрузите** в папку `keys/` на сервере

> ❗ ВАЖНО: Никогда не публикуйте этот файл в GitHub!

#### 3.5. Создать папки в Google Drive и дать доступ сервисному аккаунту

1. Откройте [drive.google.com](https://drive.google.com)
2. Создайте три папки: **Клиенты**, **Отчёты**, **Договоры**
3. Для каждой папки: ПКМ → **Открыть доступ** → вставьте email сервисного аккаунта (вида `cbmo-drive-service@project.iam.gserviceaccount.com`) → роль **Редактор** → **Готово**

#### 3.6. Получить ID папок

Откройте каждую папку в Drive — в URL будет ID:
```
https://drive.google.com/drive/folders/FOLDER_ID_HERE
```
Скопируйте `FOLDER_ID_HERE` для каждой папки.

#### 3.7. Вставить ID в google_drive_init.php

Откройте файл `google_drive_init.php` и замените:
```php
define('FOLDER_IDS', [
    'Клиенты'  => 'REPLACE_WITH_CLIENTS_FOLDER_ID',   // ← вставьте ID папки Клиенты
    'Отчёты'   => 'REPLACE_WITH_REPORTS_FOLDER_ID',   // ← вставьте ID папки Отчёты
    'Договоры' => 'REPLACE_WITH_CONTRACTS_FOLDER_ID', // ← вставьте ID папки Договоры
]);
```

---

### Шаг 4: Настроить Telegram поддержку

Это для формы «✉️ Написать в поддержку» (уже работает на сайте).

Зарегистрировать webhook (один раз, в браузере):
```
https://api.telegram.org/bot8686712934:AAE9j6m_xQt4loVVvdi4jBagtmgKrvjfkoQ/setWebhook?url=https://ypr1.ru/telegram_webhook.php
```

---

### Шаг 5: Проверить работу

1. Откройте [https://ypr1.ru](https://ypr1.ru)
2. Нажмите вкладку **📁 Файлы**
3. Нажмите **⬆️ Загрузить файл**
4. Введите PIN: `271192`
5. Выберите файл → он загрузится в Google Drive
6. Файл появится в списке с кнопками **Открыть** и **✕**

---

## 🔐 PIN-код

| PIN | Назначение |
|---|---|
| `271192` | Загрузка и удаление файлов (файловый менеджер) |
| `1111` | Режим управления порталами (чат-бот) |
| `1234` | Режим инвентаризации (чат-бот) |
| `0000` | Телефонный справочник (чат-бот) |

PIN сохраняется в `sessionStorage` на время сессии браузера.

---

## ⚙️ Настройки

### Изменить PIN-код файлового менеджера

В двух местах:

**1. В `google_drive_init.php`:**
```php
define('UPLOAD_PIN', '271192'); // ← замените на новый PIN
```

**2. В `index.html`** (строка с `const FILE_PIN`):
```javascript
const FILE_PIN='271192'; // ← замените на тот же PIN
```

### Изменить максимальный размер файла

В `upload_file.php`:
```php
$maxSize = 50 * 1024 * 1024; // 50 МБ — измените по необходимости
```

### Добавить новую папку

1. Создайте папку в Google Drive, дайте доступ сервисному аккаунту
2. Добавьте в `google_drive_init.php`:
```php
define('FOLDER_IDS', [
    'Клиенты'  => 'ID...',
    'Отчёты'   => 'ID...',
    'Договоры' => 'ID...',
    'Акты'     => 'NEW_FOLDER_ID',  // ← новая папка
]);
```
3. Добавьте в `index.html` в секцию `.fm-sidebar`:
```html
<div class="fm-folder-item" data-folder="Акты" onclick="selectFolder('Акты')">
  <span>📋</span><span>Акты</span>
  <span class="fm-folder-count" id="count-Акты">—</span>
</div>
```
4. Добавьте в объект `FM_FOLDERS` в JS:
```javascript
const FM_FOLDERS={
  'Клиенты':{icon:'👥',label:'Клиенты'},
  'Отчёты':{icon:'📊',label:'Отчёты'},
  'Договоры':{icon:'📄',label:'Договоры'},
  'Акты':{icon:'📋',label:'Акты'},  // ← новая
};
```

---

## 🐞 Частые проблемы

### Файлы не загружаются: «Ошибка сервера»

- Проверьте, что `vendor/` создана (`php composer.phar install`)
- Проверьте путь к ключу: `keys/google-drive-key.json` должен существовать
- Проверьте права папки `uploads/`: `chmod 755 uploads/`
- Проверьте PHP error log: `tail -n 50 /var/log/apache2/error.log`

### «Неверный PIN-код» при правильном PIN

- Убедитесь, что `UPLOAD_PIN` в `google_drive_init.php` и `FILE_PIN` в `index.html` совпадают

### Файловый менеджер показывает «Нет соединения с сервером»

- Убедитесь, что `list_files.php` доступен: откройте `https://ypr1.ru/list_files.php?folder=Клиенты` в браузере
- Проверьте, что FOLDER_IDs заполнены в `google_drive_init.php`

### Файлы загружаются, но не отображаются

- Убедитесь, что сервисный аккаунт имеет доступ **Редактор** к папкам в Google Drive
- Проверьте, что в `list_files.php` указан правильный `$folderId`

### Google Drive: «The caller does not have permission»

- Откройте папку в Google Drive → Общий доступ → добавьте email сервисного аккаунта с ролью **Редактор**

---

## 📱 Мобильная версия

Сайт адаптирован для мобильных устройств:
- Вкладки перестраиваются в горизонтальную полосу
- Файловый менеджер: сайдбар папок становится горизонтальным
- Список файлов: скрываются колонки «Размер» и «Изменён»

---

## 🔄 Как обновить сайт

```bash
cd /Users/andrejbobyrev/keenetic-unified
git pull
```

Затем загрузите обновлённые файлы из папки `site/` на сервер по FTP/SFTP.

---

## 📝 Безопасность

| Угроза | Защита |
|---|---|
| Загрузка без авторизации | PIN-код 271192 проверяется на backend |
| Утечка ключей | `.gitignore` исключает `keys/*.json` |
| Большие файлы | Ограничение 50 МБ на backend |
| XSS в именах файлов | HTML-экранирование через `esc()` |
| CORS | Заголовки `Access-Control-Allow-Origin` |

---

## 📊 Как это работает

```
Пользователь → вводит PIN → браузер проверяет локально
                              ↓
              → выбирает файл (click или drag-drop)
                              ↓
              → POST /upload_file.php (с PIN в body)
                              ↓
              backend: проверяет PIN → загружает в Google Drive
                              ↓
              → возвращает { success, id, webViewLink }
                              ↓
              → файл появляется в списке (обновление GET /list_files.php)

Просмотр:
Пользователь → клик «Открыть»
              → PDF: iframe с drive.google.com/file/d/ID/preview
              → Картинка: <img src="drive.google.com/uc?id=ID">
              → Другое: Google Docs Viewer (viewer?srcid=ID)

Удаление:
Пользователь → клик «✕» → confirm() → GET /delete_file.php?id=ID&pin=PIN
              backend: проверяет PIN → удаляет файл из Drive
```
