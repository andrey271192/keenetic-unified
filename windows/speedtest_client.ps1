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
    # RU ping (ya.ru)
    $ru_ping = 0
    try {
        $p = Test-Connection -ComputerName "ya.ru" -Count 3 -ErrorAction Stop
        $ru_ping = [math]::Round(($p | Measure-Object -Property ResponseTime -Average).Average, 0)
    } catch { $ru_ping = 0 }

    # RU download — download 10MB from Selectel, measure bytes actually received
    $ru_down = 0
    $urls = @(
        "https://speedtest.selectel.ru/10mb",
        "http://speedtest.selectel.ru/10mb",
        "http://ipv4.download.thinkbroadband.com/10MB.zip"
    )
    foreach ($url in $urls) {
        try {
            $start = Get-Date
            $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 30 -ErrorAction Stop
            $elapsed = [math]::Max(((Get-Date) - $start).TotalSeconds, 0.1)
            $bytes = if ($resp.Content -is [byte[]]) { $resp.Content.Length } else { [System.Text.Encoding]::UTF8.GetByteCount($resp.Content) }
            if ($bytes -gt 0) {
                $ru_down = [math]::Round($bytes * 8 / 1e6 / $elapsed, 1)
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
