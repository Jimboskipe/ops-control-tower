-- 00_setup.sql
-- Business rules in one place. Snapshot date = the date the public data was pulled.

DROP TABLE IF EXISTS run_params;
CREATE TABLE run_params (as_of TEXT, aging_days REAL, long_tail_days REAL);
INSERT INTO run_params VALUES ('2026-11-24 00:00:00', 90, 365);

DROP TABLE IF EXISTS dim_borough;
CREATE TABLE dim_borough (borough TEXT PRIMARY KEY);
INSERT INTO dim_borough VALUES ('BROOKLYN'), ('QUEENS'), ('BRONX'), ('MANHATTAN'), ('STATEN ISLAND');
