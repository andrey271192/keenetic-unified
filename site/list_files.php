<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

require_once __DIR__ . '/google_drive_init.php';

$folderName = $_GET['folder'] ?? 'Клиенты';
$folderId   = FOLDER_IDS[$folderName] ?? null;

if (!$folderId) {
    http_response_code(400);
    echo json_encode(['error' => 'Неизвестная папка: ' . $folderName]);
    exit;
}

try {
    $client  = getGoogleDriveClient();
    $service = new Google\Service\Drive($client);

    $optParams = [
        'q'       => "'" . $folderId . "' in parents and trashed = false",
        'fields'  => 'files(id,name,mimeType,size,modifiedTime,webViewLink)',
        'orderBy' => 'modifiedTime desc',
        'pageSize' => 100,
    ];

    $results = $service->files->listFiles($optParams);
    $files   = [];

    foreach ($results->getFiles() as $file) {
        $fileId = $file->getId();
        $files[] = [
            'id'           => $fileId,
            'name'         => $file->getName(),
            'mimeType'     => $file->getMimeType(),
            'size'         => (int) $file->getSize(),
            'modifiedTime' => $file->getModifiedTime(),
            'webViewLink'  => 'https://drive.google.com/file/d/' . $fileId . '/view',
        ];
    }

    echo json_encode(['files' => $files]);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => $e->getMessage()]);
}
