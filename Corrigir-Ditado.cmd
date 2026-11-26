@echo off
chcp 65001 >nul
title Corrigir ditado (Win+H)
setlocal

echo Este script corrige o ditado que encerra sozinho 0,5 s depois de comecar.
echo Ele faz backup do arquivo antes de mexer.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0corrigir-ditado.ps1"
echo.
pause
