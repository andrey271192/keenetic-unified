<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

// =============================================================
//  Local file listing (Google Drive disabled)
// =============================================================
$allowedFolders = ['Клиенты', 'Отчёты', 'Договоры'];
$folderName = (string)($_GET['folder'] ?? 'Клиенты');
if (!in_array($folderName, $allowedFolders, true)) {
    http_response_code(400);
    echo json_encode(['error' => 'Неизвестная папка: ' . $folderName]);
    exit;
}

$folderPath = __DIR__ . '/uploads/' . $folderName;
if (!is_dir($folderPath)) {
    echo json_encode(['files' => []]);
    exit;
}

$entries = @scandir($folderPath);
if (!is_array($entries)) {
    http_response_code(500);
    echo json_encode(['error' => 'Не удалось прочитать папку']);
    exit;
}

$files = [];
foreach ($entries as $fn) {
    if ($fn === '.' || $fn === '..') continue;
    $full = $folderPath . '/' . $fn;
    if (!is_file($full)) continue;

    $origName = $fn;
    $parts = explode('__', $fn, 2);
    if (count($parts) === 2 && $parts[1] !== '') {
        $origName = $parts[1];
    }

    $files[] = [
        'id' => '/uploads/' . rawurlencode($folderName) . '/' . rawurlencode($fn),
        'name' => $origName,
        'mimeType' => @mime_content_type($full) ?: 'application/octet-stream',
        'size' => (int)@filesize($full),
        'modifiedTime' => gmdate('c', @filemtime($full) ?: time()),
    ];
}

usort($files, function ($a, $b) {
    return strcmp((string)($b['modifiedTime'] ?? ''), (string)($a['modifiedTime'] ?? ''));
});

echo json_encode(['files' => $files], JSON_UNESCAPED_UNICODE);
