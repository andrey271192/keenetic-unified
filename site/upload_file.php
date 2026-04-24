<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

require_once __DIR__ . '/google_drive_init.php';

// ── PIN проверка ──────────────────────────────────────
$pin = $_POST['pin'] ?? ($_SERVER['HTTP_X_PIN'] ?? '');
if ($pin !== UPLOAD_PIN) {
    http_response_code(403);
    echo json_encode(['success' => false, 'error' => 'Неверный PIN-код']);
    exit;
}

// ── Папка ────────────────────────────────────────────
$folderName = $_POST['folder'] ?? 'Клиенты';
$folderId   = FOLDER_IDS[$folderName] ?? null;
if (!$folderId) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Неизвестная папка: ' . $folderName]);
    exit;
}

// ── Файл ─────────────────────────────────────────────
if (!isset($_FILES['file']) || $_FILES['file']['error'] !== UPLOAD_ERR_OK) {
    $errCode = $_FILES['file']['error'] ?? 'нет файла';
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Файл не получен (код: ' . $errCode . ')']);
    exit;
}

$file    = $_FILES['file'];
$maxSize = 50 * 1024 * 1024; // 50 МБ

if ($file['size'] > $maxSize) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Файл слишком большой (макс. 50 МБ)']);
    exit;
}

// ── Загрузка в Google Drive ───────────────────────────
try {
    $client  = getGoogleDriveClient();
    $service = new Google\Service\Drive($client);

    $fileMetadata = new Google\Service\Drive\DriveFile([
        'name'    => $file['name'],
        'parents' => [$folderId],
    ]);

    $content   = file_get_contents($file['tmp_name']);
    $mimeType  = $file['type'] ?: 'application/octet-stream';

    $driveFile = $service->files->create($fileMetadata, [
        'data'       => $content,
        'mimeType'   => $mimeType,
        'uploadType' => 'multipart',
        'fields'     => 'id,name,webViewLink,mimeType',
    ]);

    // Открытый доступ для просмотра (только чтение)
    $permission = new Google\Service\Drive\Permission([
        'type' => 'anyone',
        'role' => 'reader',
    ]);
    $service->permissions->create($driveFile->getId(), $permission);

    $fileId      = $driveFile->getId();
    $webViewLink = 'https://drive.google.com/file/d/' . $fileId . '/view';

    echo json_encode([
        'success'     => true,
        'id'          => $fileId,
        'name'        => $driveFile->getName(),
        'webViewLink' => $webViewLink,
    ]);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => $e->getMessage()]);
}
