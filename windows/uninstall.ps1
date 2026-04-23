Write-Host "Removing Keenetic Unified from Windows..."
Unregister-ScheduledTask -TaskName "Keenetic-CheckSites" -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "Keenetic-Speedtest" -Confirm:$false -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\keenetic-unified" -ErrorAction SilentlyContinue
Write-Host "Done"
