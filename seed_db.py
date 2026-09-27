"""
seed_db.py - Creates local_store.db with sample customers, orders, and support tickets.
Safe to re-run: it drops and rebuilds the tables each time, so data never duplicates.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "local_store.db"

SCHEMA = """
DROP TABLE IF EXISTS support_tickets;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name   TEXT NOT NULL,
    last_name    TEXT NOT NULL,
    email        TEXT UNIQUE NOT NULL,
    signup_date  DATE,
    plan         TEXT CHECK (plan IN ('free', 'pro', 'enterprise'))
);

CREATE TABLE orders (
    order_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id  INTEGER NOT NULL,
    amount       REAL NOT NULL,
    order_date   DATE NOT NULL,
    status       TEXT CHECK (status IN ('completed', 'pending', 'refunded', 'cancelled')),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE support_tickets (
    ticket_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id  INTEGER NOT NULL,
    order_id     INTEGER,
    subject      TEXT NOT NULL,
    category     TEXT CHECK (category IN ('billing', 'technical', 'account', 'shipping')),
    priority     TEXT CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    status       TEXT CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    opened_at    DATETIME NOT NULL,
    resolved_at  DATETIME,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

CREATE INDEX idx_orders_customer   ON orders(customer_id);
CREATE INDEX idx_tickets_customer  ON support_tickets(customer_id);
CREATE INDEX idx_tickets_status    ON support_tickets(status);
"""

CUSTOMERS = [
    ("Marcus", "Vance",    "marcus@example.com", "2024-01-15", "pro"),
    ("Elena",  "Reyes",    "elena@example.com",  "2024-02-10", "enterprise"),
    ("Sarah",  "Connor",   "sarah@example.com",  "2024-03-01", "free"),
    ("David",  "Okafor",   "david@example.com",  "2024-03-22", "pro"),
    ("Priya",  "Nair",     "priya@example.com",  "2024-04-05", "enterprise"),
    ("Tom",    "Becker",   "tom@example.com",    "2024-05-18", "free"),   # never orders
    ("Aisha",  "Rahman",   "aisha@example.com",  "2024-06-02", "pro"),
    ("Liam",   "O'Brien",  "liam@example.com",   "2024-06-30", "free"),   # never orders
]

ORDERS = [
    (1, 149.99, "2024-03-01", "completed"),
    (1,  45.00, "2024-03-15", "completed"),
    (2, 299.50, "2024-03-20", "pending"),
    (2,  89.00, "2024-04-02", "completed"),
    (2, 1200.00,"2024-05-10", "completed"),
    (3,  19.99, "2024-04-11", "refunded"),
    (4, 349.00, "2024-04-25", "completed"),
    (4,  75.25, "2024-06-14", "cancelled"),
    (5, 2450.00,"2024-05-01", "completed"),
    (5, 510.00, "2024-06-20", "completed"),
    (7,  99.00, "2024-06-15", "completed"),
    (7, 129.00, "2024-07-01", "pending"),
]

TICKETS = [
    (1, 1,    "Charged twice for order",         "billing",   "high",   "resolved",    "2024-03-02 09:15", "2024-03-02 14:40"),
    (2, 3,    "Order stuck in pending",          "shipping",  "medium", "open",        "2024-03-25 11:00", None),
    (2, None, "SSO login failing for team",      "technical", "urgent", "in_progress", "2024-05-12 08:30", None),
    (3, 6,    "Refund not received",             "billing",   "high",   "resolved",    "2024-04-15 16:20", "2024-04-18 10:05"),
    (4, None, "API returns 500 on /export",      "technical", "high",   "resolved",    "2024-05-03 13:45", "2024-05-04 09:00"),
    (4, 8,    "Why was my order cancelled?",     "billing",   "low",    "closed",      "2024-06-15 10:10", "2024-06-15 12:30"),
    (5, None, "Need to add 20 more seats",       "account",   "medium", "resolved",    "2024-05-20 15:00", "2024-05-21 11:15"),
    (5, 10,   "Invoice missing PO number",       "billing",   "low",    "open",        "2024-06-22 09:00", None),
    (6, None, "Cannot reset password",           "account",   "medium", "resolved",    "2024-05-19 18:05", "2024-05-19 18:45"),
    (7, 12,   "Tracking number not working",     "shipping",  "medium", "in_progress", "2024-07-03 14:20", None),
]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA)
    conn.executemany(
        "INSERT INTO customers (first_name, last_name, email, signup_date, plan) VALUES (?, ?, ?, ?, ?)",
        CUSTOMERS)
    conn.executemany(
        "INSERT INTO orders (customer_id, amount, order_date, status) VALUES (?, ?, ?, ?)",
        ORDERS)
    conn.executemany(
        "INSERT INTO support_tickets (customer_id, order_id, subject, category, priority, status, opened_at, resolved_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        TICKETS)
    conn.commit()

    for table in ("customers", "orders", "support_tickets"):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:<16} {count} rows")
    conn.close()
    print(f"\nDatabase created at: {DB_PATH}")


if __name__ == "__main__":
    main()
