"""Generate fully synthetic ops-ticket data with deliberately injected defects.

No real company, customer, or employer data is used. Output: data/raw_tickets.csv
Run:  python data/generate_mock_data.py
"""
import csv
import os
import random
from datetime import datetime, timedelta

SEED = 42
N_TICKETS = 600
START = datetime(2026, 9, 1, 6, 0, 0)
AS_OF = datetime(2026, 10, 27, 12, 0, 0)  # snapshot time used by the pipeline

PRIORITIES = ["P1", "P2", "P3", "P4"]
PRIORITY_WEIGHTS = [0.08, 0.22, 0.45, 0.25]
CATEGORIES = ["Equipment", "Scheduling", "Materials", "Billing", "Safety Docs", "Access"]
ASSIGNEES = ["crew_a", "crew_b", "crew_c", "office_1", "office_2"]
# typical resolve hours by priority (mean) used to shape the data
MEAN_RESOLVE = {"P1": 3.0, "P2": 7.0, "P3": 20.0, "P4": 60.0}
MEAN_ACK = {"P1": 0.2, "P2": 0.8, "P3": 3.0, "P4": 7.0}

FMT = "%Y-%m-%d %H:%M:%S"


def fmt(dt):
    return dt.strftime(FMT) if dt else ""


def build():
    rnd = random.Random(SEED)
    rows = []
    for i in range(1, N_TICKETS + 1):
        created = START + timedelta(minutes=rnd.randint(0, 56 * 24 * 60))
        pr = rnd.choices(PRIORITIES, PRIORITY_WEIGHTS)[0]
        cat = rnd.choice(CATEGORIES)
        ack = created + timedelta(hours=rnd.expovariate(1 / MEAN_ACK[pr]))
        resolve = ack + timedelta(hours=rnd.expovariate(1 / MEAN_RESOLVE[pr]))
        if resolve > AS_OF:
            status, ack_s, res_s = "open", fmt(ack) if ack <= AS_OF else "", ""
        else:
            status = rnd.choices(["resolved", "closed"], [0.6, 0.4])[0]
            ack_s, res_s = fmt(ack), fmt(resolve)
        rows.append({
            "ticket_id": f"T-{i:05d}", "created_at": fmt(created),
            "acknowledged_at": ack_s, "resolved_at": res_s,
            "priority": pr, "category": cat, "status": status,
            "assignee": rnd.choice(ASSIGNEES),
        })

    # ---- inject defects (this is what the exception queue must catch) ----
    idx = list(range(len(rows)))
    rnd.shuffle(idx)
    pick = lambda n: [rows[idx.pop()] for _ in range(n)]

    for r in pick(12):                      # duplicate ticket ids
        rows.append(dict(r))
    for r in pick(10):                      # resolved before created
        if r["resolved_at"]:
            created = datetime.strptime(r["created_at"], FMT)
            r["resolved_at"] = fmt(created - timedelta(hours=rnd.randint(1, 48)))
    for r in pick(15):                      # closed/resolved but missing resolved_at
        if r["status"] in ("resolved", "closed"):
            r["resolved_at"] = ""
    for r in pick(8):                       # unknown category
        r["category"] = rnd.choice(["Misc", "???", "Other", ""])
    for r in pick(10):                      # missing / invalid priority
        r["priority"] = rnd.choice(["", "P9", "urgent"])
    for r in pick(10):                      # messy whitespace / case (should be cleaned, not rejected)
        r["priority"] = " " + r["priority"].lower() + " " if r["priority"] in PRIORITIES else r["priority"]
        r["status"] = r["status"].upper()

    rnd.shuffle(rows)
    return rows


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(out_dir, "raw_tickets.csv")
    rows = build()
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {path}")


if __name__ == "__main__":
    main()
