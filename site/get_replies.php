<?php
// =============================================================
//  get_replies.php — фронт получает новые сообщения по тикету
//  GET ?ticket_id=XXX&since=TIMESTAMP
// =============================================================
$ticketsFile = __DIR__ . '/tickets.json';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

$ticketId = $_GET['ticket_id'] ?? '';
$since    = (int)($_GET['since'] ?? 0);

if (!preg_match('/^[a-f0-9]{16}$/', $ticketId)) {
    echo json_encode(['ok' => false, 'error' => 'bad_ticket']);
    exit;
}

if (!file_exists($ticketsFile)) {
    echo json_encode(['ok' => true, 'messages' => []]);
    exit;
}

$tickets = json_decode(@file_get_contents($ticketsFile), true) ?: [];
if (!isset($tickets[$ticketId])) {
    echo json_encode(['ok' => true, 'messages' => []]);
    exit;
}

$msgs = $tickets[$ticketId]['messages'] ?? [];
$new = [];
foreach ($msgs as $m) {
    if ((int)($m['ts'] ?? 0) > $since) $new[] = $m;
}

echo json_encode(['ok' => true, 'messages' => $new, 'now' => time()], JSON_UNESCAPED_UNICODE);
