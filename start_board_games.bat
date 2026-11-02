@echo off
setlocal
cd /d "%~dp0"
set "BOARD_PORT=%~1"
if not defined BOARD_PORT set /p "BOARD_PORT=Serial port [COM13]: "
if not defined BOARD_PORT set "BOARD_PORT=COM13"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\play_board_games.ps1 -Port "%BOARD_PORT%"
if errorlevel 1 pause
