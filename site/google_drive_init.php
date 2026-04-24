<?php
/**
 * Инициализация Google Drive API
 * Используется как сервисный аккаунт (Service Account JSON Key)
 */

require_once __DIR__ . '/vendor/autoload.php';

function getGoogleDriveClient() {
    $client = new Google\Client();
    $client->setApplicationName('CBMO File Manager');
    $client->setAuthConfig(__DIR__ . '/keys/google-drive-key.json');
    $client->setScopes([Google\Service\Drive::DRIVE]);
    $client->setAccessType('offline');
    return $client;
}

// =============================================
//  FOLDER IDs — замените на ваши реальные ID папок в Google Drive
//  Как получить ID: откройте папку в Drive, скопируйте часть URL после /folders/
//  Например: https://drive.google.com/drive/folders/FOLDER_ID_HERE
// =============================================
define('FOLDER_IDS', [
    'Клиенты'  => 'REPLACE_WITH_CLIENTS_FOLDER_ID',
    'Отчёты'   => 'REPLACE_WITH_REPORTS_FOLDER_ID',
    'Договоры' => 'REPLACE_WITH_CONTRACTS_FOLDER_ID',
]);

// PIN-код для защиты загрузки
define('UPLOAD_PIN', '271192');
