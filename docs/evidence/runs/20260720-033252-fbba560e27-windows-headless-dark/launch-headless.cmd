@echo off
setlocal DisableDelayedExpansion
set "VCL_DRAW_WIDGETS_FROM_FILE=1"
set "VCL_FILE_WIDGET_THEME=material"
set "SAL_SKIA=raster"
set "SAL_DISABLEGL=1"
set "SAL_LOG=+WARN.vcl.gdi"
"C:\Users\cntow\lo-material-vs2026-577059e27\msi-check\20260720-021814-9378266-fbba560e2-restart-suppression\program\soffice.exe" -env:UserInstallation=file:///C:/Users/cntow/AppData/Local/Temp/LibreOfficeMaterialQA/20260720-033252-fbba560e27-windows-headless-dark/profile --nologo --norestore --quickstart=no --language=en-US --pidfile="C:\Users\cntow\AppData\Local\Temp\LibreOfficeMaterialQA\20260720-033252-fbba560e27-windows-headless-dark\soffice.pid" --accept=pipe,name=LibreOfficeMaterialQA-fbba560e27-dark-c658b16e;urp 1>"C:\Users\cntow\AppData\Local\Temp\LibreOfficeMaterialQA\20260720-033252-fbba560e27-windows-headless-dark\logs\soffice.stdout.log" 2>"C:\Users\cntow\AppData\Local\Temp\LibreOfficeMaterialQA\20260720-033252-fbba560e27-windows-headless-dark\logs\soffice.stderr.log"
exit /b %ERRORLEVEL%