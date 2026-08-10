@echo off
chcp 65001 >nul
"D:\anaconda\python.exe" "%~dp0tools\trigger_daily_check.py" --force
set "LOF_EXIT=%ERRORLEVEL%"
echo.
if not "%LOF_EXIT%"=="0" echo LOF提醒提交失败，请检查上方错误。
timeout /t 5 /nobreak >nul
exit /b %LOF_EXIT%
