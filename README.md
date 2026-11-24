# Ops Control Tower — Municipal Building & Construction Inspection Pipeline

**Every ticket accounted for. Every bad row explained. Nothing gets dropped without a reason.**

On a jobsite, you measure twice and cut once. This repository applies that exact standard to operations and compliance data. It ingests **5,000 real NYC 311 Department of Buildings (DOB) service and inspection requests** (September 2024 public intake from NYC Open Data), normalizes the feed into staging, routes status-vs-timestamp defects into an actionable exception queue, and computes SLA and time-to-close metrics (`median`, `mean`, `P90`) strictly from verified records—proving at the end that every single raw row is accounted for (`0` unaccounted rows).

> **Proprietary Trading & IP Notice:** No proprietary trading strategies, live market execution code, or personal trading data have been placed in this repository. All personal and algorithmic trading systems are strictly proprietary information and are intentionally excluded from public repositories.

## What It Does

```
raw_311_dob_2024-09.csv (5,000 real NYC DOB rows)  ->  staging  ->  exception queue  ->  mart  ->  KPIs + HTML dashboard
```

| Stage | File | What happens |
|---|---|---|
| Setup | `sql/00_setup.sql` | Snapshot parameters (`90d` aging threshold, `365d` long-tail threshold) and valid borough dimension |
| Staging | `sql/01_staging.sql` | Trim, normalize timestamps, standardize case, and rank duplicates via `ROW_NUMBER()`. Zero rows dropped |
| Exception queue | `sql/02_exception_queue.sql` | 7 data-quality and operational alert rules with severity and plain-English diagnostics |
| Mart | `sql/03_mart.sql` | Trusted closed requests (`mart_requests`) and verified open backlog (`mart_open_backlog`) |
| KPIs | `sql/04_kpis.sql` | Mean, median, and P90 days-to-close (because mean alone lies on skewed data), plus row-level completeness reconciliation |

### Exception & Alert Rules

| Rule | Kind | Real-Data Count | Why it matters |
|---|---|---|---|
| `STATUS_DATE_MISMATCH` | REJECT | **73** | Marked `Open` or `Assigned` in the city feed, yet carries a `closed_date` timestamp. Excluded from closed-ticket KPIs until reconciled |
| `DUPLICATE_KEY` | REJECT | 0 (tested in unit suite) | Prevents double-counting volume |
| `CLOSED_BEFORE_CREATED` | REJECT | 0 (tested in unit suite) | Prevents negative durations from poisoning MTTR |
| `CLOSED_MISSING_DATE` | REJECT | 0 (tested in unit suite) | Marked `Closed` without a closure timestamp |
| `LONG_TAIL_CLOSURE` | ALERT | **235** | Valid closed requests taking >365 days (`median = 18.4d` vs `mean = 76.8d`) |
| `UNSPECIFIED_BOROUGH` | ALERT | **2** | Missing valid borough; kept in overall KPIs, flagged for geo rollups |
| `OPEN_AGING` | ALERT | 0 (tested in unit suite) | Open requests aging past threshold |

### Completeness Reconciliation

The pipeline fails loudly if any raw row is unaccounted for:

```
raw rows (5,000) = clean closed (4,927) + open backlog (0) + rejected exceptions (73)   ->   unaccounted = 0
```

## Run It Locally

Python 3.9+ standard library only (`sqlite3`, `csv`, `unittest`). Nothing to install.

```bash
python pipeline.py                    # run staging -> exception queue -> mart -> KPIs
python dashboard.py                   # generate output/dashboard.html
python -m unittest discover -s tests  # run 8 real-data + rule-fixture unit tests
python data/fetch_data.py             # optional: re-pull fresh rows from NYC Open Data API
```

## Runbook

For on-call troubleshooting when reconciliation fails or an exception rule spikes, see [RUNBOOK.md](RUNBOOK.md).
