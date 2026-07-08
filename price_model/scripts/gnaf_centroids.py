"""
Build per-suburb and per-(suburb, postcode) geographic centroids from the
G-NAF seed files shipped in the Alethia repo (apps/api/seeds/gnaf_seed_*.sql).

G-NAF (Geocoded National Address File) is open Australian government address
data, not confidential. We only read it to compute approximate suburb centroids
(median lat/lng) so the price models have real geography. The resulting
suburb_centroids.csv is a small artifact that ships with the model, so this
script only needs to be re-run if the underlying address data changes.

Usage:
    python gnaf_centroids.py \
        --gnaf-dir /path/to/Alethia/apps/api/seeds \
        --out ../data/suburb_centroids.csv
"""
import argparse
import csv
import glob
import os
import re
import statistics
from collections import defaultdict

# Matches one VALUES tuple:
# ('PID','ADDRESS','SUBURB','POSTCODE',lat,lng,'GEOCODE_TYPE')
# Single quotes inside a field are escaped by doubling ('') in SQLite dumps.
ROW_RE = re.compile(
    r"\('(?:[^']|'')*',"          # pid
    r"'(?:[^']|'')*',"            # address_line1
    r"'((?:[^']|'')*)',"          # suburb  (captured)
    r"'(\d{3,4})',"               # postcode (captured)
    r"(-?\d+\.?\d*),"             # lat (captured)
    r"(-?\d+\.?\d*),"             # lng (captured)
    r"'[^']*'\)"                  # geocode_type
)


def parse_seeds(gnaf_dir):
    files = sorted(glob.glob(os.path.join(gnaf_dir, "gnaf_seed_*.sql")))
    if not files:
        raise SystemExit(f"No gnaf_seed_*.sql found in {gnaf_dir}")
    by_suburb_pc = defaultdict(lambda: ([], []))  # (suburb, postcode) -> (lats, lngs)
    by_suburb = defaultdict(lambda: ([], []))      # suburb -> (lats, lngs)
    n = 0
    for fp in files:
        with open(fp, "r", encoding="utf-8") as fh:
            text = fh.read()
        for m in ROW_RE.finditer(text):
            suburb = m.group(1).replace("''", "'").strip().upper()
            postcode = m.group(2).strip()
            lat = float(m.group(3))
            lng = float(m.group(4))
            # QLD sanity bbox (generous): lat ~ -29..-9, lng ~ 138..154
            if not (-30 < lat < -9 and 137 < lng < 155):
                continue
            by_suburb_pc[(suburb, postcode)][0].append(lat)
            by_suburb_pc[(suburb, postcode)][1].append(lng)
            by_suburb[suburb][0].append(lat)
            by_suburb[suburb][1].append(lng)
            n += 1
    return by_suburb_pc, by_suburb, n, len(files)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--gnaf-dir", default=os.path.join(here, "..", "..", "..", "Alethia", "apps", "api", "seeds"),
                    help="Directory holding gnaf_seed_*.sql")
    ap.add_argument("--out", default=os.path.join(here, "..", "data", "suburb_centroids.csv"))
    args = ap.parse_args()

    by_suburb_pc, by_suburb, n_rows, n_files = parse_seeds(args.gnaf_dir)

    rows = []
    # (suburb, postcode) level centroids
    for (suburb, pc), (lats, lngs) in by_suburb_pc.items():
        rows.append({
            "suburb": suburb,
            "postcode": pc,
            "lat": round(statistics.median(lats), 6),
            "lng": round(statistics.median(lngs), 6),
            "n_addresses": len(lats),
            "level": "suburb_postcode",
        })
    # suburb-only centroids (fallback when postcode unknown / mismatched)
    for suburb, (lats, lngs) in by_suburb.items():
        rows.append({
            "suburb": suburb,
            "postcode": "",
            "lat": round(statistics.median(lats), 6),
            "lng": round(statistics.median(lngs), 6),
            "n_addresses": len(lats),
            "level": "suburb",
        })

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["suburb", "postcode", "lat", "lng", "n_addresses", "level"])
        w.writeheader()
        w.writerows(rows)

    n_sp = sum(1 for r in rows if r["level"] == "suburb_postcode")
    n_s = sum(1 for r in rows if r["level"] == "suburb")
    print(f"Parsed {n_rows:,} GNAF addresses from {n_files} files")
    print(f"Wrote {len(rows):,} centroid rows ({n_sp:,} suburb+postcode, {n_s:,} suburb) -> {args.out}")


if __name__ == "__main__":
    main()
