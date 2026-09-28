"""
sql_core.py - Non-GUI logic for SQL Assistant: settings, schema, read-only queries, Claude API.
"""
import json
import os
import sqlite3
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DEFAULT_DB = APP_DIR / "local_store.db"
# Settings live outside the project folder so the API key never ends up in Git.
SETTINGS_PATH = Path(os.environ.get("APPDATA", Path.home())) / "SQLAssistant" / "settings.json"
MODEL = "claude-sonnet-5"
MAX_ROWS = 1000


# ---------- settings ----------
def load_settings() -> dict:
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_settings(settings: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def get_api_key(settings: dict) -> str:
    return os.environ.get("ANTHROPIC_API_KEY") or settings.get("api_key", "")


# ---------- database ----------
def connect_readonly(db_path) -> sqlite3.Connection:
    """Open the database in read-only mode, so nothing can modify it."""
    path = Path(db_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")
    return sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)


def get_schema(db_path) -> dict:
    """Return {table_name: [(column, type, is_primary_key), ...]}."""
    with connect_readonly(db_path) as conn:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {t: [(c[1], c[2] or "", bool(c[5])) for c in conn.execute(f'PRAGMA table_info("{t}")')]
                for t in tables}


def schema_for_prompt(db_path, sample_rows: int = 3) -> str:
    """CREATE statements plus a few sample rows per table, so Claude sees real values."""
    parts = []
    with connect_readonly(db_path) as conn:
        for name, sql in conn.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            parts.append(sql.strip() + ";")
            cur = conn.execute(f'SELECT * FROM "{name}" LIMIT {sample_rows}')
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            if rows:
                parts.append(f"-- sample rows from {name} ({', '.join(cols)}):")
                parts.extend(f"--   {r}" for r in rows)
            parts.append("")
    return "\n".join(parts)


def run_query(db_path, sql: str):
    """Run one read-only statement. Returns (columns, rows, truncated, seconds)."""
    sql = sql.strip().rstrip(";").strip()
    if not sql:
        raise ValueError("There's no SQL to run.")
    start = time.perf_counter()
    with connect_readonly(db_path) as conn:
        try:
            cur = conn.execute(sql)
        except sqlite3.OperationalError as e:
            if "readonly" in str(e):
                raise PermissionError("This app is read-only. It can look at data but not change it.") from e
            raise
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchmany(MAX_ROWS + 1)
    truncated = len(rows) > MAX_ROWS
    return columns, rows[:MAX_ROWS], truncated, time.perf_counter() - start


# ---------- Claude ----------
SYSTEM_PROMPT = """You translate questions into SQLite queries.
You are given the database schema and sample rows. Write exactly one read-only SELECT (or WITH ... SELECT)
statement that answers the question. Use only tables and columns that exist. Prefer readable column aliases.
Add LIMIT 100 unless the question clearly needs every row.

Respond with ONLY a JSON object, no markdown fences, in this shape:
{"sql": "<the query>", "explanation": "<one or two plain-English sentences on what the query does>"}

If the question can't be answered from this schema, respond with:
{"sql": "", "explanation": "<why not, and what data would be needed>"}"""


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def ask_claude(api_key: str, db_path, question: str, failed_sql: str = "", error: str = "") -> dict:
    """Ask Claude for SQL. Pass failed_sql/error to have it fix a query that didn't run."""
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("The 'anthropic' package isn't installed. Run install_app.bat, then reopen the app.")
    if not api_key:
        raise RuntimeError("Add your Anthropic API key in Settings to ask questions.")

    content = f"Database schema:\n{schema_for_prompt(db_path)}\n\nQuestion: {question}"
    if failed_sql:
        content += f"\n\nYour previous query:\n{failed_sql}\nfailed with this error:\n{error}\nReturn a corrected query."

    client = anthropic.Anthropic(api_key=api_key)
    try:
        msg = client.messages.create(
            model=MODEL, max_tokens=1024, system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}])
    except anthropic.AuthenticationError:
        raise RuntimeError("Your API key was rejected. Check it in Settings.")
    except anthropic.APIConnectionError:
        raise RuntimeError("Couldn't reach the Claude API. Check your internet connection.")
    except anthropic.APIStatusError as e:
        raise RuntimeError(f"The Claude API returned an error ({e.status_code}): {e.message}")

    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    try:
        data = _parse_json(text)
    except (ValueError, json.JSONDecodeError):
        raise RuntimeError("Claude's reply wasn't in the expected format. Try rephrasing the question.")
    return {"sql": data.get("sql", "").strip(), "explanation": data.get("explanation", "").strip()}
