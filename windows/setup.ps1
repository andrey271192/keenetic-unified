param(
    [Parameter(Mandatory=$true)][string]$ServerIP,
    [Parameter(Mandatory=$true)][string]$RouterName,
    [string]$RouterLanIP = "192.168.88.1"
)

$dir = "$env:LOCALAPPDATA\keenetic-unified"
New-Item -ItemType Directory -Force -Path $dir | Out-Null

Copy-Item "$PSScriptRoot\check_sites.ps1" "$dir\" -Force
Copy-Item "$PSScriptRoot\speedtest_client.ps1" "$dir\" -Force

$cs = Get-Content "$dir\check_sites.ps1" -Raw
$cs = $cs -replace 'SERVER_IP', $ServerIP
$cs = $cs -replace '"ROUTER"', "`"$RouterName`""
$cs = $cs -replace 'ROUTER_LAN_IP', $RouterLanIP
Set-Content "$dir\check_sites.ps1" -Value $cs

$ss = Get-Content "$dir\speedtest_client.ps1" -Raw
$ss = $ss -replace 'SERVER_IP', $ServerIP
$ss = $ss -replace '"ROUTER"', "`"$RouterName`""
Set-Content "$dir\speedtest_client.ps1" -Value $ss

$action1 = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$dir\check_sites.ps1`""
$trigger1 = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 15) -Once -At (Get-Date)
Register-ScheduledTask -TaskName "Keenetic-CheckSites" -Action $action1 -Trigger $trigger1 -Force | Out-Null

$action2 = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$dir\speedtest_client.ps1`""
$trigger2 = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Hours 4) -Once -At (Get-Date)
Register-ScheduledTask -TaskName "Keenetic-Speedtest" -Action $action2 -Trigger $trigger2 -Force | Out-Null

Write-Host "OK: $RouterName -> $ServerIP (LAN: $RouterLanIP)"
Write-Host "Files: $dir"
