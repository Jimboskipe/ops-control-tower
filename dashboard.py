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


def bar(label, pct, target=95):
    color = "#1f9d55" if pct >= target else "#d9822b" if pct >= 80 else "#c0392b"
    return (f"<div class='bar'><span class='lbl'>{html.escape(label)}</span>"
            f"<div class='track'><div class='fill' style='width:{pct}%;background:{color}'></div></div>"
            f"<span class='val'>{pct}%</span></div>")


def main():
    con = sqlite3.connect(DB)
    q = lambda s: con.execute(s).fetchall()
    rec = q("SELECT * FROM reconciliation")[0]
    sla = q("SELECT priority,tickets,ack_sla_pct,resolve_sla_pct,mttr_hours,resolve_target_hours FROM kpi_sla_by_priority")
    weekly = q("SELECT created_week,tickets,mttr_hours,resolve_sla_pct FROM kpi_mttr_weekly")
    cats = q("SELECT category,tickets,mttr_hours,resolve_sla_pct FROM kpi_by_category")
    exc = q("SELECT exception_type,kind,severity,COUNT(*) FROM exception_queue GROUP BY 1,2,3 ORDER BY 4 DESC")
    breaches = q("SELECT ticket_id,priority,category,age_hours,resolve_target_hours FROM mart_open_backlog "
                 "WHERE age_hours > resolve_target_hours ORDER BY age_hours DESC LIMIT 15")
    bars = "".join(bar(f"{r[0]} resolve SLA", r[3]) for r in sla)
    page = f"""<!doctype html><meta charset='utf-8'><title>Ops Control Tower</title>
<style>body{{font-family:Segoe UI,Arial;margin:28px;max-width:980px;color:#222}}
h1{{margin:0}}h2{{margin-top:28px;border-bottom:2px solid #ddd;padding-bottom:4px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{border:1px solid #ccc;padding:5px 8px;text-align:left}}
th{{background:#f0f3f8}}.bar{{display:flex;align-items:center;gap:10px;margin:6px 0}}.lbl{{width:140px;font-size:13px}}
.track{{flex:1;background:#eee;height:16px;border-radius:8px;overflow:hidden}}.fill{{height:100%}}.val{{width:50px;font-weight:600}}
.kpi{{display:inline-block;margin:6px 14px 6px 0;padding:10px 16px;border:1px solid #ccd;border-radius:8px}}
.kpi b{{display:block;font-size:22px}}</style>
<h1>Ops Control Tower</h1><div>Synthetic data. Snapshot as of 2026-10-27 12:00.</div>
<div><span class='kpi'><b>{rec[0]}</b>raw rows</span><span class='kpi'><b>{rec[1]}</b>clean resolved</span>
<span class='kpi'><b>{rec[2]}</b>open</span><span class='kpi'><b>{rec[3]}</b>rejected</span>
<span class='kpi'><b>{rec[4]}</b>unaccounted</span></div>
<h2>Resolve SLA by priority</h2>{bars}
{table(['Priority','Tickets','Ack SLA %','Resolve SLA %','MTTR (h)','Target (h)'], sla)}
<h2>Exception queue</h2>{table(['Exception','Kind','Severity','Count'], exc)}
<h2>Open tickets past SLA (worst 15)</h2>{table(['Ticket','Priority','Category','Age (h)','Target (h)'], breaches)}
<h2>MTTR by week</h2>{table(['Week','Tickets','MTTR (h)','Resolve SLA %'], weekly)}
<h2>By category</h2>{table(['Category','Tickets','MTTR (h)','Resolve SLA %'], cats)}"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
