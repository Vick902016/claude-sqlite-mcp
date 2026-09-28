@echo off
REM Installs SQL Assistant and creates a desktop shortcut
cd /d "%~dp0"
python install_app.py || (echo. & echo Install failed. See the message above. & pause & exit /b 1)
echo.
pause
