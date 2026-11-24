"""Ops Control Tower pipeline: raw CSV -> staging -> exception queue -> mart -> KPIs.

Run:  python pipeline.py
Standard library only (sqlite3), so it runs anywhere.
"""
import csv
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "data", "raw_311_dob_2024-09.csv")
DB = os.path.join(ROOT, "output", "ops.db")
SQL_FILES = ["00_setup.sql", "01_staging.sql", "02_exception_queue.sql", "03_mart.sql", "04_kpis.sql"]
RAW_COLS = ["unique_key", "created_date", "closed_date", "agency",
            "complaint_type", "descriptor", "status", "borough"]


def load_raw(con, path=RAW):
    con.execute("DROP TABLE IF EXISTS raw_requests")
    con.execute("CREATE TABLE raw_requests (%s)" % ", ".join(c + " TEXT" for c in RAW_COLS))
    with open(path, newline="", encoding="utf-8") as f:
        rows = [tuple(r.get(c, "") for c in RAW_COLS) for r in csv.DictReader(f)]
    con.executemany("INSERT INTO raw_requests VALUES (%s)" % ",".join("?" * len(RAW_COLS)), rows)
    return len(rows)


def run(db_path=DB, raw_path=RAW):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)
    con = sqlite3.connect(db_path)
    n = load_raw(con, raw_path)
    for name in SQL_FILES:
        with open(os.path.join(ROOT, "sql", name), encoding="utf-8") as f:
            con.executescript(f.read())
    con.commit()
    return con, n


def main():
    if not os.path.exists(RAW):
        sys.exit("Missing data file. Run: python data/fetch_data.py")
    con, n = run()
    rec = con.execute("SELECT * FROM reconciliation").fetchone()
    print(f"loaded {n} raw rows")
    print("reconciliation: raw=%d closed=%d open=%d rejected=%d unaccounted=%d" % rec)
    print("\nexception queue:")
    for t, k, c in con.execute(
            "SELECT exception_type, kind, COUNT(*) FROM exception_queue GROUP BY 1,2 ORDER BY 3 DESC"):
        print(f"  {t:26s} {k:6s} {c}")
    print("\noverall (requests, mean d, median d, p90 d, <=1d %, <=30d %, <=90d %):")
    print("  ", con.execute("SELECT * FROM kpi_overall").fetchone())
    if rec[4] != 0:
        sys.exit("RECONCILIATION FAILED: unaccounted rows != 0")
    print("\nOK: every raw row is accounted for.")


if __name__ == "__main__":
    main()
