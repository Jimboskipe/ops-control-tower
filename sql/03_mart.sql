-- 03_mart.sql
-- Trusted closed requests and trusted open backlog. REJECT rows are excluded from both.

DROP TABLE IF EXISTS mart_requests;
CREATE TABLE mart_requests AS
SELECT s.row_id, s.unique_key, s.complaint_type, s.descriptor, s.borough, s.created_at, s.closed_at,
       ROUND(julianday(s.closed_at) - julianday(s.created_at), 3) AS days_to_close,
       STRFTIME('%Y-W%W', s.created_at) AS created_week
FROM stg_requests s
WHERE s.status = 'closed' AND s.closed_at IS NOT NULL
  AND s.row_id NOT IN (SELECT row_id FROM exception_queue WHERE kind = 'REJECT');

DROP TABLE IF EXISTS mart_open_backlog;
CREATE TABLE mart_open_backlog AS
SELECT s.row_id, s.unique_key, s.complaint_type, s.descriptor, s.borough, s.status, s.created_at,
       ROUND(julianday(p.as_of) - julianday(s.created_at), 1) AS age_days
FROM stg_requests s CROSS JOIN run_params p
WHERE s.status IN ('open', 'assigned') AND s.closed_at IS NULL
  AND s.row_id NOT IN (SELECT row_id FROM exception_queue WHERE kind = 'REJECT');
