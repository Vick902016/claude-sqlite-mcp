# SQL Assistant (desktop app)

A small Windows app for asking questions about the database without opening Claude Desktop.
Type a question in plain English; Claude writes the SQL, the app runs it and shows the results.

## Install

1. Copy `sql_assistant.pyw`, `sql_core.py`, `install_app.py` and `install_app.bat` into the project folder.
2. Double-click `install_app.bat`. It installs the `anthropic` Python package and creates a
   **SQL Assistant** shortcut on your desktop.
3. Open the app, click **Settings**, and paste your Anthropic API key.

The key is stored only on your computer, in `%APPDATA%\SQLAssistant\settings.json`, outside the project
folder so it can never be committed to Git. Alternatively, set an `ANTHROPIC_API_KEY` environment variable.

## Features

- **Ask Claude:** question in, SQL and results out, with a one-line explanation of the query.
- **Auto-fix:** if Claude's first query errors, the app sends the error back and runs the corrected query.
- **Your own SQL:** edit the SQL box and press **Run SQL** (or Ctrl+Enter). No API key needed for this.
- **Table browser:** see every table and column; double-click a table to preview its rows.
- **Export to CSV** and **Copy SQL**.
- **Open database…** works with any SQLite file, and remembers the last one you opened.

## Safety

The app opens databases in SQLite's read-only mode, so no query can change or delete data, even one
that Claude writes. Only one statement runs at a time, and results are capped at 1,000 rows.

## How it differs from the MCP setup

The MCP server lets Claude Desktop explore the database during a chat. This app calls the Claude API
directly: it sends the schema, a few sample rows, and your question, and gets SQL back. API usage is
billed per request through your Anthropic API account, separately from a Claude.ai subscription.
