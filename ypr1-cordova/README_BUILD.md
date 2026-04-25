## ypr1-app (Cordova) — сборка APK

Этот каталог подготовлен так, чтобы вы могли собрать APK из мобильной версии `/app/`.

### Самый быстрый способ получить APK

- **BuildFirebase**: загрузите файл `www/index.html` (как `index.html`) и `config.xml` в выбранный сервис, либо просто загрузите исходный `ypr1-app.html` как указано в ваших инструкциях.

### Локальная сборка (Windows/Mac/Linux)

1) Установите зависимости:
- Node.js LTS
- Java **JDK 17**
- Android Studio (SDK 33+)
- Cordova:

```bash
npm i -g cordova
```

2) Сборка:

```bash
cd ypr1-cordova
npm i
cordova platform add android
cordova build android
```

APK будет в:
`platforms/android/app/build/outputs/apk/debug/app-debug.apk`

