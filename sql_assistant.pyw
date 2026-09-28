"""
SQL Assistant - ask questions about a SQLite database in plain English.
Double-click to run (the .pyw extension opens it without a console window).
"""
import csv
import tkinter.font as tkfont
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import sql_core as core

# Palette
BG = "#F3F5F8"
PANEL = "#FFFFFF"
INK = "#1E2A36"
MUTED = "#667381"
LINE = "#D6DDE4"
ACCENT = "#1F5F8B"
ACCENT_DARK = "#174A6D"
CODE_BG = "#1E2A36"
CODE_FG = "#E6EDF3"
ERROR = "#B3261E"

FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI Semibold", 10)
FONT_TITLE = ("Segoe UI Semibold", 13)
FONT_CODE = ("Consolas", 11)

EXAMPLES = [
    "Top customers by completed order total",
    "Customers who never placed an order",
    "Average ticket resolution time in hours by category",
    "Open or in-progress tickets, most urgent first",
]


class SQLAssistant(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SQL Assistant")
        self.geometry("1150x740")
        self.minsize(900, 560)
        self.configure(bg=BG)

        self.settings = core.load_settings()
        self.db_path = Path(self.settings.get("db_path") or core.DEFAULT_DB)
        self.results = ([], [])
        self.jobs = queue.Queue()

        self._style()
        self._build()
        self.load_database(self.db_path, quiet=True)
        self.after(100, self._poll_jobs)

    # ---------- layout ----------
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=INK, font=FONT)
        s.configure("Panel.TFrame", background=PANEL)
        s.configure("TLabel", background=BG)
        s.configure("Panel.TLabel", background=PANEL)
        s.configure("Muted.TLabel", background=BG, foreground=MUTED)
        s.configure("PanelMuted.TLabel", background=PANEL, foreground=MUTED)
        s.configure("Title.TLabel", background=BG, font=FONT_TITLE)
        s.configure("Heading.TLabel", background=PANEL, font=FONT_BOLD)
        s.configure("Accent.TButton", background=ACCENT, foreground="white", font=FONT_BOLD,
                    borderwidth=0, padding=(14, 6))
        s.map("Accent.TButton", background=[("active", ACCENT_DARK), ("disabled", LINE)])
        s.configure("TButton", background=PANEL, bordercolor=LINE, padding=(10, 5))
        s.map("TButton", background=[("active", BG)])
        s.configure("Link.TButton", background=PANEL, foreground=ACCENT, borderwidth=0, padding=(4, 2))
        s.map("Link.TButton", background=[("active", PANEL)], foreground=[("active", ACCENT_DARK)])
        s.configure("Treeview", background=PANEL, fieldbackground=PANEL, bordercolor=LINE, rowheight=24)
        s.configure("Treeview.Heading", background=BG, font=FONT_BOLD, relief="flat")
        s.map("Treeview", background=[("selected", "#DCE8F2")], foreground=[("selected", INK)])
        s.configure("TEntry", padding=6, bordercolor=LINE)

    def _build(self):
        # Top bar
        top = ttk.Frame(self, padding=(16, 12, 16, 8))
        top.pack(fill="x")
        ttk.Label(top, text="SQL Assistant", style="Title.TLabel").pack(side="left")
        ttk.Button(top, text="Settings", command=self.open_settings).pack(side="right")
        ttk.Button(top, text="Open database…", command=self.choose_database).pack(side="right", padx=8)
        self.db_label = ttk.Label(top, text="", style="Muted.TLabel")
        self.db_label.pack(side="right", padx=8)

        self.status = ttk.Label(self, text="", style="Muted.TLabel", padding=(16, 0, 16, 10))
        self.status.pack(side="bottom", fill="x")

        body = ttk.PanedWindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # Left: tables
        left = ttk.Frame(body, style="Panel.TFrame", padding=10)
        ttk.Label(left, text="Tables", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(left, text="Double-click a table to preview it", style="PanelMuted.TLabel").pack(anchor="w", pady=(0, 6))
        self.schema_tree = ttk.Treeview(left, show="tree", selectmode="browse")
        self.schema_tree.column("#0", width=250)
        self.schema_tree.pack(fill="both", expand=True)
        self.schema_tree.bind("<Double-1>", self.preview_table)
        body.add(left, weight=1)

        # Right: ask, SQL, results
        right = ttk.Frame(body)
        body.add(right, weight=4)

        ask = ttk.Frame(right, style="Panel.TFrame", padding=12)
        ask.pack(fill="x", padx=(8, 0))
        ttk.Label(ask, text="Ask a question about your data", style="Heading.TLabel").pack(anchor="w")
        row = ttk.Frame(ask, style="Panel.TFrame")
        row.pack(fill="x", pady=(6, 4))
        self.question = ttk.Entry(row, font=("Segoe UI", 11))
        self.question.pack(side="left", fill="x", expand=True)
        self.question.bind("<Return>", lambda e: self.ask())
        self.ask_btn = ttk.Button(row, text="Ask Claude", style="Accent.TButton", command=self.ask)
        self.ask_btn.pack(side="left", padx=(8, 0))
        ex = ttk.Frame(ask, style="Panel.TFrame")
        ex.pack(fill="x")
        ttk.Label(ex, text="Try:", style="PanelMuted.TLabel").grid(row=0, column=0, sticky="w")
        for i, q in enumerate(EXAMPLES):
            ttk.Button(ex, text=q, style="Link.TButton",
                       command=lambda q=q: self._use_example(q)).grid(row=i // 2, column=1 + i % 2, sticky="w")

        # SQL panel
        sql_frame = ttk.Frame(right, style="Panel.TFrame", padding=12)
        sql_frame.pack(fill="x", padx=(8, 0), pady=8)
        head = ttk.Frame(sql_frame, style="Panel.TFrame")
        head.pack(fill="x")
        ttk.Label(head, text="SQL", style="Heading.TLabel").pack(side="left")
        ttk.Button(head, text="Copy SQL", command=self.copy_sql).pack(side="right")
        self.run_btn = ttk.Button(head, text="Run SQL", style="Accent.TButton", command=self.run_sql)
        self.run_btn.pack(side="right", padx=8)
        self.explanation = ttk.Label(sql_frame, text="Ask a question above, or write your own SQL here and press Run SQL (Ctrl+Enter).",
                                     style="PanelMuted.TLabel", wraplength=800, justify="left")
        self.explanation.pack(anchor="w", pady=(4, 6), fill="x")
        self.sql_text = tk.Text(sql_frame, height=7, font=FONT_CODE, bg=CODE_BG, fg=CODE_FG,
                                insertbackground=CODE_FG, relief="flat", padx=10, pady=8, wrap="word",
                                selectbackground=ACCENT)
        self.sql_text.pack(fill="x")
        self.sql_text.bind("<Control-Return>", lambda e: (self.run_sql(), "break")[1])
        sql_frame.bind("<Configure>", lambda e: self.explanation.configure(wraplength=e.width - 30))

        # Results
        res = ttk.Frame(right, style="Panel.TFrame", padding=12)
        res.pack(fill="both", expand=True, padx=(8, 0))
        rhead = ttk.Frame(res, style="Panel.TFrame")
        rhead.pack(fill="x", pady=(0, 6))
        ttk.Label(rhead, text="Results", style="Heading.TLabel").pack(side="left")
        ttk.Button(rhead, text="Export to CSV", command=self.export_csv).pack(side="right")
        grid = ttk.Frame(res, style="Panel.TFrame")
        grid.pack(fill="both", expand=True)
        self.result_tree = ttk.Treeview(grid, show="headings")
        ys = ttk.Scrollbar(grid, orient="vertical", command=self.result_tree.yview)
        xs = ttk.Scrollbar(grid, orient="horizontal", command=self.result_tree.xview)
        self.result_tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.result_tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        grid.rowconfigure(0, weight=1)
        grid.columnconfigure(0, weight=1)

    # ---------- helpers ----------
    def set_status(self, text, error=False):
        self.status.configure(text=text, foreground=ERROR if error else MUTED)

    def set_sql(self, sql):
        self.sql_text.delete("1.0", "end")
        self.sql_text.insert("1.0", sql)

    def get_sql(self):
        return self.sql_text.get("1.0", "end").strip()

    def _use_example(self, q):
        self.question.delete(0, "end")
        self.question.insert(0, q)
        self.ask()

    def _busy(self, busy):
        state = "disabled" if busy else "normal"
        self.ask_btn.configure(state=state)
        self.run_btn.configure(state=state)
        self.configure(cursor="watch" if busy else "")

    # ---------- database ----------
    def load_database(self, path, quiet=False):
        try:
            schema = core.get_schema(path)
        except Exception as e:
            self.db_label.configure(text="No database loaded")
            msg = f"{e}. Run 'python seed_db.py' in the project folder, or use Open database."
            self.set_status(msg, error=True)
            if not quiet:
                messagebox.showerror("Couldn't open database", msg)
            return
        self.db_path = Path(path)
        self.settings["db_path"] = str(self.db_path)
        core.save_settings(self.settings)
        self.db_label.configure(text=self.db_path.name)
        self.schema_tree.delete(*self.schema_tree.get_children())
        for table, cols in schema.items():
            node = self.schema_tree.insert("", "end", iid=table, text=f"{table}  ({len(cols)} columns)", open=False)
            for name, ctype, pk in cols:
                label = f"{name}   {ctype.lower()}{'   (key)' if pk else ''}"
                self.schema_tree.insert(node, "end", text=label)
        self.set_status(f"Opened {self.db_path} (read-only). {len(schema)} tables.")

    def choose_database(self):
        path = filedialog.askopenfilename(
            title="Open SQLite database",
            filetypes=[("SQLite databases", "*.db *.sqlite *.sqlite3"), ("All files", "*.*")])
        if path:
            self.load_database(path)

    def preview_table(self, _event):
        item = self.schema_tree.focus()
        table = item if self.schema_tree.parent(item) == "" else self.schema_tree.parent(item)
        if table:
            self.set_sql(f'SELECT *\nFROM "{table}"\nLIMIT 100;')
            self.explanation.configure(text=f"Preview of the first 100 rows of {table}.")
            self.run_sql()

    # ---------- actions ----------
    def open_settings(self):
        current = core.get_api_key(self.settings)
        hint = "A key is saved. Paste a new one to replace it." if current else "Paste your Anthropic API key (starts with sk-ant-)."
        key = simpledialog.askstring("Settings", f"{hint}\n\nIt's stored only on this computer, in:\n{core.SETTINGS_PATH}",
                                     parent=self, show="*")
        if key:
            self.settings["api_key"] = key.strip()
            core.save_settings(self.settings)
            self.set_status("API key saved.")

    def ask(self):
        question = self.question.get().strip()
        if not question:
            self.set_status("Type a question first.", error=True)
            return
        self._busy(True)
        self.set_status("Asking Claude…")
        api_key = core.get_api_key(self.settings)
        threading.Thread(target=self._ask_worker, args=(api_key, question), daemon=True).start()

    def _ask_worker(self, api_key, question):
        """Runs in the background: get SQL, run it, and retry once with the error if it fails."""
        try:
            answer = core.ask_claude(api_key, self.db_path, question)
            if not answer["sql"]:
                self.jobs.put(("no_sql", answer))
                return
            try:
                result = core.run_query(self.db_path, answer["sql"])
            except Exception as first_error:
                answer = core.ask_claude(api_key, self.db_path, question, answer["sql"], str(first_error))
                result = core.run_query(self.db_path, answer["sql"])
                answer["explanation"] += " (Fixed automatically after the first attempt returned an error.)"
            self.jobs.put(("answer", (answer, result)))
        except Exception as e:
            self.jobs.put(("error", e))

    def _poll_jobs(self):
        try:
            while True:
                kind, payload = self.jobs.get_nowait()
                self._busy(False)
                if kind == "answer":
                    answer, result = payload
                    self.set_sql(answer["sql"])
                    self.explanation.configure(text=answer["explanation"])
                    self.show_results(*result)
                elif kind == "no_sql":
                    self.explanation.configure(text=payload["explanation"])
                    self.set_status("Claude couldn't answer that from this database.", error=True)
                else:
                    self.set_status(str(payload), error=True)
        except queue.Empty:
            pass
        self.after(100, self._poll_jobs)

    def run_sql(self):
        try:
            result = core.run_query(self.db_path, self.get_sql())
        except Exception as e:
            self.set_status(f"Query failed: {e}", error=True)
            return
        self.show_results(*result)

    def show_results(self, columns, rows, truncated, seconds):
        tree = self.result_tree
        tree.delete(*tree.get_children())
        tree["columns"] = columns
        body_font, head_font = tkfont.Font(font=FONT), tkfont.Font(font=FONT_BOLD)
        for i, c in enumerate(columns):
            widest = max([head_font.measure(str(c))] + [body_font.measure(str(r[i])) for r in rows[:100]])
            width = max(80, min(360, widest + 28))
            tree.heading(c, text=c)
            tree.column(c, width=width, anchor="w", stretch=False)
        for r in rows:
            tree.insert("", "end", values=["" if v is None else v for v in r])
        self.results = (columns, rows)
        note = f" Showing the first {core.MAX_ROWS}." if truncated else ""
        self.set_status(f"{len(rows)} row{'s' if len(rows) != 1 else ''} in {seconds:.2f} s.{note}")

    def copy_sql(self):
        self.clipboard_clear()
        self.clipboard_append(self.get_sql())
        self.set_status("SQL copied to clipboard.")

    def export_csv(self):
        columns, rows = self.results
        if not columns:
            self.set_status("Run a query first, then export.", error=True)
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")],
                                            initialfile="results.csv")
        if path:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(columns)
                w.writerows(rows)
            self.set_status(f"Exported {len(rows)} rows to {path}")


if __name__ == "__main__":
    SQLAssistant().mainloop()
