"""
install_app.py - Installs the Anthropic SDK and puts a "SQL Assistant" shortcut on your desktop.
"""
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
SCRIPT = APP_DIR / "sql_assistant.pyw"


def ps_quote(s) -> str:
    return "'" + str(s).replace("'", "''") + "'"


def main():
    print("Installing the Anthropic Python package...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "--quiet", "anthropic"])

    if sys.platform != "win32":
        print(f"Done. Start the app with: python {SCRIPT}")
        return

    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        pythonw = Path(sys.executable)
    ps = (
        "$desktop = [Environment]::GetFolderPath('Desktop'); "
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $desktop 'SQL Assistant.lnk')); "
        f"$s.TargetPath = {ps_quote(pythonw)}; "
        f"$s.Arguments = {ps_quote(chr(34) + str(SCRIPT) + chr(34))}; "
        f"$s.WorkingDirectory = {ps_quote(APP_DIR)}; "
        "$s.Description = 'Ask questions about your SQLite database'; "
        "$s.Save()"
    )
    subprocess.check_call(["powershell", "-NoProfile", "-Command", ps])
    print("Created 'SQL Assistant' on your desktop. Double-click it to start.")


if __name__ == "__main__":
    main()
