<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

// =============================================================
//  Local file delete (Google Drive disabled)
// =============================================================
$PIN = '271192';
$pin = $_GET['pin'] ?? ($_SERVER['HTTP_X_PIN'] ?? '');
if ($pin !== $PIN) {
    http_response_code(403);
    echo json_encode(['success' => false, 'error' => 'Неверный PIN-код']);
    exit;
}

$id = (string)($_GET['id'] ?? '');
if ($id === '') {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'ID файла не указан']);
    exit;
}

// ожидаем /uploads/<folder>/<file>
if (!preg_match('#^/uploads/([^/]+)/([^/]+)$#', $id, $m)) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Неверный формат ID']);
    exit;
}
$folder = rawurldecode($m[1]);
$file = rawurldecode($m[2]);

$allowedFolders = ['Клиенты', 'Отчёты', 'Договоры'];
if (!in_array($folder, $allowedFolders, true)) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Неизвестная папка']);
    exit;
}

// строгий basename для защиты от traversal
$file = basename($file);
$path = __DIR__ . '/uploads/' . $folder . '/' . $file;
if (!is_file($path)) {
    http_response_code(404);
    echo json_encode(['success' => false, 'error' => 'Файл не найден']);
    exit;
}

if (!@unlink($path)) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Не удалось удалить файл']);
    exit;
}

echo json_encode(['success' => true]);
