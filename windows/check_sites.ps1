$SERVER          = "http://212.118.42.105:8000"
$ROUTER_NAME     = "Andrey"
$ROUTER_SSH_HOST = "192.168.88.1:22"
$ROUTER_SSH_USER = "root"
$ROUTER_SSH_PASS = "keenetic"
$sites = @{
    "YouTube"  = "https://www.youtube.com"
    "Netflix"  = "https://www.netflix.com"
    "Telegram" = "https://web.telegram.org"
}
$results = @{}
foreach ($n in $sites.Keys) {
    try {
        Invoke-WebRequest -Uri $sites[$n] -TimeoutSec 15 -UseBasicParsing -ErrorAction Stop | Out-Null
        $results[$n] = $true
    } catch {
        $results[$n] = $false
    }
}
$body = @{ router = $ROUTER_NAME; sites = $results } | ConvertTo-Json
try {
    $resp = Invoke-RestMethod -Uri "$SERVER/api/push_sites" -Method POST -Body $body -ContentType "application/json"
    if ($resp.restart_neo) {
        echo y | plink -ssh -l $ROUTER_SSH_USER -pw $ROUTER_SSH_PASS $ROUTER_SSH_HOST "neo restart" 2>$null
        Start-Sleep 120
        $re = @{}
        foreach ($n in $sites.Keys) {
            try { Invoke-WebRequest -Uri $sites[$n] -TimeoutSec 15 -UseBasicParsing -ErrorAction Stop | Out-Null; $re[$n]=$true }
            catch { $re[$n]=$false }
        }
        $body2 = @{ router = $ROUTER_NAME; sites = $re; after_restart = $true } | ConvertTo-Json
        Invoke-RestMethod -Uri "$SERVER/api/push_sites_recheck" -Method POST -Body $body2 -ContentType "application/json"
    }
} catch {
    Write-Host "Server unreachable: $_"
}
