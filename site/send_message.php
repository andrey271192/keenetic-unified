<?php
// =============================================================
//  send_message.php — создание тикета + отправка в Telegram
// =============================================================
$botToken = '8686712934:AAE9j6m_xQt4loVVvdi4jBagtmgKrvjfkoQ';
$chatId   = '371010834';
$ticketsFile = __DIR__ . '/tickets.json';

header('Content-Type: text/plain; charset=utf-8');

$name    = trim($_POST['name'] ?? '');
$phone   = trim($_POST['phone'] ?? '');
$email   = trim($_POST['email'] ?? '');
$message = trim($_POST['message'] ?? '');

$phoneDigits = preg_replace('/\D/', '', $phone);
if (!$name || strlen($phoneDigits) < 10 || !$message) {
    die('invalid_data');
}

// ---------- Генерация ticket_id ----------
$ticketId = bin2hex(random_bytes(8)); // 16 символов

// ---------- Формирование сообщения ----------
$caption  = "📬 НОВОЕ ОБРАЩЕНИЕ\n\n";
$caption .= "🎫 Тикет: #{$ticketId}\n";
$caption .= "👤 Имя: $name\n";
$caption .= "📞 Телефон: $phone";
if ($email) $caption .= "\n📧 Email: $email";
$caption .= "\n💬 Сообщение: $message";
$caption .= "\n🕒 " . date('Y-m-d H:i:s');
$caption .= "\n\n↩️ Ответьте на это сообщение (Reply) — ответ уйдёт пользователю на сайт.";

// ---------- Отправка в Telegram ----------
if (isset($_FILES['attachment']) && $_FILES['attachment']['error'] === UPLOAD_ERR_OK) {
    $fileSize = $_FILES['attachment']['size'];
    if ($fileSize > 20 * 1024 * 1024) { die('file_too_large'); }
    $filePath = $_FILES['attachment']['tmp_name'];
    $fileName = basename($_FILES['attachment']['name']);
    $mimeType = mime_content_type($filePath);
    $fileData = new CURLFile($filePath, $mimeType, $fileName);
    $postFields = ['chat_id' => $chatId, 'document' => $fileData, 'caption' => $caption];
    $url = "https://api.telegram.org/bot{$botToken}/sendDocument";
} else {
    $url = "https://api.telegram.org/bot{$botToken}/sendMessage";
    $postFields = ['chat_id' => $chatId, 'text' => $caption];
}

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, $postFields);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpCode !== 200) {
    die('error');
}

// ---------- Сохранение тикета ----------
$resp = json_decode($response, true);
$tgMessageId = $resp['result']['message_id'] ?? null;

$tickets = [];
if (file_exists($ticketsFile)) {
    $raw = @file_get_contents($ticketsFile);
    $tickets = json_decode($raw, true) ?: [];
}

$tickets[$ticketId] = [
    'ticket_id'    => $ticketId,
    'name'         => $name,
    'phone'        => $phone,
    'email'        => $email,
    'message'      => $message,
    'tg_chat_id'   => $chatId,
    'tg_msg_id'    => $tgMessageId,
    'created_at'   => time(),
    'messages'     => [
        ['from' => 'user', 'text' => $message, 'ts' => time()]
    ],
];

// Атомарная запись с блокировкой
$fp = fopen($ticketsFile, 'c+');
if ($fp) {
    flock($fp, LOCK_EX);
    ftruncate($fp, 0);
    rewind($fp);
    fwrite($fp, json_encode($tickets, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
    flock($fp, LOCK_UN);
    fclose($fp);
}

// ---------- Ответ фронту ----------
echo 'ok:' . $ticketId;
