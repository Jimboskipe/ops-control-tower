-- 04_kpis.sql
-- Time-to-close metrics. Mean AND median AND p90, because the mean alone lies on skewed data.

DROP TABLE IF EXISTS ranked;
CREATE TEMP TABLE ranked AS
SELECT complaint_type, borough, days_to_close,
       ROW_NUMBER() OVER (PARTITION BY complaint_type ORDER BY days_to_close) AS rn,
       COUNT(*)     OVER (PARTITION BY complaint_type)                         AS n
FROM mart_requests;

DROP TABLE IF EXISTS kpi_by_type;
CREATE TABLE kpi_by_type AS
SELECT complaint_type,
       MAX(n)                                                          AS requests,
       ROUND(AVG(days_to_close), 1)                                    AS mean_days,
       ROUND(AVG(CASE WHEN rn IN ((n + 1) / 2, (n + 2) / 2) THEN days_to_close END), 1) AS median_days,
       ROUND(MAX(CASE WHEN rn = (9 * n + 9) / 10 THEN days_to_close END), 1)            AS p90_days,
       ROUND(100.0 * AVG(days_to_close <= 1), 1)                       AS pct_within_1d,
       ROUND(100.0 * AVG(days_to_close <= 30), 1)                      AS pct_within_30d,
       ROUND(100.0 * AVG(days_to_close <= 90), 1)                      AS pct_within_90d
FROM ranked
GROUP BY complaint_type
ORDER BY requests DESC;

DROP TABLE IF EXISTS kpi_by_borough;
CREATE TABLE kpi_by_borough AS
SELECT borough, COUNT(*) AS requests,
       ROUND(AVG(days_to_close), 1) AS mean_days,
       ROUND(100.0 * AVG(days_to_close <= 30), 1) AS pct_within_30d
FROM mart_requests
WHERE borough IN (SELECT borough FROM dim_borough)
GROUP BY borough
ORDER BY requests DESC;

DROP TABLE IF EXISTS kpi_overall;
CREATE TABLE kpi_overall AS
WITH r AS (
  SELECT days_to_close,
         ROW_NUMBER() OVER (ORDER BY days_to_close) AS rn,
         COUNT(*) OVER () AS n
  FROM mart_requests
)
SELECT MAX(n)                                                         AS requests,
       ROUND(AVG(days_to_close), 1)                                   AS mean_days,
       ROUND(AVG(CASE WHEN rn IN ((n + 1) / 2, (n + 2) / 2) THEN days_to_close END), 1) AS median_days,
       ROUND(MAX(CASE WHEN rn = (9 * n + 9) / 10 THEN days_to_close END), 1)            AS p90_days,
       ROUND(100.0 * AVG(days_to_close <= 1), 1)                      AS pct_within_1d,
       ROUND(100.0 * AVG(days_to_close <= 30), 1)                     AS pct_within_30d,
       ROUND(100.0 * AVG(days_to_close <= 90), 1)                     AS pct_within_90d
FROM r;

-- Completeness reconciliation: every raw row must be accounted for exactly once.
DROP TABLE IF EXISTS reconciliation;
CREATE TABLE reconciliation AS
SELECT
    (SELECT COUNT(*) FROM raw_requests)                                         AS raw_rows,
    (SELECT COUNT(*) FROM mart_requests)                                        AS closed_rows,
    (SELECT COUNT(*) FROM mart_open_backlog)                                    AS open_rows,
    (SELECT COUNT(DISTINCT row_id) FROM exception_queue WHERE kind = 'REJECT')  AS rejected_rows,
    (SELECT COUNT(*) FROM raw_requests)
      - (SELECT COUNT(*) FROM mart_requests)
      - (SELECT COUNT(*) FROM mart_open_backlog)
      - (SELECT COUNT(DISTINCT row_id) FROM exception_queue WHERE kind = 'REJECT') AS unaccounted_rows;
