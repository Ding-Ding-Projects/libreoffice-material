@echo off
setlocal DisableDelayedExpansion
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0bin\Invoke-RootBuildRoute.ps1" -Route Bootstrap %*
exit /b %ERRORLEVEL%
