<?php
// =============================================================
//  send_message.php — создание тикета + отправка в Telegram
//  С сервера должен быть доступ api.telegram.org:443 (иначе таймаут).
//  Если хостинг блокирует Telegram:
//    export TELEGRAM_HTTP_PROXY="http://IP:PORT"   # HTTP-прокси с выходом в интернет
//    export TELEGRAM_RELAX_SSL=1                 # только при ошибках SSL (не отключает блокировку порта)
//  Переменные задайте в pool php-fpm (env[...]) или в /etc/environment и перезапустите php-fpm.
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

function relax_ssl(): bool
{
    return getenv('TELEGRAM_RELAX_SSL') === '1' || getenv('TELEGRAM_RELAX_SSL') === 'true';
}

function tg_http_proxy(): string
{
    $p = getenv('TELEGRAM_HTTP_PROXY');
    if ($p) {
        return $p;
    }
    $p = getenv('HTTPS_PROXY');
    if ($p) {
        return $p;
    }
    return (string) (getenv('https_proxy') ?: '');
}

/** Для stream-контекста: tcp://host:port */
function tg_proxy_tcp(string $proxyUrl): ?string
{
    $proxyUrl = trim($proxyUrl);
    if ($proxyUrl === '') {
        return null;
    }
    if (preg_match('#^https?://([^/:]+)(?::(\d+))?#i', $proxyUrl, $m)) {
        $port = isset($m[2]) && $m[2] !== '' ? (int) $m[2] : 8080;
        return 'tcp://' . $m[1] . ':' . $port;
    }
    return null;
}

/**
 * @return array{ok:bool, body:string, http:int, curl_err?:string}
 */
function tg_curl_post(string $url, $postFields, int $retries = 3): array
{
    $lastErr = '';
    for ($attempt = 0; $attempt < $retries; $attempt++) {
        if ($attempt > 0) {
            usleep(800000);
        }
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $postFields);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 15);
        curl_setopt($ch, CURLOPT_TIMEOUT, 60);
        curl_setopt($ch, CURLOPT_IPRESOLVE, CURL_IPRESOLVE_V4);
        curl_setopt($ch, CURLOPT_HTTP_VERSION, CURL_HTTP_VERSION_1_1);
        curl_setopt($ch, CURLOPT_ENCODING, '');
        if (relax_ssl()) {
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);
        }
        $px = tg_http_proxy();
        if ($px !== '') {
            curl_setopt($ch, CURLOPT_PROXY, $px);
            curl_setopt($ch, CURLOPT_PROXYTYPE, CURLPROXY_HTTP);
        }
        $body = curl_exec($ch);
        $http = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $errno = curl_errno($ch);
        $lastErr = curl_error($ch);
        curl_close($ch);
        if ($body !== false && $http > 0) {
            return ['ok' => true, 'body' => (string) $body, 'http' => $http, 'curl_err' => $lastErr];
        }
        @error_log("send_message curl attempt " . ($attempt + 1) . " errno=$errno err=$lastErr");
    }
    return ['ok' => false, 'body' => '', 'http' => 0, 'curl_err' => $lastErr];
}

/**
 * Запасной путь для sendMessage (JSON), без вложения.
 * @return array{ok:bool, body:string, http:int}
 */
function tg_stream_json_post(string $botToken, string $chatId, string $text): array
{
    $url = "https://api.telegram.org/bot{$botToken}/sendMessage";
    $payload = json_encode(['chat_id' => $chatId, 'text' => $text], JSON_UNESCAPED_UNICODE);
    if ($payload === false) {
        return ['ok' => false, 'body' => '', 'http' => 0];
    }
    $ssl = [
        'verify_peer' => !relax_ssl(),
        'verify_peer_name' => !relax_ssl(),
    ];
    $httpOpts = [
        'method' => 'POST',
        'header' => "Content-Type: application/json\r\nContent-Length: " . strlen($payload) . "\r\n",
        'content' => $payload,
        'timeout' => 60,
        'ignore_errors' => true,
    ];
    $tcp = tg_proxy_tcp(tg_http_proxy());
    if ($tcp !== null) {
        $httpOpts['proxy'] = $tcp;
        $httpOpts['request_fulluri'] = true;
    }
    $ctx = stream_context_create([
        'http' => $httpOpts,
        'ssl' => $ssl,
    ]);
    $http = 0;
    $raw = @file_get_contents($url, false, $ctx);
    if (isset($http_response_header[0]) && preg_match('/\s(\d{3})\s/', $http_response_header[0], $m)) {
        $http = (int) $m[1];
    }
    $ok = $raw !== false && $http === 200;
    if (!$ok) {
        @error_log('send_message stream fallback http=' . $http . ' len=' . strlen((string) $raw));
    }
    return ['ok' => $ok, 'body' => $raw === false ? '' : (string) $raw, 'http' => $http];
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
$response = '';
$httpCode = 0;

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
    $r = tg_curl_post($url, $postFields, 4);
    if (!$r['ok']) {
        die('curl_error');
    }
    $response = $r['body'];
    $httpCode = $r['http'];
} else {
    $caption = tg_clip($caption, 4000);
    $url = "https://api.telegram.org/bot{$botToken}/sendMessage";
    $postFields = ['chat_id' => $chatId, 'text' => $caption];
    $r = tg_curl_post($url, $postFields, 4);
    if ($r['ok'] && $r['http'] === 200) {
        $response = $r['body'];
        $httpCode = 200;
    } else {
        $sr = tg_stream_json_post($botToken, $chatId, $caption);
        if ($sr['ok'] && $sr['http'] === 200) {
            $response = $sr['body'];
            $httpCode = 200;
        } elseif (!$r['ok']) {
            die('curl_error');
        } else {
            $httpCode = $r['http'];
            $response = $r['body'];
        }
    }
}

if ($httpCode !== 200) {
    @error_log('send_message Telegram HTTP ' . $httpCode . ' body=' . substr($response, 0, 500));
    die('telegram_http');
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
