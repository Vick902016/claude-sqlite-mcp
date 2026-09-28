# Claude + SQLite (local MCP project)
![SQL Assistant desktop app](sql_assistant_preview.png)

Includes **SQL Assistant**, a desktop app that turns plain-English questions into SQL using the Claude API. See [SQL_ASSISTANT.md](SQL_ASSISTANT.md).
Ask Claude Desktop questions about a local database in plain English. Claude reads the schema,
writes the SQL, runs it, and shows you the results. No server, ports, or passwords required.

## What's in this folder

| File | Purpose |
|---|---|
| `setup.bat` | One-click setup for Windows: checks Python, installs uv if needed, builds the DB, configures Claude |
| `seed_db.py` | Creates `local_store.db` with customers, orders, and support tickets (safe to re-run) |
| `configure_claude.py` | Adds the SQLite server to `claude_desktop_config.json` without overwriting your other settings |

## Prerequisites

- **Claude Desktop** (download from claude.ai/download)
- **Python 3.10+** from python.org, with "Add python.exe to PATH" ticked during install

## Setup (Windows)

1. Unzip this folder somewhere permanent, e.g. `C:\Users\<you>\sqlite_claude_project`.
   (The config points to this exact location, so don't move it afterwards; if you do, re-run setup.)
2. Double-click `setup.bat`, or from Command Prompt:
   ```
   cd %USERPROFILE%\sqlite_claude_project
   setup.bat
   ```
3. Fully quit Claude Desktop: right-click its icon in the system tray, then Quit. Closing the window is not enough.
4. Reopen Claude Desktop and start a new chat. Click the tools / connectors icon in the chat bar and confirm
   `local-sqlite` is listed with tools like `list_tables`, `describe_table`, and `read_query`.

## The sample data

- **customers** (8): name, email, signup date, plan (free / pro / enterprise). Tom and Liam have never ordered.
- **orders** (12): amount, date, status (completed / pending / refunded / cancelled)
- **support_tickets** (10): category, priority, status, opened/resolved timestamps, optional link to an order

## Prompts to try

- "What tables are in my database and how are they related?"
- "Show each customer's total spent on completed orders, highest first."
- "Find customers who have never placed an order."
- "What's the average ticket resolution time in hours, by category?"
- "List all open or in-progress tickets, sorted by priority, with the customer's name and plan."
- "Which enterprise customers have unresolved billing tickets?"
- "Show me the SQL first, then run it."

## Troubleshooting Q&A

**Q: `'#' is not recognized as an internal or external command`**
Command Prompt doesn't treat `#` as a comment. Skip comment lines when pasting, or use `REM`.

**Q: `mkdir -p ~/...` says "The syntax of the command is incorrect"**
CMD doesn't support `-p` or `~`. Use `mkdir %USERPROFILE%\sqlite_claude_project` instead.

**Q: The server doesn't show up in Claude Desktop.**
- Make sure you fully quit Claude from the system tray, not just closed the window.
- Open Claude Desktop > Settings > Developer. It shows each MCP server's status and a link to its logs.
- Logs are also in `%APPDATA%\Claude\logs\` (look for `mcp-server-local-sqlite.log`).

**Q: The log says `uvx` can't be found / `spawn uvx ENOENT`.**
Claude Desktop doesn't always see your terminal's PATH. `configure_claude.py` writes the full path to
`uvx.exe` to avoid this. If you installed uv after running setup, open a new Command Prompt and re-run
`python configure_claude.py`.

**Q: `uvx` isn't found right after installing uv.**
The installer updates PATH for new terminals only. Close Command Prompt, open a new one, and re-run `setup.bat`.

**Q: I edited the config by hand and now Claude won't start the server.**
JSON needs double backslashes in Windows paths (`C:\\Users\\...`). Easier: run `python configure_claude.py`,
which escapes paths correctly. It saves your previous file as `claude_desktop_config.json.bak`.

**Q: How do I reset the data?**
Run `python seed_db.py` again. It rebuilds the tables from scratch.

**Q: Can Claude change my data?**
Yes. `mcp-server-sqlite` includes `write_query` and `create_table` tools in addition to read tools.
Claude Desktop asks for your approval before each tool call, so review write actions before allowing them.
For anything you care about, point the server at a copy of the database.

**Q: How do I use my own database instead?**
Edit `DB_PATH` in `configure_claude.py` to point at your `.db` file, run it again, and restart Claude Desktop.

## Note on the server package

`mcp-server-sqlite` was originally one of Anthropic's reference MCP servers and has since been moved to the
archived servers repo. It still installs and works through `uvx`, which makes it fine for learning and
local projects, but it no longer receives active maintenance.
