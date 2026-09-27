"""
configure_claude.py - Adds the local SQLite MCP server to Claude Desktop's config.

- Finds claude_desktop_config.json (standard install or Microsoft Store install)
- Keeps any MCP servers you already have
- Backs up the existing file before changing it
- Writes the database path with correct JSON escaping (no manual \\ needed)
- Uses the full path to uvx so Claude Desktop can find it
"""
import json
import os
import shutil
import sys
from pathlib import Path

SERVER_NAME = "local-sqlite"
DB_PATH = Path(__file__).resolve().parent / "local_store.db"


def find_config_path() -> Path:
    if len(sys.argv) > 1:                      # optional override: python configure_claude.py <path>
        return Path(sys.argv[1])
    appdata = os.environ.get("APPDATA")
    localappdata = os.environ.get("LOCALAPPDATA")
    if appdata:                                # Windows
        # Microsoft Store installs keep the config inside a package folder
        if localappdata:
            for pkg in Path(localappdata, "Packages").glob("Claude_*"):
                store_cfg = pkg / "LocalCache" / "Roaming" / "Claude"
                if store_cfg.exists():
                    return store_cfg / "claude_desktop_config.json"
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
    return Path.home() / ".config/Claude/claude_desktop_config.json"


def main():
    if not DB_PATH.exists():
        sys.exit("local_store.db not found. Run 'python seed_db.py' first.")

    uvx = shutil.which("uvx")
    if not uvx:
        sys.exit("uvx not found on PATH. Install uv first (see README), then open a NEW terminal and retry.")

    cfg_path = find_config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    if cfg_path.exists() and cfg_path.stat().st_size > 0:
        try:
            config = json.loads(cfg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            sys.exit(f"Your existing config has invalid JSON ({e}). Fix or delete it, then re-run:\n  {cfg_path}")
        backup = cfg_path.with_name(cfg_path.name + ".bak")
        shutil.copy2(cfg_path, backup)
        print(f"Backed up existing config to: {backup}")

    config.setdefault("mcpServers", {})[SERVER_NAME] = {
        "command": uvx,
        "args": ["mcp-server-sqlite", "--db-path", str(DB_PATH)],
    }
    cfg_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    print(f"Updated: {cfg_path}\n")
    print(json.dumps(config, indent=2))
    print("\nNext: fully QUIT Claude Desktop (system tray > Quit, not just close the window) and reopen it.")


if __name__ == "__main__":
    main()
