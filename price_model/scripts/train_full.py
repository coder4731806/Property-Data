"""
Retrain the four model families on the full sales history, index-adjusted.

Differences from train.py (which stays untouched):
  * input is data/clean_full.csv -- ~660k rows, 2008-2026
  * every price is converted to base-month dollars with data/price_index.json
    before training, so 2010..2026 sales all contribute to what attributes are
    worth while the index carries the market trend
  * models predict CURRENT-dollar prices directly (base month = newest month)
  * sample weights decay with age (half-life --half-life-months) so recent
    sales still dominate
  * evaluation converts predictions BACK to at-sale dollars, so metrics are
    honest and directly comparable with the old 28k-row run
  * outputs go to models_full/ and reports_full/ (does not clobber models/)

Run:
    python train_full.py                          # everything
    python train_full.py --models linear lightgbm
"""
import argparse
import json
import os
import time

import joblib
import numpy as np
import pandas as pd

from features import FeaturePipeline
from metrics import regression_metrics
from models_lib import LinearPI, LgbmQuantile, EbmConformal, KnnComparables, Q_LO, Q_HI

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "clean_full.csv")
INDEX = os.path.join(HERE, "..", "data", "price_index.json")
MODELS = os.path.join(HERE, "..", "models_full")
REPORTS = os.path.join(HERE, "..", "reports_full")
ALL_MODELS = ["linear", "lightgbm", "knn", "ebm"]
KNN_COLS = ["address", "suburb", "property_type", "lat", "lng", "bedrooms",
            "bathrooms", "car_spaces", "land_size_m2", "building_size_m2",
            "sold_price", "date_sold"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def attach_index(df, index):
    """Multiplier I[sale_month] per row (region index, state fallback).
    price_base = sold_price / I ; price_at_sale = price_base * I."""
    state = index["state"]
    regions = index["regions"]
    months = df["date_sold"].dt.strftime("%Y-%m")
    last = index["base_month"]

    def lookup(region, m):
        tbl = regions.get(region, state)
        return tbl.get(m) or state.get(m) or 1.0

    df = df.copy()
    df["idx"] = [lookup(r, m if m <= last else last)
                 for r, m in zip(df["region"], months)]
    df["price_adj"] = df["sold_price"] / df["idx"]
    return df


def trim_by_type(df):
    def tt(g):
        lo, hi = g["price_adj"].quantile([0.005, 0.995])
        return g[(g["price_adj"] >= lo) & (g["price_adj"] <= hi)]
    return df.groupby("property_type", group_keys=False).apply(tt)


def month_split(df, test_months=3, val_months=3):
    """test = newest N months, val = N months before that, core = rest."""
    mx = df["date_sold"].max()
    test_cut = mx - pd.DateOffset(months=test_months)
    val_cut = test_cut - pd.DateOffset(months=val_months)
    test = df[df["date_sold"] > test_cut]
    val = df[(df["date_sold"] > val_cut) & (df["date_sold"] <= test_cut)]
    core = df[df["date_sold"] <= val_cut]
    return core, val, test, test_cut


def train_lgbm(Xc, yc, wc, Xv, yv):
    import lightgbm as lgb
    base = dict(objective="quantile", learning_rate=0.05, num_leaves=63,
                min_data_in_leaf=60, feature_fraction=0.8, bagging_fraction=0.8,
                bagging_freq=1, max_depth=-1, verbose=-1, seed=42, metric="quantile")
    boosters = {}
    for q in [Q_LO, 0.5, Q_HI]:
        dtr = lgb.Dataset(Xc.to_numpy(float), label=yc, weight=wc)
        dva = lgb.Dataset(Xv.to_numpy(float), label=yv, reference=dtr)
        m = lgb.train(dict(base, alpha=q), dtr, num_boost_round=2500, valid_sets=[dva],
                      callbacks=[lgb.early_stopping(100, verbose=False), lgb.log_evaluation(0)])
        boosters[q] = m
        log(f"  lgbm q={q}: best_iter={m.best_iteration or m.current_iteration()}")
    mq = LgbmQuantile(boosters)
    lo, _, hi = mq._log_preds(Xv)
    scores = np.maximum(lo - yv, yv - hi)
    n = len(scores)
    level = min(1.0, np.ceil((n + 1) * 0.90) / n)
    mq.cqr_delta = float(np.quantile(scores, level))
    log(f"  lgbm CQR delta (log)={mq.cqr_delta:.4f}")
    return mq


def train_ebm(Xc, yc, wc, Xv, yv, feat_names, outer_bags, interactions, cap):
    from interpret.glassbox import ExplainableBoostingRegressor
    if cap and len(Xc) > cap:            # newest rows (data is date-sorted)
        Xc, yc, wc = Xc.iloc[-cap:], yc[-cap:], wc[-cap:]
        log(f"  ebm capped to newest {cap:,} rows")
    ebm = ExplainableBoostingRegressor(random_state=42, interactions=interactions,
                                       outer_bags=outer_bags, n_jobs=-1,
                                       feature_names=feat_names)
    ebm.fit(Xc.to_numpy(float), yc, sample_weight=wc)
    resid = yv - ebm.predict(Xv.to_numpy(float))
    q_lo, q_hi = float(np.quantile(resid, 0.05)), float(np.quantile(resid, 0.95))
    log(f"  ebm conformal residual band (log): [{q_lo:.3f}, {q_hi:.3f}]")
    return EbmConformal(ebm, q_lo, q_hi)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=ALL_MODELS, choices=ALL_MODELS)
    ap.add_argument("--min-year", type=int, default=2013)
    ap.add_argument("--half-life-months", type=float, default=24.0)
    ap.add_argument("--knn-months", type=int, default=24)
    ap.add_argument("--ebm-bags", type=int, default=4)
    ap.add_argument("--ebm-interactions", type=int, default=6)
    ap.add_argument("--ebm-cap", type=int, default=250_000)
    args = ap.parse_args()

    os.makedirs(MODELS, exist_ok=True)
    os.makedirs(REPORTS, exist_ok=True)

    log(f"loading {DATA}")
    df = pd.read_csv(DATA, dtype={"postcode": str}, parse_dates=["date_sold"])
    with open(INDEX) as fh:
        index = json.load(fh)
    df = df[df["date_sold"].dt.year >= args.min_year]
    df = attach_index(df, index)
    n0 = len(df)
    df = trim_by_type(df).sort_values("date_sold").reset_index(drop=True)
    log(f"rows {args.min_year}+: {n0:,} -> {len(df):,} after per-type trim "
        f"(base month {index['base_month']})")

    df["y_log"] = np.log(df["price_adj"])
    age_m = (df["date_sold"].max() - df["date_sold"]).dt.days / 30.44
    df["w"] = 0.5 ** (age_m / args.half_life_months)

    core, val, test, cutoff = month_split(df)
    train = pd.concat([core, val])
    log(f"core={len(core):,} val={len(val):,} test={len(test):,} test_cutoff={cutoff.date()}")

    pipe = FeaturePipeline().fit(train, train["y_log"])
    Xc, Xv, Xte = pipe.transform(core), pipe.transform(val), pipe.transform(test)
    Xtr = pipe.transform(train)
    yc, yv = core["y_log"].to_numpy(), val["y_log"].to_numpy()
    wc = core["w"].to_numpy()
    joblib.dump(pipe, os.path.join(MODELS, "feature_pipeline.joblib"))

    # actuals in AT-SALE dollars; models predict base-month dollars, so scale
    # predictions by the test rows' index multiplier before scoring
    actual = test["sold_price"].to_numpy(float)
    mult = test["idx"].to_numpy(float)

    results = {}
    preds = pd.DataFrame({"actual": actual})

    def record(name, p, lo, hi):
        p, lo, hi = p * mult, lo * mult, hi * mult
        results[name] = regression_metrics(actual, p, lo, hi)
        preds[f"{name}_point"], preds[f"{name}_low"], preds[f"{name}_high"] = p, lo, hi
        m = results[name]
        log(f"  {name}: MAE=${m['mae']:,.0f} MedAPE={m['median_ape_pct']:.1f}% "
            f"<10%={m['within_10pct']:.0f} cover90={m['coverage_90_pct']:.1f} "
            f"width={m['median_rel_interval_width_pct']:.0f}%")

    if "linear" in args.models:
        log("training Linear")
        m = LinearPI().fit(Xtr, train["y_log"])
        record("linear", *m.predict_interval(Xte))
        joblib.dump(m, os.path.join(MODELS, "linear.joblib"))

    if "lightgbm" in args.models:
        log("training LightGBM quantile (weighted)")
        m = train_lgbm(Xc, yc, wc, Xv, yv)
        record("lightgbm", *m.predict_interval(Xte))
        joblib.dump(m, os.path.join(MODELS, "lightgbm.joblib"))

    if "knn" in args.models:
        log(f"training KNN comparables (last {args.knn_months} months)")
        knn_cut = df["date_sold"].max() - pd.DateOffset(months=args.knn_months)
        recent = train[train["date_sold"] > knn_cut]
        m = KnnComparables().fit(recent[KNN_COLS].reset_index(drop=True),
                                 recent["y_log"].reset_index(drop=True))
        record("knn", *m.predict_interval(None, df=test[KNN_COLS]))
        joblib.dump(m, os.path.join(MODELS, "knn.joblib"))

    if "ebm" in args.models:
        log("training EBM (weighted)")
        m = train_ebm(Xc, yc, wc, Xv, yv, pipe.feature_names_,
                      args.ebm_bags, args.ebm_interactions, args.ebm_cap)
        record("ebm", *m.predict_interval(Xte))
        joblib.dump(m, os.path.join(MODELS, "ebm.joblib"))

    meta = {
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_train": int(len(train)), "n_test": int(len(test)),
        "min_year": args.min_year, "half_life_months": args.half_life_months,
        "index_base_month": index["base_month"],
        "test_cutoff_date": str(cutoff), "feature_names": pipe.feature_names_,
        "global_log_mean": pipe.global_mean_, "knn_cols": KNN_COLS,
        "metrics": results,
    }
    with open(os.path.join(MODELS, "metadata.json"), "w") as fh:
        json.dump(meta, fh, indent=2, default=str)
    with open(os.path.join(REPORTS, "metrics.json"), "w") as fh:
        json.dump(results, fh, indent=2)
    preds.to_csv(os.path.join(REPORTS, "test_predictions.csv"), index=False)

    log("comparison:")
    hdr = f"{'model':<11}{'MAE':>12}{'MAPE%':>8}{'MedAPE%':>9}{'<10%':>7}{'<20%':>7}{'R2log':>7}{'Cover90':>9}{'Width%':>8}"
    print(hdr); print("-" * len(hdr))
    for name in ALL_MODELS:
        if name in results:
            m = results[name]
            print(f"{name:<11}{m['mae']:>12,.0f}{m['mape_pct']:>8.1f}{m['median_ape_pct']:>9.1f}"
                  f"{m['within_10pct']:>7.0f}{m['within_20pct']:>7.0f}{m['r2_log']:>7.3f}"
                  f"{m['coverage_90_pct']:>9.1f}{m['median_rel_interval_width_pct']:>8.0f}")


if __name__ == "__main__":
    main()
