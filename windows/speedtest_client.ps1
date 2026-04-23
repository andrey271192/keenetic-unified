$SERVER      = "http://SERVER_IP:8000"
$ROUTER_NAME = "ROUTER"

# Find speedtest binary: PATH → script dir → speedtest-monitor → common paths
$ST_BIN = Get-Command speedtest -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $ST_BIN) {
    $candidates = @(
        "$PSScriptRoot\speedtest.exe",
        "$env:USERPROFILE\speedtest-monitor\speedtest.exe",
        "$env:LOCALAPPDATA\keenetic-unified\speedtest.exe",
        "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Ookla.Speedtest*\speedtest.exe",
        "C:\Program Files\Ookla\Speedtest CLI\speedtest.exe"
    )
    foreach ($c in $candidates) {
        $found = Get-Item $c -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) { $ST_BIN = $found.FullName; break }
    }
}

function Run-ST {
    if (-not $ST_BIN) {
        Write-Host "speedtest not found. Run: winget install Ookla.Speedtest"
        return @{ down=0; up=0; ping=0 }
    }
    try {
        $o = & "$ST_BIN" --format=json --accept-license --accept-gdpr 2>$null | ConvertFrom-Json
        return @{
            down = [math]::Round($o.download.bandwidth * 8 / 1e6, 1)
            up   = [math]::Round($o.upload.bandwidth * 8 / 1e6, 1)
            ping = [math]::Round($o.ping.latency, 0)
        }
    } catch { return @{ down=0; up=0; ping=0 } }
}

function Run-RU {
    # RU ping — прямой пинг до российского сервера (не идёт через VPN)
    $ru_ping = 0
    try {
        $p = Test-Connection -ComputerName "ya.ru" -Count 3 -ErrorAction Stop
        $ru_ping = [math]::Round(($p | Measure-Object -Property ResponseTime -Average).Average, 0)
    } catch { $ru_ping = 0 }

    # RU download — WebClient качает с российского CDN напрямую (минуя VPN)
    # Российские IP не маршрутизируются через VPN в HydraRoute
    $ru_down = 0
    $test_urls = @(
        "http://mirror.yandex.ru/debian/ls-lR.gz",   # Yandex mirror ~20MB
        "http://lg.fiord.ru/10mb.test",               # Fiord RU 10MB
        "http://speedtest.ucom.ru/10mb.bin"           # UCOM 10MB
    )
    foreach ($url in $test_urls) {
        try {
            $wc = New-Object System.Net.WebClient
            $wc.Headers.Add("User-Agent", "Mozilla/5.0")
            $start = Get-Date
            $data = $wc.DownloadData($url)
            $elapsed = [math]::Max(((Get-Date) - $start).TotalSeconds, 0.1)
            if ($data.Length -gt 100000) {
                $ru_down = [math]::Round($data.Length * 8 / 1e6 / $elapsed, 1)
                break
            }
        } catch { continue }
    }

    return @{ down = $ru_down; ping = $ru_ping }
}

$vpn = Run-ST
$ru  = Run-RU

Write-Host "VPN: down=$($vpn.down) up=$($vpn.up) ping=$($vpn.ping)"
Write-Host "RU:  down=$($ru.down) ping=$($ru.ping)"

$body = @{
    router   = $ROUTER_NAME
    vpn_down = $vpn.down; vpn_up = $vpn.up
    ru_down  = $ru.down;  ru_up  = 0
    ping     = $vpn.ping; ru_ping = $ru.ping
} | ConvertTo-Json

try { Invoke-RestMethod -Uri "$SERVER/api/push_speed" -Method POST -Body $body -ContentType "application/json" }
catch { Write-Host "Server unreachable: $_" }
