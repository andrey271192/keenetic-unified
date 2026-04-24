<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

// =============================================================
//  Local upload storage (Google Drive disabled)
// =============================================================
$PIN = '271192';
$pin = $_POST['pin'] ?? ($_SERVER['HTTP_X_PIN'] ?? '');
if ($pin !== $PIN) {
    http_response_code(403);
    echo json_encode(['success' => false, 'error' => 'Неверный PIN-код']);
    exit;
}

$allowedFolders = ['Клиенты', 'Отчёты', 'Договоры'];
$folderName = (string)($_POST['folder'] ?? 'Клиенты');
if (!in_array($folderName, $allowedFolders, true)) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Неизвестная папка: ' . $folderName]);
    exit;
}

if (!isset($_FILES['file']) || ($_FILES['file']['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) {
    $errCode = $_FILES['file']['error'] ?? 'нет файла';
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Файл не получен (код: ' . $errCode . ')']);
    exit;
}

$file = $_FILES['file'];
$maxSize = 50 * 1024 * 1024; // 50 МБ
if (($file['size'] ?? 0) > $maxSize) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Файл слишком большой (макс. 50 МБ)']);
    exit;
}

$uploadsRoot = __DIR__ . '/uploads';
$folderPath = $uploadsRoot . '/' . $folderName;
if (!is_dir($folderPath) && !@mkdir($folderPath, 0775, true)) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Не удалось создать папку для загрузки']);
    exit;
}

$origName = (string)($file['name'] ?? 'file');
$safeOrig = preg_replace('/[^\p{L}\p{N}\s\.\-\_\(\)\[\]]/u', '_', $origName);
$safeOrig = trim((string)$safeOrig);
if ($safeOrig === '') {
    $safeOrig = 'file';
}

$uniq = date('Ymd_His') . '_' . bin2hex(random_bytes(4));
$stored = $uniq . '__' . $safeOrig;
$target = $folderPath . '/' . $stored;

if (!@move_uploaded_file($file['tmp_name'], $target)) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Не удалось сохранить файл на сервере']);
    exit;
}

@chmod($target, 0664);

$relUrl = '/uploads/' . rawurlencode($folderName) . '/' . rawurlencode($stored);
$mime = @mime_content_type($target) ?: 'application/octet-stream';

echo json_encode([
    'success' => true,
    'id' => $relUrl,
    'name' => $safeOrig,
    'mimeType' => $mime,
    'size' => (int)filesize($target),
    'modifiedTime' => gmdate('c', @filemtime($target) ?: time()),
]);
