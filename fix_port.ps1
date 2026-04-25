Get-NetTCPConnection -LocalPort 8091 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "done"
