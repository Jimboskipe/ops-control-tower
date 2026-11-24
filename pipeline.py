"""Ops Control Tower pipeline: raw CSV -> staging -> exception queue -> mart -> KPIs.

Run:  python pipeline.py
Uses only the Python standard library (sqlite3), so it runs anywhere.
"""
import csv
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "data", "raw_tickets.csv")
DB = os.path.join(ROOT, "output", "ops.db")
SQL_FILES = ["00_setup.sql", "01_staging.sql", "02_exception_queue.sql", "03_mart.sql", "04_kpis.sql"]
RAW_COLS = ["ticket_id", "created_at", "acknowledged_at", "resolved_at",
            "priority", "category", "status", "assignee"]


def load_raw(con):
    con.execute("DROP TABLE IF EXISTS raw_tickets")
    con.execute("CREATE TABLE raw_tickets (%s)" % ", ".join(c + " TEXT" for c in RAW_COLS))
    with open(RAW, newline="", encoding="utf-8") as f:
        rows = [tuple(r[c] for c in RAW_COLS) for r in csv.DictReader(f)]
    con.executemany("INSERT INTO raw_tickets VALUES (%s)" % ",".join("?" * len(RAW_COLS)), rows)
    return len(rows)


def run(db_path=DB):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)
    con = sqlite3.connect(db_path)
    n = load_raw(con)
    for name in SQL_FILES:
        with open(os.path.join(ROOT, "sql", name), encoding="utf-8") as f:
            con.executescript(f.read())
    con.commit()
    return con, n


def main():
    if not os.path.exists(RAW):
        sys.exit("Missing data/raw_tickets.csv. Run: python data/generate_mock_data.py")
    con, n = run()
    rec = con.execute("SELECT * FROM reconciliation").fetchone()
    print(f"loaded {n} raw rows")
    print("reconciliation: raw=%d mart=%d open=%d rejected=%d unaccounted=%d" % rec)
    print("\nexception queue summary:")
    for t, k, c in con.execute(
            "SELECT exception_type, kind, COUNT(*) FROM exception_queue GROUP BY 1,2 ORDER BY 3 DESC"):
        print(f"  {t:30s} {k:6s} {c}")
    print("\nSLA by priority (priority, tickets, ack%, resolve%, MTTR h, target h):")
    for r in con.execute("SELECT * FROM kpi_sla_by_priority"):
        print("  ", r)
    if rec[4] != 0:
        sys.exit("RECONCILIATION FAILED: unaccounted rows != 0")
    print("\nOK: every raw row is accounted for.")


if __name__ == "__main__":
    main()
