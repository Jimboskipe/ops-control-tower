-- 02_exception_queue.sql
-- REJECT rows are kept out of timing KPIs and need human review.
-- ALERT rows are valid records that deserve attention but stay in the mart.

DROP TABLE IF EXISTS exception_queue;
CREATE TABLE exception_queue AS

SELECT row_id, unique_key, 'DUPLICATE_KEY' AS exception_type, 'REJECT' AS kind, 'HIGH' AS severity,
       'unique_key appears more than once; later copy rejected' AS detail
FROM stg_requests WHERE dup_rank > 1

UNION ALL
SELECT row_id, unique_key, 'CLOSED_BEFORE_CREATED', 'REJECT', 'HIGH',
       'closed_at is earlier than created_at'
FROM stg_requests
WHERE dup_rank = 1 AND closed_at IS NOT NULL AND closed_at < created_at

UNION ALL
SELECT row_id, unique_key, 'CLOSED_MISSING_DATE', 'REJECT', 'HIGH',
       'status = closed but closed_at is blank'
FROM stg_requests
WHERE dup_rank = 1 AND status = 'closed' AND closed_at IS NULL

UNION ALL
SELECT row_id, unique_key, 'STATUS_DATE_MISMATCH', 'REJECT', 'MEDIUM',
       'status = ' || status || ' but a closed_at date exists; cannot tell which is right'
FROM stg_requests
WHERE dup_rank = 1 AND status <> 'closed' AND closed_at IS NOT NULL

UNION ALL
SELECT row_id, unique_key, 'UNSPECIFIED_BOROUGH', 'ALERT', 'LOW',
       'borough = ' || COALESCE(borough, '(blank)') || '; record kept, excluded from borough rollups'
FROM stg_requests
WHERE dup_rank = 1 AND (borough IS NULL OR borough NOT IN (SELECT borough FROM dim_borough))

UNION ALL
SELECT s.row_id, s.unique_key, 'LONG_TAIL_CLOSURE', 'ALERT', 'MEDIUM',
       'took ' || ROUND(julianday(s.closed_at) - julianday(s.created_at), 0) || ' days to close; inflates the mean'
FROM stg_requests s CROSS JOIN run_params p
WHERE s.dup_rank = 1 AND s.status = 'closed' AND s.closed_at >= s.created_at
  AND julianday(s.closed_at) - julianday(s.created_at) > p.long_tail_days

UNION ALL
SELECT s.row_id, s.unique_key, 'OPEN_AGING', 'ALERT', 'HIGH',
       'still ' || s.status || ' after ' || ROUND(julianday(p.as_of) - julianday(s.created_at), 0) || ' days'
FROM stg_requests s CROSS JOIN run_params p
WHERE s.dup_rank = 1 AND s.status IN ('open', 'assigned') AND s.closed_at IS NULL
  AND julianday(p.as_of) - julianday(s.created_at) > p.aging_days;
