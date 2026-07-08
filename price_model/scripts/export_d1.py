"""
Export the sold records as a Cloudflare D1 import (SQL dump), replacing the
knn joblib in production: comparable sales become a SQL query.

    python export_d1.py                # writes ../cf_artifacts/d1/
    wrangler d1 create alethia-sold    # once
    wrangler d1 import alethia-sold --file=sold_records.sql --remote

Size guide: ~660k rows -> well inside the D1 free tier (5 GB storage,
5M row reads/day; one comparables query reads a few hundred rows).
"""
import gzip
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "clean_full.csv")
OUT = os.path.join(HERE, "..", "cf_artifacts", "d1")

SCHEMA = """\
DROP TABLE IF EXISTS sold_records;
CREATE TABLE sold_records (
  id            TEXT PRIMARY KEY,
  region        TEXT,
  suburb        TEXT,
  postcode      TEXT,
  address       TEXT,
  property_type TEXT,
  bedrooms      INTEGER,
  bathrooms     INTEGER,
  car_spaces    INTEGER,
  land_size_m2  REAL,
  sold_price    INTEGER,
  date_sold     TEXT,          -- ISO yyyy-mm-dd
  lat           REAL,
  lng           REAL,
  agency_name   TEXT,          -- marketing agency (~91% coverage)
  agent_names   TEXT           -- comma-separated agent(s) (~61% coverage)
);
CREATE INDEX idx_sold_suburb_type ON sold_records(suburb, property_type, date_sold);
CREATE INDEX idx_sold_postcode    ON sold_records(postcode, date_sold);
CREATE INDEX idx_sold_date        ON sold_records(date_sold);
CREATE INDEX idx_sold_agency      ON sold_records(agency_name);
"""

COMPARABLES_SQL = """\
-- Comparable sales for the estimator ("based on N similar sold properties").
-- Bind: :suburb :type :beds :lat :lng
-- Geo ranking uses a degree-space distance; at QLD latitudes 1 deg lng ~ 99km,
-- 1 deg lat ~ 111km, close enough for ranking nearby sales.
SELECT address, suburb, property_type, bedrooms, bathrooms, car_spaces,
       land_size_m2, sold_price, date_sold,
       ((lat - :lat)*(lat - :lat) + (lng - :lng)*(lng - :lng)) AS d2
FROM sold_records
WHERE property_type = :type
  AND bedrooms BETWEEN :beds - 1 AND :beds + 1
  AND date_sold >= date('now', '-24 months')
  AND lat BETWEEN :lat - 0.15 AND :lat + 0.15
  AND lng BETWEEN :lng - 0.15 AND :lng + 0.15
ORDER BY d2 ASC, date_sold DESC
LIMIT 15;
"""


def esc(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"


def val(v, as_int=False):
    if v is None or pd.isna(v):
        return "NULL"
    return str(int(v)) if as_int else str(round(float(v), 6))


def main():
    os.makedirs(OUT, exist_ok=True)
    df = pd.read_csv(DATA, dtype={"postcode": str}, parse_dates=["date_sold"])
    df["date_sold"] = df["date_sold"].dt.strftime("%Y-%m-%d")
    print(f"{len(df):,} rows")

    with open(os.path.join(OUT, "schema.sql"), "w") as fh:
        fh.write(SCHEMA)
    with open(os.path.join(OUT, "comparables.sql"), "w") as fh:
        fh.write(COMPARABLES_SQL)

    # agent columns may be absent from an older clean_full.csv — degrade to NULL
    has_agents = "agency_name" in df.columns and "agent_names" in df.columns
    if not has_agents:
        print("WARNING: clean_full.csv has no agency_name/agent_names; "
              "re-run data_prep_db.py to populate the agent leaderboard.")

    # D1 rejects any single statement over ~100KB (SQLITE_TOOBIG). Batch by
    # accumulated byte size, not row count -- agency_name/agent_names are
    # variable-length (a fixed row count that fit the old 14-column schema
    # can silently overflow once wide text columns are added).
    MAX_BATCH_BYTES = 50_000

    path = os.path.join(OUT, "sold_records.sql.gz")
    cols = ("(id,region,suburb,postcode,address,property_type,bedrooms,bathrooms,"
            "car_spaces,land_size_m2,sold_price,date_sold,lat,lng,agency_name,agent_names)")
    with gzip.open(path, "wt", compresslevel=6) as fh:
        fh.write(SCHEMA + "\n")
        batch = []
        batch_bytes = 0
        for r in df.itertuples(index=False):
            agency = esc(getattr(r, "agency_name", None)) if has_agents else "NULL"
            agents = esc(getattr(r, "agent_names", None)) if has_agents else "NULL"
            row = (
                f"({esc(r.id)},{esc(r.region)},{esc(r.suburb)},{esc(r.postcode)},"
                f"{esc(r.address)},{esc(r.property_type)},{val(r.bedrooms, True)},"
                f"{val(r.bathrooms, True)},{val(r.car_spaces, True)},{val(r.land_size_m2)},"
                f"{val(r.sold_price, True)},{esc(r.date_sold)},{val(r.lat)},{val(r.lng)},"
                f"{agency},{agents})")
            if batch and batch_bytes + len(row) + 2 > MAX_BATCH_BYTES:
                fh.write(f"INSERT INTO sold_records {cols} VALUES\n" + ",\n".join(batch) + ";\n")
                batch = []
                batch_bytes = 0
            batch.append(row)
            batch_bytes += len(row) + 2
        if batch:
            fh.write(f"INSERT INTO sold_records {cols} VALUES\n" + ",\n".join(batch) + ";\n")
    print(f"wrote {path} ({os.path.getsize(path)/1e6:.1f} MB gz)")
    print("import with: gunzip sold_records.sql.gz && "
          "wrangler d1 import <db-name> --file=sold_records.sql --remote")


if __name__ == "__main__":
    main()
