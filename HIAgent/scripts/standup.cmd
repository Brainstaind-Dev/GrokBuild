@echo off
REM Convenience wrapper for standup.ps1
setlocal
set SCRIPT_DIR=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%standup.ps1" %*
endlocal
