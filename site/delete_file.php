<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

require_once __DIR__ . '/google_drive_init.php';

// PIN проверка (передаётся GET параметром или заголовком)
$pin = $_GET['pin'] ?? ($_SERVER['HTTP_X_PIN'] ?? '');
if ($pin !== UPLOAD_PIN) {
    http_response_code(403);
    echo json_encode(['success' => false, 'error' => 'Неверный PIN-код']);
    exit;
}

$fileId = $_GET['id'] ?? '';
if (!$fileId) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'ID файла не указан']);
    exit;
}

try {
    $client  = getGoogleDriveClient();
    $service = new Google\Service\Drive($client);
    $service->files->delete($fileId);
    echo json_encode(['success' => true]);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => $e->getMessage()]);
}
