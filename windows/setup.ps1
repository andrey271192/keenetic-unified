param(
    [Parameter(Mandatory=$true)][string]$ServerIP,
    [Parameter(Mandatory=$true)][string]$RouterName,
    [string]$RouterLanIP = "192.168.88.1"
)

$dir = "$env:LOCALAPPDATA\keenetic-unified"
New-Item -ItemType Directory -Force -Path $dir | Out-Null

Copy-Item "$PSScriptRoot\speedtest_client.ps1" "$dir\" -Force

# Patch placeholders
$ss = Get-Content "$dir\speedtest_client.ps1" -Raw
$ss = $ss -replace 'SERVER_IP', $ServerIP
$ss = $ss -replace '"ROUTER"', "`"$RouterName`""
Set-Content "$dir\speedtest_client.ps1" -Value $ss

$script = "$dir\speedtest_client.ps1"
$ps     = "powershell.exe"
$args_sites = "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`" -Mode sites"
$args_speed = "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`" -Mode speed"

# Delete old tasks silently (ignore errors if they don't exist or need admin)
schtasks /delete /tn "Keenetic-CheckSites" /f 2>$null | Out-Null
schtasks /delete /tn "Keenetic-Speedtest"  /f 2>$null | Out-Null

# Create tasks for current user — no admin required
schtasks /create /tn "Keenetic-CheckSites" /tr "$ps $args_sites" /sc minute /mo 30 /f | Out-Null
schtasks /create /tn "Keenetic-Speedtest"  /tr "$ps $args_speed" /sc hourly /mo 4  /f | Out-Null

Write-Host "OK: $RouterName -> $ServerIP (LAN: $RouterLanIP)"
Write-Host "Sites check: every 30 min  (Keenetic-CheckSites)"
Write-Host "Speed test:  every 4 hours (Keenetic-Speedtest)"
Write-Host "Files: $dir"
