# Runbook — Ops Control Tower

Plain steps for the operator on call. First rule: **check `reconciliation` before touching anything else.**

## 1. Pipeline fails with `RECONCILIATION FAILED`

`unaccounted_rows` is not `0`, meaning raw rows went missing between `raw_requests` and the final tables.

1. Run `python pipeline.py` and inspect the reconciliation line.
2. Query `output/ops.db`:
   ```sql
   SELECT * FROM reconciliation;
   SELECT status, COUNT(*) FROM stg_requests GROUP BY 1;
   ```
3. If a new status value appeared in the source feed (outside `closed`, `open`, `assigned`), update `02_exception_queue.sql` and `03_mart.sql` so every status is explicitly routed. Never delete raw rows by hand.

## 2. Exception queue spikes

Query the breakdown:
```sql
SELECT exception_type, kind, severity, COUNT(*)
FROM exception_queue
GROUP BY 1, 2, 3
ORDER BY 4 DESC;
```

| Rule | Cause | Action |
|---|---|---|
| `STATUS_DATE_MISMATCH` | Source ticket has `status IN ('open','assigned')` but a populated `closed_date` (73 rows in the Sep 2024 NYC DOB feed) | Export the affected `unique_key` list and flag for upstream source reconciliation. Do not guess whether the status or the timestamp is right |
| `DUPLICATE_KEY` | Upstream batch re-sent existing keys | Pipeline automatically retains `dup_rank = 1` and rejects later copies |
| `CLOSED_BEFORE_CREATED` | Timezone shift or backdated closure timestamp | Reject from timing KPIs and report `unique_key` list to source owner |
| `CLOSED_MISSING_DATE` | Ticket closed without a timestamp | Route to ticketing admin team |
| `LONG_TAIL_CLOSURE` | Multi-year inspection backlogs closing in bulk | Always report **median** and **P90** alongside the mean so bulk backlog sweeps do not distort weekly ops reviews |

## 3. Ground Rules

- Never delete a raw row. Route bad rows to `exception_queue` with a specific rule code.
- Always report `median_days` and `p90_days` next to `mean_days`.
- If `unaccounted_rows != 0`, nothing ships.
