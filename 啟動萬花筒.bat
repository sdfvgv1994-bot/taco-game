@echo off
chcp 65001 > nul
title 萬花筒
cd /d "%~dp0"
if not exist ".cache" mkdir ".cache"
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
echo 啟動萬花筒中...（錯誤訊息會記在 .cache\kaleidoscope_log.txt）
"%PY%" kaleidoscope\kaleidoscope.py %* > ".cache\kaleidoscope_log.txt" 2>&1
type ".cache\kaleidoscope_log.txt"
pause
