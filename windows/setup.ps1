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

$ps = "powershell.exe"
$script = "`"$dir\speedtest_client.ps1`""

# Task 1: check sites every 30 minutes
$action1  = New-ScheduledTaskAction -Execute $ps -Argument "-ExecutionPolicy Bypass -File $script -Mode sites"
$trigger1 = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 30) -Once -At (Get-Date)
Register-ScheduledTask -TaskName "Keenetic-CheckSites" -Action $action1 -Trigger $trigger1 -RunLevel Highest -Force | Out-Null

# Task 2: run speedtest every 4 hours
$action2  = New-ScheduledTaskAction -Execute $ps -Argument "-ExecutionPolicy Bypass -File $script -Mode speed"
$trigger2 = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Hours 4) -Once -At (Get-Date)
Register-ScheduledTask -TaskName "Keenetic-Speedtest" -Action $action2 -Trigger $trigger2 -RunLevel Highest -Force | Out-Null

Write-Host "OK: $RouterName -> $ServerIP (LAN: $RouterLanIP)"
Write-Host "Sites check: every 30 min  (Keenetic-CheckSites)"
Write-Host "Speed test:  every 4 hours (Keenetic-Speedtest)"
Write-Host "Files: $dir"
