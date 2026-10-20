@echo off
chcp 65001 > nul
title 貪食蛇
cd /d "%~dp0"
if not exist ".cache" mkdir ".cache"
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
echo 啟動貪食蛇中...（錯誤訊息會記在 .cache\snake_log.txt）
"%PY%" snake\snake.py %* > ".cache\snake_log.txt" 2>&1
type ".cache\snake_log.txt"
pause
