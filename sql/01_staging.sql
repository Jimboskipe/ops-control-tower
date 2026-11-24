-- 01_staging.sql
-- Raw rows -> typed, trimmed, normalised. Nothing is dropped. Every raw row keeps a row_id.

DROP TABLE IF EXISTS stg_requests;
CREATE TABLE stg_requests AS
SELECT
    r.rowid                                             AS row_id,
    TRIM(r.unique_key)                                  AS unique_key,
    REPLACE(SUBSTR(NULLIF(TRIM(r.created_date), ''), 1, 19), 'T', ' ') AS created_at,
    REPLACE(SUBSTR(NULLIF(TRIM(r.closed_date), ''), 1, 19), 'T', ' ')  AS closed_at,
    TRIM(r.agency)                                      AS agency,
    TRIM(r.complaint_type)                              AS complaint_type,
    TRIM(r.descriptor)                                  AS descriptor,
    LOWER(TRIM(r.status))                               AS status,
    UPPER(TRIM(r.borough))                              AS borough,
    ROW_NUMBER() OVER (PARTITION BY TRIM(r.unique_key) ORDER BY r.rowid) AS dup_rank
FROM raw_requests r;
