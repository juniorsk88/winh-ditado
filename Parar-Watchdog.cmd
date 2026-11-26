@echo off
chcp 65001 >nul
title Parar vigia do ditado
setlocal

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'WinhDitadoVigia' -ErrorAction SilentlyContinue;" ^
  "$n = 0;" ^
  "Get-CimInstance Win32_Process -Filter \"Name='powershell.exe'\" | Where-Object { $_.CommandLine -and $_.CommandLine -like '*watchdog-ditado.ps1*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; $n++ };" ^
  "Write-Host ('Vigia parado (removido do autostart). Processos encerrados: ' + $n);" ^
  "Write-Host 'O ditado em si continua como estava - para parar ele, use stop-winh.cmd'"

echo.
pause
