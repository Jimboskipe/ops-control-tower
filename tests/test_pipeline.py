"""Tests: every row accounted for, every rule fires when it should.

Real-data tests run against the included public dataset. Rule tests use a tiny
hand-built fixture so each rule is proven independently of what the real data happens to contain.

Run:  python -m unittest discover -s tests
"""
import csv
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import pipeline  # noqa: E402

HEAD = ["unique_key", "created_date", "closed_date", "agency", "complaint_type", "descriptor", "status", "borough"]


def run_fixture(rows):
    tmp = tempfile.mkdtemp()
    p = os.path.join(tmp, "f.csv")
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEAD)
        w.writerows(rows)
    return pipeline.run(os.path.join(tmp, "t.db"), p)[0]


class RealDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.con, cls.n = pipeline.run(os.path.join(tempfile.mkdtemp(), "t.db"))

    def q(self, sql):
        return self.con.execute(sql).fetchall()

    def test_every_row_accounted_for(self):
        self.assertEqual(self.q("SELECT unaccounted_rows FROM reconciliation")[0][0], 0)

    def test_raw_count_matches_file(self):
        self.assertEqual(self.q("SELECT raw_rows FROM reconciliation")[0][0], self.n)

    def test_no_negative_days_in_mart(self):
        self.assertEqual(self.q("SELECT COUNT(*) FROM mart_requests WHERE days_to_close < 0")[0][0], 0)

    def test_percentages_in_range(self):
        for col in ("pct_within_1d", "pct_within_30d", "pct_within_90d"):
            v = self.q(f"SELECT {col} FROM kpi_overall")[0][0]
            self.assertTrue(0 <= v <= 100)

    def test_median_not_above_p90(self):
        m, p = self.q("SELECT median_days, p90_days FROM kpi_overall")[0]
        self.assertLessEqual(m, p)


class RuleTests(unittest.TestCase):
    def kinds(self, con):
        return {r[0] for r in con.execute("SELECT DISTINCT exception_type FROM exception_queue")}

    def test_each_rule_fires(self):
        con = run_fixture([
            ["1", "2024-09-01T08:00:00.000", "2024-09-03T08:00:00.000", "DOB", "A", "x", "Closed", "BROOKLYN"],
            ["2", "2024-09-01T08:00:00.000", "2024-09-02T08:00:00.000", "DOB", "A", "x", "Closed", "BROOKLYN"],
            ["2", "2024-09-01T08:00:00.000", "2024-09-02T08:00:00.000", "DOB", "A", "x", "Closed", "BROOKLYN"],  # dup
            ["3", "2024-09-05T08:00:00.000", "2024-09-01T08:00:00.000", "DOB", "A", "x", "Closed", "BRONX"],     # inverted
            ["4", "2024-09-05T08:00:00.000", "", "DOB", "A", "x", "Closed", "QUEENS"],                          # missing date
            ["5", "2024-09-05T08:00:00.000", "2024-09-09T08:00:00.000", "DOB", "A", "x", "Open", "QUEENS"],     # mismatch
            ["6", "2024-09-05T08:00:00.000", "2024-09-06T08:00:00.000", "DOB", "A", "x", "Closed", "Unspecified"],
            ["7", "2023-01-01T08:00:00.000", "2024-09-06T08:00:00.000", "DOB", "A", "x", "Closed", "BRONX"],     # long tail
            ["8", "2024-01-01T08:00:00.000", "", "DOB", "A", "x", "Open", "BRONX"],                              # aging
        ])
        got = self.kinds(con)
        for k in ["DUPLICATE_KEY", "CLOSED_BEFORE_CREATED", "CLOSED_MISSING_DATE", "STATUS_DATE_MISMATCH",
                  "UNSPECIFIED_BOROUGH", "LONG_TAIL_CLOSURE", "OPEN_AGING"]:
            self.assertIn(k, got)
        rec = con.execute("SELECT * FROM reconciliation").fetchone()
        self.assertEqual(rec[4], 0)

    def test_messy_case_is_cleaned_not_rejected(self):
        con = run_fixture([
            ["1", "2024-09-01T08:00:00.000", "2024-09-02T08:00:00.000", "DOB", "A", "x", " CLOSED ", " brooklyn "],
        ])
        self.assertEqual(con.execute("SELECT COUNT(*) FROM mart_requests").fetchone()[0], 1)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM exception_queue").fetchone()[0], 0)

    def test_duplicates_never_reach_mart(self):
        con = run_fixture([
            ["9", "2024-09-01T08:00:00.000", "2024-09-02T08:00:00.000", "DOB", "A", "x", "Closed", "BRONX"],
            ["9", "2024-09-01T08:00:00.000", "2024-09-02T08:00:00.000", "DOB", "A", "x", "Closed", "BRONX"],
        ])
        self.assertEqual(con.execute("SELECT COUNT(*) FROM mart_requests").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
