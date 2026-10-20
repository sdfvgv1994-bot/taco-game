@echo off
chcp 65001 > nul
title 俄羅斯方塊
cd /d "%~dp0"
if not exist ".cache" mkdir ".cache"
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
echo 啟動俄羅斯方塊中...（錯誤訊息會記在 .cache\tetris_log.txt）
"%PY%" tetris\tetris.py %* > ".cache\tetris_log.txt" 2>&1
type ".cache\tetris_log.txt"
pause
