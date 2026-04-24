<?php
// =============================================================
//  reply.php — пользователь отвечает со стороны сайта
//  POST ticket_id, text
// =============================================================
$botToken = '8686712934:AAE9j6m_xQt4loVVvdi4jBagtmgKrvjfkoQ';
$ticketsFile = __DIR__ . '/tickets.json';

header('Content-Type: application/json; charset=utf-8');

$ticketId = $_POST['ticket_id'] ?? '';
$text     = trim($_POST['text'] ?? '');

if (!preg_match('/^[a-f0-9]{16}$/', $ticketId) || $text === '') {
    echo json_encode(['ok' => false, 'error' => 'bad_input']); exit;
}
if (function_exists('mb_strlen')) {
    if (mb_strlen($text) > 4000) { $text = mb_substr($text, 0, 4000); }
} else {
    if (strlen($text) > 8000) { $text = substr($text, 0, 8000); }
}

$fp = fopen($ticketsFile, 'c+');
if (!$fp) { echo json_encode(['ok' => false]); exit; }
flock($fp, LOCK_EX);
$raw = stream_get_contents($fp);
$tickets = json_decode($raw, true) ?: [];

if (!isset($tickets[$ticketId])) {
    flock($fp, LOCK_UN); fclose($fp);
    echo json_encode(['ok' => false, 'error' => 'not_found']); exit;
}

$t = $tickets[$ticketId];

// Отправляем в Telegram как reply на исходное сообщение тикета
$tgText = "💬 Ответ от пользователя (тикет #{$ticketId})\n"
        . "👤 {$t['name']} · 📞 {$t['phone']}\n\n"
        . $text;

$postFields = [
    'chat_id' => $t['tg_chat_id'],
    'text'    => $tgText,
];
if (!empty($t['tg_msg_id'])) {
    $postFields['reply_to_message_id'] = $t['tg_msg_id'];
}

$ch = curl_init("https://api.telegram.org/bot{$botToken}/sendMessage");
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, $postFields);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
$resp = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpCode !== 200) {
    flock($fp, LOCK_UN); fclose($fp);
    echo json_encode(['ok' => false, 'error' => 'tg_fail']); exit;
}

$tickets[$ticketId]['messages'][] = [
    'from' => 'user',
    'text' => $text,
    'ts'   => time(),
];

ftruncate($fp, 0);
rewind($fp);
fwrite($fp, json_encode($tickets, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
flock($fp, LOCK_UN);
fclose($fp);

echo json_encode(['ok' => true, 'ts' => time()]);
