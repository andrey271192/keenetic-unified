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

$ticketId = bin2hex(random_bytes(8));

function tg_clip(string $s, int $max): string
{
    if (function_exists('mb_substr')) {
        return mb_substr($s, 0, $max, 'UTF-8');
    }
    return strlen($s) <= $max ? $s : substr($s, 0, $max);
}

$caption  = "📬 НОВОЕ ОБРАЩЕНИЕ\n\n";
$caption .= "🎫 Тикет: #{$ticketId}\n";
$caption .= "👤 Имя: $name\n";
$caption .= "📞 Телефон: $phone";
if ($email) {
    $caption .= "\n📧 Email: $email";
}
$caption .= "\n💬 Сообщение: $message";
$caption .= "\n🕒 " . date('Y-m-d H:i:s');
$caption .= "\n\n↩️ Ответьте на это сообщение (Reply) — ответ уйдёт пользователю на сайт.";

$hasFile = isset($_FILES['attachment']) && $_FILES['attachment']['error'] === UPLOAD_ERR_OK;
if ($hasFile) {
    $caption = tg_clip($caption, 1000);
    $fileSize = $_FILES['attachment']['size'];
    if ($fileSize > 20 * 1024 * 1024) {
        die('file_too_large');
    }
    $filePath = $_FILES['attachment']['tmp_name'];
    $fileName = basename($_FILES['attachment']['name']);
    $mimeType = mime_content_type($filePath);
    if ($mimeType === false) {
        $mimeType = 'application/octet-stream';
    }
    $fileData = new CURLFile($filePath, $mimeType, $fileName);
    $postFields = ['chat_id' => $chatId, 'document' => $fileData, 'caption' => $caption];
    $url = "https://api.telegram.org/bot{$botToken}/sendDocument";
} else {
    $caption = tg_clip($caption, 4000);
    $url = "https://api.telegram.org/bot{$botToken}/sendMessage";
    $postFields = ['chat_id' => $chatId, 'text' => $caption];
}

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, $postFields);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 12);
curl_setopt($ch, CURLOPT_TIMEOUT, 45);
curl_setopt($ch, CURLOPT_IPRESOLVE, CURL_IPRESOLVE_V4);
$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($response === false) {
    die('curl_error');
}
if ($httpCode !== 200) {
    die('error');
}

$resp = json_decode($response, true);
if (!($resp['ok'] ?? false)) {
    die('telegram_error');
}

$tgMessageId = $resp['result']['message_id'] ?? null;

$newTicket = [
    'ticket_id'    => $ticketId,
    'name'         => $name,
    'phone'        => $phone,
    'email'        => $email,
    'message'      => $message,
    'tg_chat_id'   => $chatId,
    'tg_msg_id'    => $tgMessageId,
    'created_at'   => time(),
    'messages'     => [
        ['from' => 'user', 'text' => $message, 'ts' => time()],
    ],
];

$jsonFlags = JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT;
if (defined('JSON_INVALID_UTF8_SUBSTITUTE')) {
    $jsonFlags |= JSON_INVALID_UTF8_SUBSTITUTE;
}

$saved = false;
$fp = @fopen($ticketsFile, 'c+');
if ($fp) {
    if (flock($fp, LOCK_EX)) {
        rewind($fp);
        $buf = stream_get_contents($fp);
        $tickets = [];
        if ($buf !== false && $buf !== '') {
            $tickets = json_decode($buf, true) ?: [];
        }
        $tickets[$ticketId] = $newTicket;
        $payload = json_encode($tickets, $jsonFlags);
        if ($payload !== false) {
            rewind($fp);
            ftruncate($fp, 0);
            $written = fwrite($fp, $payload);
            fflush($fp);
            $saved = ($written !== false);
        }
        flock($fp, LOCK_UN);
    }
    fclose($fp);
}

if (!$saved) {
    @error_log('send_message: tickets.json save failed for ' . $ticketId);
}

echo 'ok:' . $ticketId;
