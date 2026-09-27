@echo off
REM One-click setup for the Claude + SQLite MCP project (Windows)
cd /d "%~dp0"

echo === Checking Python ===
python --version || (echo Python not found. Install from https://www.python.org and tick "Add to PATH". & pause & exit /b 1)

echo.
echo === Checking uv ===
where uvx >nul 2>&1
if errorlevel 1 (
    echo uv not found - installing...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)
where uvx || (echo uvx still not found. Close this window, open a NEW Command Prompt, and run setup.bat again. & pause & exit /b 1)

echo.
echo === Creating database ===
python seed_db.py || (pause & exit /b 1)

echo.
echo === Configuring Claude Desktop ===
python configure_claude.py || (pause & exit /b 1)

echo.
echo Done! Quit Claude Desktop from the system tray, reopen it, and start a new chat.
pause
