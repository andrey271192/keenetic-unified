$SERVER      = "http://SERVER_IP:8000"
$ROUTER_NAME = "ROUTER"

# Find speedtest binary: PATH → script dir → common install paths
$ST_BIN = Get-Command speedtest -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $ST_BIN) {
    $candidates = @(
        "$PSScriptRoot\speedtest.exe",
        "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Ookla.Speedtest*\speedtest.exe",
        "C:\Program Files\Ookla\Speedtest CLI\speedtest.exe"
    )
    foreach ($c in $candidates) {
        $found = Get-Item $c -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) { $ST_BIN = $found.FullName; break }
    }
}

function Run-ST {
    if (-not $ST_BIN) { Write-Host "speedtest not found. Run: winget install Ookla.Speedtest"; return @{ down=0; up=0; ping=0 } }
    try {
        $o = & "$ST_BIN" --format=json --accept-license --accept-gdpr 2>$null | ConvertFrom-Json
        return @{
            down = [math]::Round($o.download.bandwidth * 8 / 1e6, 1)
            up   = [math]::Round($o.upload.bandwidth * 8 / 1e6, 1)
            ping = [math]::Round($o.ping.latency, 0)
        }
    } catch { return @{ down=0; up=0; ping=0 } }
}

$vpn = Run-ST
$body = @{
    router   = $ROUTER_NAME
    vpn_down = $vpn.down; vpn_up = $vpn.up
    ru_down  = 0; ru_up = 0
    ping     = $vpn.ping; ru_ping = 0
} | ConvertTo-Json

try { Invoke-RestMethod -Uri "$SERVER/api/push_speed" -Method POST -Body $body -ContentType "application/json" }
catch { Write-Host "Server unreachable: $_" }
