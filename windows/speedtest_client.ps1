$SERVER      = "http://SERVER_IP:8000"
$ROUTER_NAME = "ROUTER"

function Run-ST {
    try {
        $o = & speedtest --format=json 2>$null | ConvertFrom-Json
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
