param(
    [ValidateSet("sites","speed","all")]
    [string]$Mode = "all"
)

$SERVER      = "http://SERVER_IP:8000"
$ROUTER_NAME = "ROUTER"

# Sites to check — these should be routed via VPN by HydraRoute on the router.
# PC is behind the router so it uses real HydraRoute DNS interception — honest check.
$SITES_TO_CHECK = @("canva.com", "instagram.com", "netflix.com", "youtube.com")

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
    # RU ping — direct ping to Russian server (bypasses VPN)
    $ru_ping = 0
    try {
        $p = Test-Connection -ComputerName "ya.ru" -Count 3 -ErrorAction Stop
        $ru_ping = [math]::Round(($p | Measure-Object -Property ResponseTime -Average).Average, 0)
    } catch { $ru_ping = 0 }

    # RU download — WebClient downloads from Russian CDN directly (HydraRoute keeps RU IPs local)
    $ru_down = 0
    $test_urls = @(
        "http://mirror.yandex.ru/debian/ls-lR.gz",
        "http://lg.fiord.ru/10mb.test",
        "http://speedtest.ucom.ru/10mb.bin"
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

function Check-Sites {
    # PC is behind the router — uses HydraRoute DNS, so this is a real end-user check.
    $results = @{}
    foreach ($site in $SITES_TO_CHECK) {
        try {
            $req = [System.Net.HttpWebRequest]::Create("https://$site")
            $req.Timeout     = 10000
            $req.UserAgent   = "Mozilla/5.0"
            $req.AllowAutoRedirect = $true
            $resp = $req.GetResponse()
            $code = [int]$resp.StatusCode
            $resp.Close()
            $results[$site] = ($code -ge 200 -and $code -lt 600)
        } catch [System.Net.WebException] {
            # Connection refused / timeout / SSL error = site unreachable
            $status = $_.Exception.Response
            if ($status) {
                $code = [int]$status.StatusCode
                # Any HTTP response (even 403/503) means TCP+DNS works
                $results[$site] = $true
            } else {
                $results[$site] = $false
            }
        } catch {
            $results[$site] = $false
        }
    }
    return $results
}

# --- Sites check (Mode: sites | all) ---
if ($Mode -eq "sites" -or $Mode -eq "all") {
    Write-Host "Checking sites..."
    $sites = Check-Sites
    foreach ($s in $sites.Keys) {
        $icon = if ($sites[$s]) { "OK" } else { "FAIL" }
        Write-Host "  $icon $s"
    }
    $sitesBody = @{ router = $ROUTER_NAME; sites = $sites } | ConvertTo-Json -Depth 3
    try {
        $siteResp = Invoke-RestMethod -Uri "$SERVER/api/push_sites" -Method POST -Body $sitesBody -ContentType "application/json"
        Write-Host "Sites sent. restart_neo=$($siteResp.restart_neo)"
    } catch { Write-Host "Sites send failed: $_" }
}

# --- Speed test (Mode: speed | all) ---
if ($Mode -eq "speed" -or $Mode -eq "all") {
    Write-Host "Running speedtest (VPN)..."
    $vpn = Run-ST
    Write-Host "Running RU speed..."
    $ru = Run-RU
    Write-Host "VPN: down=$($vpn.down) up=$($vpn.up) ping=$($vpn.ping)"
    Write-Host "RU:  down=$($ru.down) ping=$($ru.ping)"
    $speedBody = @{
        router   = $ROUTER_NAME
        vpn_down = $vpn.down; vpn_up = $vpn.up
        ru_down  = $ru.down;  ru_up  = 0
        ping     = $vpn.ping; ru_ping = $ru.ping
    } | ConvertTo-Json
    try { Invoke-RestMethod -Uri "$SERVER/api/push_speed" -Method POST -Body $speedBody -ContentType "application/json" }
    catch { Write-Host "Speed send failed: $_" }
}
