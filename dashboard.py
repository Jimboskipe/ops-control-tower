"""Build a single-file HTML dashboard from the pipeline output.

Run:  python dashboard.py     (after pipeline.py)   -> output/dashboard.html
"""
import html
import os
import sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(ROOT, "output", "ops.db")
OUT = os.path.join(ROOT, "output", "dashboard.html")


def table(headers, rows):
    h = "".join(f"<th>{html.escape(str(x))}</th>" for x in headers)
    b = "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><tr>{h}</tr>{b}</table>"


def bar(label, pct, target=70):
    color = "#1f9d55" if pct >= target else "#d9822b" if pct >= 50 else "#c0392b"
    return (f"<div class='bar'><span class='lbl'>{html.escape(label)}</span>"
            f"<div class='track'><div class='fill' style='width:{min(pct, 100)}%;background:{color}'></div></div>"
            f"<span class='val'>{pct}%</span></div>")


def main():
    con = sqlite3.connect(DB)
    q = lambda s: con.execute(s).fetchall()
    rec = q("SELECT * FROM reconciliation")[0]
    overall = q("SELECT requests,mean_days,median_days,p90_days,pct_within_1d,pct_within_30d,pct_within_90d FROM kpi_overall")[0]
    by_type = q("SELECT complaint_type,requests,mean_days,median_days,p90_days,pct_within_1d,pct_within_30d,pct_within_90d FROM kpi_by_type")
    by_bor = q("SELECT borough,requests,mean_days,pct_within_30d FROM kpi_by_borough")
    exc = q("SELECT exception_type,kind,severity,COUNT(*) FROM exception_queue GROUP BY 1,2,3 ORDER BY 4 DESC")
    mismatch = q("SELECT unique_key,exception_type,severity,detail FROM exception_queue WHERE kind='REJECT' LIMIT 15")
    bars = "".join(bar(f"{r[0][:24]} (<=30d)", r[6]) for r in by_type[:6])
    page = f"""<!doctype html><meta charset='utf-8'><title>Ops Control Tower — NYC DOB 311</title>
<style>body{{font-family:Segoe UI,Arial;margin:28px;max-width:1020px;color:#222}}
h1{{margin:0}}h2{{margin-top:28px;border-bottom:2px solid #ddd;padding-bottom:4px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{border:1px solid #ccc;padding:5px 8px;text-align:left}}
th{{background:#f0f3f8}}.bar{{display:flex;align-items:center;gap:10px;margin:6px 0}}.lbl{{width:210px;font-size:13px}}
.track{{flex:1;background:#eee;height:16px;border-radius:8px;overflow:hidden}}.fill{{height:100%}}.val{{width:55px;font-weight:600}}
.kpi{{display:inline-block;margin:6px 14px 6px 0;padding:10px 16px;border:1px solid #ccd;border-radius:8px}}
.kpi b{{display:block;font-size:22px}}</style>
<h1>Ops Control Tower — NYC Department of Buildings 311 Pipeline</h1>
<div>Real public municipal data: 5,000 NYC 311 Department of Buildings service requests (September 2024 intake).</div>
<div><span class='kpi'><b>{rec[0]}</b>raw rows</span><span class='kpi'><b>{rec[1]}</b>clean closed</span>
<span class='kpi'><b>{rec[2]}</b>open backlog</span><span class='kpi'><b>{rec[3]}</b>rejected (exceptions)</span>
<span class='kpi'><b>{rec[4]}</b>unaccounted</span><span class='kpi'><b>{overall[2]}d / {overall[1]}d</b>median / mean close</span></div>
<h2>30-Day Closure Rate by Top Complaint Types</h2>{bars}
{table(['Complaint Type','Requests','Mean (d)','Median (d)','P90 (d)','<=1d %','<=30d %','<=90d %'], by_type)}
<h2>Exception Queue Summary</h2>{table(['Exception Type','Kind','Severity','Count'], exc)}
<h2>Sample Rejected Rows (Status vs. Closed Date Mismatch)</h2>{table(['Unique Key','Exception','Severity','Detail'], mismatch)}
<h2>By Borough</h2>{table(['Borough','Requests','Mean (d)','<=30d %'], by_bor)}"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
