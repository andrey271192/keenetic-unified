<?php
// =============================================================
//  telegram_webhook.php — принимает Reply от оператора
// =============================================================
//  Настройка (один раз, в браузере):
//  https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://ВАШ_ДОМЕН/telegram_webhook.php
// =============================================================

$botToken = '8686712934:AAE9j6m_xQt4loVVvdi4jBagtmgKrvjfkoQ';
$ticketsFile = __DIR__ . '/tickets.json';

header('Content-Type: application/json; charset=utf-8');

$input = file_get_contents('php://input');
$update = json_decode($input, true);

if (!$update || !isset($update['message'])) {
    echo json_encode(['ok' => true]);
    exit;
}

$msg = $update['message'];
$text = $msg['text'] ?? $msg['caption'] ?? '';
$replyTo = $msg['reply_to_message'] ?? null;

// Работаем только с ответами (Reply) оператора
if (!$replyTo || !$text) {
    echo json_encode(['ok' => true]);
    exit;
}

$origText = $replyTo['text'] ?? $replyTo['caption'] ?? '';
// Извлекаем ticket_id из оригинального сообщения
if (!preg_match('/Тикет:\s*#([a-f0-9]{16})/u', $origText, $m)) {
    // Попробуем по message_id
    $replyMsgId = $replyTo['message_id'] ?? null;
    $tickets = file_exists($ticketsFile) ? (json_decode(@file_get_contents($ticketsFile), true) ?: []) : [];
    $foundTid = null;
    foreach ($tickets as $tid => $t) {
        if (isset($t['tg_msg_id']) && $t['tg_msg_id'] == $replyMsgId) { $foundTid = $tid; break; }
    }
    if (!$foundTid) { echo json_encode(['ok' => true]); exit; }
    $ticketId = $foundTid;
} else {
    $ticketId = $m[1];
}

// ---------- Добавляем ответ оператора в тикет ----------
$fp = fopen($ticketsFile, 'c+');
if (!$fp) { echo json_encode(['ok' => false]); exit; }
flock($fp, LOCK_EX);
$raw = stream_get_contents($fp);
$tickets = json_decode($raw, true) ?: [];

if (!isset($tickets[$ticketId])) {
    flock($fp, LOCK_UN); fclose($fp);
    echo json_encode(['ok' => true]); exit;
}

$operator = trim(($msg['from']['first_name'] ?? '') . ' ' . ($msg['from']['last_name'] ?? '')) ?: 'Оператор';

$tickets[$ticketId]['messages'][] = [
    'from' => 'operator',
    'name' => $operator,
    'text' => $text,
    'ts'   => time(),
];

ftruncate($fp, 0);
rewind($fp);
fwrite($fp, json_encode($tickets, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
flock($fp, LOCK_UN);
fclose($fp);

// Подтверждение в Telegram (галочка)
$ch = curl_init("https://api.telegram.org/bot{$botToken}/sendMessage");
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, [
    'chat_id' => $msg['chat']['id'],
    'text'    => "✅ Ответ отправлен пользователю (тикет #{$ticketId})",
    'reply_to_message_id' => $msg['message_id'],
]);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_exec($ch);
curl_close($ch);

echo json_encode(['ok' => true]);
