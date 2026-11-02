@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\play_board_games.ps1 -ListPorts
pause
