@echo off
setlocal DisableDelayedExpansion
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0bin\Invoke-RootBuildRoute.ps1" -Route Program %*
exit /b %ERRORLEVEL%
