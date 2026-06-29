"""
Load the 12 QLD sold-price Excel files, clean them into one tidy table, attach
suburb geo-centroids, and write data/clean.csv for training.

Run:
    python data_prep.py --listings-dir ../.. --out ../data/clean.csv
"""
import argparse
import glob
import json
import os

import numpy as np
import pandas as pd

from common import (
    REGION_FROM_FILE, canonical_property_type, normalize_suburb,
    parse_date, parse_price, parse_size,
)

EXPECTED_COLS = ["ID", "Full Address", "Street", "Suburb", "State", "Postcode",
                 "Sold Price", "Date Sold", "Property Type", "Bedrooms",
                 "Bathrooms", "Car Spaces", "Land Size (m²)", "Building Size (m²)"]


def load_raw(listings_dir):
    files = sorted(glob.glob(os.path.join(listings_dir, "*.xlsx")))
    files = [f for f in files if not os.path.basename(f).startswith("~")]
    if not files:
        raise SystemExit(f"No .xlsx files in {listings_dir}")
    frames = []
    for fp in files:
        stem = os.path.splitext(os.path.basename(fp))[0]
        region = REGION_FROM_FILE.get(stem, stem.lower())
        df = pd.read_excel(fp, sheet_name=0, dtype=object)
        df.columns = [str(c).strip() for c in df.columns]
        df["__region"] = region
        df["__source"] = stem
        frames.append(df)
        print(f"  loaded {stem:32s} rows={len(df):5d} region={region}")
    return pd.concat(frames, ignore_index=True)


def clean(df, centroids_path, price_min, price_max):
    out = pd.DataFrame()
    out["id"] = df["ID"].astype(str)
    out["region"] = df["__region"]
    out["address"] = df["Full Address"].astype(str)
    out["suburb"] = df["Suburb"].map(normalize_suburb)
    out["postcode"] = df["Postcode"].astype(str).str.extract(r"(\d{3,4})", expand=False)
    out["property_type"] = df["Property Type"].map(canonical_property_type)
    out["sold_price"] = df["Sold Price"].map(parse_price)
    out["date_sold"] = df["Date Sold"].map(parse_date)
    for col, src in [("bedrooms", "Bedrooms"), ("bathrooms", "Bathrooms"), ("car_spaces", "Car Spaces")]:
        out[col] = pd.to_numeric(df[src], errors="coerce")
    out["land_size_m2"] = df["Land Size (m²)"].map(parse_size)
    out["building_size_m2"] = df["Building Size (m²)"].map(parse_size)

    n0 = len(out)
    # Dedupe by listing ID (regions overlap so the same sale appears repeatedly)
    out = out.drop_duplicates(subset=["id"], keep="first")
    n_dedupe = n0 - len(out)

    # Must have price + suburb + type
    out = out[out["sold_price"].notna() & (out["suburb"] != "") & out["property_type"].notna()]

    # Report price distribution BEFORE outlier trim
    p = out["sold_price"]
    pcts = {q: float(np.percentile(p, q)) for q in [0.5, 1, 5, 25, 50, 75, 95, 99, 99.5]}
    print("\nSold price percentiles (pre-trim):")
    for q, v in pcts.items():
        print(f"  P{q:<4} ${v:,.0f}")

    # Outlier removal: absolute bounds, then per-type 0.5/99.5 pct trim
    before = len(out)
    out = out[(out["sold_price"] >= price_min) & (out["sold_price"] <= price_max)]
    n_abs = before - len(out)

    def trim_type(g):
        lo, hi = g["sold_price"].quantile([0.005, 0.995])
        return g[(g["sold_price"] >= lo) & (g["sold_price"] <= hi)]

    before = len(out)
    out = out.groupby("property_type", group_keys=False).apply(trim_type)
    n_pct = before - len(out)

    # Sanity caps on sizes (winsorise extreme values, keep the row)
    for col, cap in [("land_size_m2", out["land_size_m2"].quantile(0.999)),
                     ("building_size_m2", out["building_size_m2"].quantile(0.999))]:
        out.loc[out[col] > cap, col] = cap
    # Implausible tiny building sizes -> treat as missing
    out.loc[(out["building_size_m2"].notna()) & (out["building_size_m2"] < 10), "building_size_m2"] = np.nan
    out.loc[(out["land_size_m2"].notna()) & (out["land_size_m2"] < 1), "land_size_m2"] = np.nan

    # Clip count features to sane ranges
    out["bedrooms"] = out["bedrooms"].clip(0, 12)
    out["bathrooms"] = out["bathrooms"].clip(0, 12)
    out["car_spaces"] = out["car_spaces"].clip(0, 20)

    # Attach geo centroids (suburb+postcode first, then suburb-only fallback)
    cen = pd.read_csv(centroids_path, dtype={"postcode": str})
    sp = cen[cen["level"] == "suburb_postcode"][["suburb", "postcode", "lat", "lng"]]
    so = cen[cen["level"] == "suburb"][["suburb", "lat", "lng"]].rename(
        columns={"lat": "lat_s", "lng": "lng_s"})
    out = out.merge(sp, on=["suburb", "postcode"], how="left").merge(so, on="suburb", how="left")
    out["lat"] = out["lat"].fillna(out["lat_s"])
    out["lng"] = out["lng"].fillna(out["lng_s"])
    out = out.drop(columns=["lat_s", "lng_s"])
    n_nogeo = int(out["lat"].isna().sum())
    # Fill the few unmatched suburbs with the dataset-wide median centroid
    out["lat"] = out["lat"].fillna(out["lat"].median())
    out["lng"] = out["lng"].fillna(out["lng"].median())

    out = out.reset_index(drop=True)

    summary = {
        "rows_raw": int(n0),
        "dupe_ids_removed": int(n_dedupe),
        "removed_abs_bounds": int(n_abs),
        "removed_pct_trim": int(n_pct),
        "rows_clean": int(len(out)),
        "suburbs": int(out["suburb"].nunique()),
        "no_geo_match_filled": int(n_nogeo),
        "price_percentiles_pretrim": pcts,
        "date_min": str(out["date_sold"].min()),
        "date_max": str(out["date_sold"].max()),
        "land_missing_pct": round(100 * out["land_size_m2"].isna().mean(), 1),
        "building_missing_pct": round(100 * out["building_size_m2"].isna().mean(), 1),
        "type_counts": out["property_type"].value_counts().to_dict(),
    }
    return out, summary


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--listings-dir", default=os.path.join(here, "..", ".."))
    ap.add_argument("--centroids", default=os.path.join(here, "..", "data", "suburb_centroids.csv"))
    ap.add_argument("--out", default=os.path.join(here, "..", "data", "clean.csv"))
    ap.add_argument("--price-min", type=float, default=50_000)
    ap.add_argument("--price-max", type=float, default=30_000_000)
    args = ap.parse_args()

    print("Loading Excel files...")
    raw = load_raw(args.listings_dir)
    clean_df, summary = clean(raw, args.centroids, args.price_min, args.price_max)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    clean_df.to_csv(args.out, index=False)
    with open(os.path.join(os.path.dirname(args.out), "data_quality.json"), "w") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print("\n=== CLEAN DATASET SUMMARY ===")
    print(json.dumps({k: v for k, v in summary.items() if k != "price_percentiles_pretrim"}, indent=2, default=str))
    print(f"\nWrote {len(clean_df):,} rows -> {args.out}")


if __name__ == "__main__":
    main()
