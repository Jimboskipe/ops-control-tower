"""Download the public dataset used by Ops Control Tower.

Source: NYC Open Data, 311 Service Requests (dataset erm2-nwe9), Department of Buildings
requests created in September 2024. Public data, no API key needed.

Run:  python data/fetch_data.py
"""
import os
import urllib.parse
import urllib.request

BASE = "https://data.cityofnewyork.us/resource/erm2-nwe9.csv"
QUERY = {
    "$select": "unique_key,created_date,closed_date,agency,complaint_type,descriptor,status,borough",
    "$where": "agency='DOB' AND created_date between '2024-09-01T00:00:00' AND '2024-09-30T23:59:59'",
    "$limit": "5000",
    "$order": "created_date",
}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw_311_dob_2024-09.csv")


def main():
    url = BASE + "?" + urllib.parse.urlencode(QUERY)
    data = urllib.request.urlopen(url, timeout=60).read().decode("utf-8")
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(data)
    print("wrote", OUT, "-", data.count("\n") - 1, "rows")


if __name__ == "__main__":
    main()
