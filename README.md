# Ops Control Tower

**Every ticket accounted for. Every bad row explained. Nothing gets dropped without a reason.**

I run a lot of jobs by one rule: measure twice, cut once. This is that rule applied to operations data. It takes a messy ticket feed, cleans what can be cleaned, kicks out what can't with a plain-English reason, and reports SLA and MTTR only from rows it trusts. Then it proves every raw row ended up somewhere.

All data here is **synthetic**. No real company, customer, or employer data.

## What it does

```
raw_tickets.csv  ->  staging  ->  exception queue  ->  mart  ->  KPIs + dashboard
```

| Stage | File | What happens |
|---|---|---|
| Setup | `sql/00_setup.sql` | SLA targets by priority, valid categories, snapshot time |
| Staging | `sql/01_staging.sql` | Trim, uppercase, type, rank duplicates. Nothing dropped |
| Exception queue | `sql/02_exception_queue.sql` | Six rules, each with severity and a readable detail |
| Mart | `sql/03_mart.sql` | Clean resolved tickets and open backlog only |
| KPIs | `sql/04_kpis.sql` | SLA attainment, MTTR (overall, weekly, by category), reconciliation |

### Exception rules

| Rule | Kind | Why it matters |
|---|---|---|
| `DUPLICATE_TICKET_ID` | REJECT | Double-counting inflates volume |
| `MISSING_OR_INVALID_PRIORITY` | REJECT | Can't judge SLA without a priority |
| `UNKNOWN_CATEGORY` | REJECT | Breaks category reporting |
| `TIME_INVERTED` | REJECT | Resolved before created. Negative MTTR poisons the average |
| `MISSING_RESOLVED_AT` | REJECT | Marked done but no finish time |
| `OPEN_SLA_BREACH` | ALERT | Valid ticket, but late. Someone needs to act now |

Messy case and spacing (`" p2 "`, `RESOLVED`) is cleaned, not rejected. Rejecting recoverable data is its own kind of waste.

### Reconciliation

The pipeline fails loudly if any raw row is unaccounted for:

```
raw rows = clean resolved + open backlog + rejected     (unaccounted must be 0)
```

On the included data: `612 = 544 + 13 + 55`.

## Run it

Python 3.9 or newer. Standard library only, nothing to install.

```
python data/generate_mock_data.py     # build synthetic data with injected defects
python pipeline.py                    # run the pipeline, print summary
python dashboard.py                   # build output/dashboard.html
python -m unittest discover -s tests  # 7 tests
```

## Tests

The test suite checks that every raw row is accounted for, every injected defect type is caught, no duplicates or negative times reach the mart, and messy-case rows are cleaned rather than rejected.

## Runbook

When something breaks or an alert fires, see [RUNBOOK.md](RUNBOOK.md).

## Built with

SQL (SQLite dialect) and Python. Window functions, CTE-style staging, joins to dimension tables, reconciliation checks.
