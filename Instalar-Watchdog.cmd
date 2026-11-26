@echo off
chcp 65001 >nul
title Instalar vigia do ditado
setlocal

set "PS=%~dp0watchdog-ditado.ps1"
if not exist "%PS%" (
  echo [ERRO] watchdog-ditado.ps1 nao encontrado ao lado deste .cmd
  pause
  exit /b 1
)

echo Instalando o vigia do ditado (Win+H)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ps = '%PS%';" ^
  "$cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"' + $ps + '\"';" ^
  "Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'WinhDitadoVigia' -Value $cmd -Type String;" ^
  "Get-CimInstance Win32_Process -Filter \"Name='powershell.exe'\" | Where-Object { $_.CommandLine -and $_.CommandLine -like '*watchdog-ditado.ps1*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue };" ^
  "Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File',$ps -WindowStyle Hidden;" ^
  "Start-Sleep -Seconds 3;" ^
  "Write-Host 'Vigia instalado e rodando. Ele reinicia o ditado se ele sumir.'"

echo.
echo Teste: feche o ditado pelo Gerenciador de Tarefas e espere 30 s.
pause
