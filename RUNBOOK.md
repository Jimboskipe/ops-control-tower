# Runbook

Plain steps for the person on call. If you only read one line: **check `reconciliation` first.**

## 1. Pipeline failed with "RECONCILIATION FAILED"

`unaccounted_rows` is not 0, meaning raw rows went missing between stages.

1. Run `python pipeline.py` and read the counts.
2. Open `output/ops.db`: `SELECT * FROM reconciliation;`
3. Find the gap:
   - `SELECT COUNT(*) FROM raw_tickets;` vs `SELECT COUNT(*) FROM stg_tickets;` Staging must match raw.
   - If staging is short, a JOIN dropped rows. Check `01_staging.sql`.
   - If mart is short, a new status value is not `open`, `resolved` or `closed`. Check `SELECT DISTINCT status FROM stg_tickets;`
4. Fix the rule or add the new status. Re-run. Do not hand-edit the database.

## 2. Exception queue spiked

1. `SELECT exception_type, COUNT(*) FROM exception_queue WHERE kind='REJECT' GROUP BY 1 ORDER BY 2 DESC;`
2. Match the top type below.

| Spike in | Likely cause | Action |
|---|---|---|
| `DUPLICATE_TICKET_ID` | Source system re-sent a batch | Ask source owner to dedupe. Keep earliest copy, which the pipeline already does |
| `MISSING_OR_INVALID_PRIORITY` | New priority label (e.g. `P0`) | Confirm with ops lead. If real, add to `dim_priority_sla` with targets |
| `UNKNOWN_CATEGORY` | New category | Confirm. If real, add to `dim_category` |
| `TIME_INVERTED` | Clock or timezone bug in source | Spot-check 5 rows. Raise with source owner. Do not "fix" timestamps here |
| `MISSING_RESOLVED_AT` | Tickets closed without a timestamp | Send list to the team that closes tickets |

## 3. SLA alert (`OPEN_SLA_BREACH`)

1. List the worst:
   `SELECT ticket_id, priority, age_hours, resolve_target_hours FROM mart_open_backlog WHERE age_hours > resolve_target_hours ORDER BY age_hours DESC;`
2. P1 and P2 first. Assign a human, post in the ops channel, note the ticket IDs.
3. Re-run after the shift to confirm they cleared.

## 4. MTTR looks wrong

1. Is `mart_tickets` row count reasonable against the week before?
2. `SELECT MIN(resolve_hours), MAX(resolve_hours) FROM mart_tickets;` A negative minimum means a `TIME_INVERTED` rule gap.
3. One huge outlier? Check that ticket in `stg_tickets` before touching any rule.

## 5. Changing SLA targets

Edit the numbers in `sql/00_setup.sql`, re-run, and note the change and the date in the commit message so history stays honest.

## Ground rules

- Never delete a raw row. Reject it with a reason.
- Never silently fix data. Clean what is obviously formatting, reject what is genuinely wrong, and say which.
- If the numbers do not reconcile, nothing ships.
