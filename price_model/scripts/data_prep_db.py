"""
Build the FULL training table straight from the REAscrape region SQLite dbs
(skips the xlsx export step entirely, so all ~660k scraped sold records are
available, not just the 33k that made it into the spreadsheets).

Usage:
    python data_prep_db.py --data-dir /path/to/REAscrape/data \
                           --out ../data/clean_full.csv

Output columns match clean.csv plus nothing else changes downstream:
    id,region,address,suburb,postcode,property_type,sold_price,date_sold,
    bedrooms,bathrooms,car_spaces,land_size_m2,building_size_m2,lat,lng,
    agency_name,agent_names
(agency_name/agent_names are carried through only for the D1 export / agent
leaderboard; the trainers select feature columns by name and ignore them.)
"""
import argparse
import glob
import json
import os
import sqlite3

import numpy as np
import pandas as pd

from common import canonical_property_type, normalize_suburb, parse_date, parse_price, parse_size

HERE = os.path.dirname(os.path.abspath(__file__))

# absolute sanity bounds only; statistical trimming happens at train time on
# index-adjusted prices (so a cheap-but-normal 2010 sale is not clipped by
# 2026 standards)
PRICE_MIN, PRICE_MAX = 30_000, 30_000_000


def suburb_region_map(data_dir):
    """region folders contain one directory per scraped suburb; that mapping is
    more trustworthy than the db rows (some dbs were built across regions)."""
    m = {}
    for region_dir in sorted(glob.glob(os.path.join(data_dir, "*"))):
        if not os.path.isdir(region_dir):
            continue
        region = os.path.basename(region_dir).replace("-", "_")
        for sub_dir in glob.glob(os.path.join(region_dir, "*")):
            if os.path.isdir(sub_dir):
                sub = normalize_suburb(os.path.basename(sub_dir).replace("-", " "))
                m.setdefault(sub, region)
    return m


def load_dbs(data_dir):
    frames = []
    for db_path in sorted(glob.glob(os.path.join(data_dir, "*", "*.db"))):
        name = os.path.basename(db_path)
        if "progress" in name:
            continue
        region = os.path.splitext(name)[0].replace("-", "_")
        con = sqlite3.connect(db_path)
        df = pd.read_sql_query(
            """SELECT id, suburb, postcode, full_address, street_address,
                      property_type, bedrooms, bathrooms, car_spaces,
                      land_size_m2, sale_price, sold_date,
                      agency_name, agent_names
               FROM listings""", con)
        con.close()
        df["__region"] = region
        frames.append(df)
        print(f"  loaded {region:32s} rows={len(df):6d}")
    if not frames:
        raise SystemExit(f"No region .db files under {data_dir}")
    return pd.concat(frames, ignore_index=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "..", "data", "clean_full.csv"))
    ap.add_argument("--centroids", default=os.path.join(HERE, "..", "data", "suburb_centroids.csv"))
    args = ap.parse_args()

    raw = load_dbs(args.data_dir)
    n0 = len(raw)

    sub2region = suburb_region_map(args.data_dir)
    out = pd.DataFrame()
    out["id"] = raw["id"].astype(str)
    suburbs_norm = raw["suburb"].map(normalize_suburb)
    out["region"] = suburbs_norm.map(sub2region).fillna(raw["__region"])
    addr = raw["full_address"].fillna(raw["street_address"])
    out["address"] = addr.astype(str)
    out["suburb"] = raw["suburb"].map(normalize_suburb)
    out["postcode"] = raw["postcode"].astype(str).str.extract(r"(\d{3,4})", expand=False)
    out["property_type"] = raw["property_type"].map(canonical_property_type)
    out["sold_price"] = raw["sale_price"].map(parse_price)
    out["date_sold"] = raw["sold_date"].map(parse_date)
    for col, src in [("bedrooms", "bedrooms"), ("bathrooms", "bathrooms"), ("car_spaces", "car_spaces")]:
        out[col] = pd.to_numeric(raw[src], errors="coerce")
    out["land_size_m2"] = raw["land_size_m2"].map(parse_size)
    out["building_size_m2"] = np.nan  # not captured in the db schema

    # marketing agency + agent(s) — carried through for the D1 export and the
    # suburb agent leaderboard; not used as model features. agent_names is a
    # comma-separated list as scraped (e.g. "Jane Doe, John Smith").
    def _clean_txt(s):
        s = s.astype(str).str.strip()
        return s.where(~s.isin(["", "None", "nan", "NaN", "null"]), other=np.nan)
    out["agency_name"] = _clean_txt(raw["agency_name"])
    out["agent_names"] = _clean_txt(raw["agent_names"])

    # dedupe across overlapping regions
    out = out.drop_duplicates(subset=["id"], keep="first")
    n_dedupe = n0 - len(out)

    out = out[out["sold_price"].notna() & (out["suburb"] != "") & out["property_type"].notna()]
    out = out[(out["sold_price"] >= PRICE_MIN) & (out["sold_price"] <= PRICE_MAX)]
    out = out[out["date_sold"].notna() & (out["date_sold"] >= pd.Timestamp("2000-01-01"))]

    # attach suburb centroids
    cent = pd.read_csv(args.centroids)
    cent.columns = [c.lower() for c in cent.columns]
    sub_col = "suburb" if "suburb" in cent.columns else cent.columns[0]
    cent[sub_col] = cent[sub_col].map(normalize_suburb)
    cent = cent.drop_duplicates(subset=[sub_col])
    lat_c = "lat" if "lat" in cent.columns else "latitude"
    lng_c = "lng" if "lng" in cent.columns else "longitude"
    out = out.merge(cent[[sub_col, lat_c, lng_c]].rename(
        columns={sub_col: "suburb", lat_c: "lat", lng_c: "lng"}), on="suburb", how="left")
    no_geo = int(out["lat"].isna().sum())
    # fill missing geo with postcode means then global mean
    pc_mean = out.groupby("postcode")[["lat", "lng"]].transform("mean")
    out[["lat", "lng"]] = out[["lat", "lng"]].fillna(pc_mean)
    out[["lat", "lng"]] = out[["lat", "lng"]].fillna(out[["lat", "lng"]].mean())

    out = out.sort_values("date_sold").reset_index(drop=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    out.to_csv(args.out, index=False)

    q = {
        "rows_raw": int(n0),
        "dupe_ids_removed": int(n_dedupe),
        "rows_clean": int(len(out)),
        "suburbs": int(out["suburb"].nunique()),
        "date_min": str(out["date_sold"].min()),
        "date_max": str(out["date_sold"].max()),
        "no_geo_match_filled": no_geo,
        "land_missing_pct": round(float(out["land_size_m2"].isna().mean() * 100), 1),
        "type_counts": out["property_type"].value_counts().to_dict(),
        "rows_by_year": out["date_sold"].dt.year.value_counts().sort_index().to_dict(),
    }
    with open(os.path.join(os.path.dirname(os.path.abspath(args.out)), "data_quality_full.json"), "w") as fh:
        json.dump(q, fh, indent=2, default=str)
    print(json.dumps(q, indent=2, default=str))


if __name__ == "__main__":
    main()
