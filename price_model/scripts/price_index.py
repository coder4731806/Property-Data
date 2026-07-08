"""
Method: two-way fixed effects estimated by alternating projections.
    log(price) = group_effect(suburb x type) + month_effect + noise
Iterating "month effect = mean residual by month" against "group effect = mean
residual by group" converges in a handful of passes and is robust to the sales
mix changing over time (a plain median-by-month index is not).

Outputs data/price_index.json:
    { "base_month": "2026-06", "state": {"2008-01": 0.31, ...},
      "regions": {"gold_coast": {...}, ...} }
Index values are multiplicative: price_now = price_then * I[now] / I[then].
Region indices are shrunk toward the state index where monthly counts are thin.
"""
import argparse
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SHRINK_K = 40.0   # region-month observations needed to mostly trust the region


def month_effects(d, n_iter=8):
    """Two-way FE via alternating projections. Returns dict month -> effect (log)."""
    d = d.copy()
    d["g"] = d["suburb"].astype(str) + "|" + d["property_type"].astype(str)
    y = np.log(d["sold_price"].to_numpy(float))
    g = d["g"].to_numpy()
    m = d["month"].to_numpy()
    ge = pd.Series(0.0, index=pd.unique(g))
    me = pd.Series(0.0, index=pd.unique(m))
    for _ in range(n_iter):
        resid = y - ge[g].to_numpy()
        me = pd.Series(resid, index=m).groupby(level=0).mean()
        resid = y - me[m].to_numpy()
        ge = pd.Series(resid, index=g).groupby(level=0).mean()
    return me.sort_index()


def smooth_and_fill(me, all_months):
    """Reindex to a full month range, interpolate gaps, 3-month centred smooth."""
    s = me.reindex(all_months).astype(float)
    s = s.interpolate(limit_direction="both")
    return s.rolling(3, center=True, min_periods=1).mean()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "..", "data", "clean_full.csv"))
    ap.add_argument("--out", default=os.path.join(HERE, "..", "data", "price_index.json"))
    ap.add_argument("--min-year", type=int, default=2008)
    args = ap.parse_args()

    df = pd.read_csv(args.data, dtype={"postcode": str}, parse_dates=["date_sold"])
    df = df[df["date_sold"].dt.year >= args.min_year]
    df["month"] = df["date_sold"].dt.strftime("%Y-%m")
    all_months = sorted(df["month"].unique())

    print(f"fitting state index on {len(df):,} sales, {len(all_months)} months")
    me_state = smooth_and_fill(month_effects(df), all_months)
    base_month = all_months[-1]
    base = me_state[base_month]
    state_idx = np.exp(me_state - base)

    regions = {}
    counts_by_rm = df.groupby(["region", "month"]).size()
    for region, sub in df.groupby("region"):
        if len(sub) < 2000:
            regions[region] = {m: round(float(v), 4) for m, v in state_idx.items()}
            continue
        me_r = smooth_and_fill(month_effects(sub), all_months)
        me_r = me_r - me_r[base_month]
        n = counts_by_rm.loc[region].reindex(all_months).fillna(0)
        w = n / (n + SHRINK_K)
        blended = w * me_r + (1 - w) * (me_state - base)
        idx = np.exp(blended)
        regions[region] = {m: round(float(v), 4) for m, v in idx.items()}
        print(f"  {region:32s} n={len(sub):6,}  10y growth x{idx.iloc[-1]/idx.iloc[max(0,len(idx)-121)]:.2f}")

    out = {
        "base_month": base_month,
        "built_from_rows": int(len(df)),
        "state": {m: round(float(v), 4) for m, v in state_idx.items()},
        "regions": regions,
    }
    with open(args.out, "w") as fh:
        json.dump(out, fh)
    print(f"wrote {args.out}  base={base_month}  "
          f"state index 2015-01={out['state'].get('2015-01')}  (1.0 = {base_month})")


if __name__ == "__main__":
    main()
