"""
Train the four model families on a shared temporal holdout and save artifacts.

  Linear Regression  - exact analytic prediction intervals (explainable baseline)
  LightGBM quantile  - native 5/50/95 band via pinball loss (recommended)
  KNN comparables    - "based on N similar sold properties"
  EBM                - glassbox GAM + split-conformal intervals

The split and feature pipeline are recomputed deterministically on every run, so
you can train models in separate invocations and the artifacts stay consistent:

    python train.py                         # everything (use this on your Mac)
    python train.py --models linear lightgbm knn
    python train.py --models ebm --ebm-bags 8

Outputs -> ../models/*.joblib, ../reports/metrics.json, ../reports/test_predictions.csv
"""
import argparse
import json
import os
import time

import joblib
import numpy as np
import pandas as pd

from features import FeaturePipeline, time_split
from metrics import regression_metrics
from models_lib import LinearPI, LgbmQuantile, EbmConformal, KnnComparables, Q_LO, Q_HI

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "clean.csv")
MODELS = os.path.join(HERE, "..", "models")
REPORTS = os.path.join(HERE, "..", "reports")
ALL_MODELS = ["linear", "lightgbm", "knn", "ebm"]
KNN_COLS = ["address", "suburb", "property_type", "lat", "lng", "bedrooms",
            "bathrooms", "car_spaces", "land_size_m2", "building_size_m2",
            "sold_price", "date_sold"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def internal_val(train, frac=0.12):
    dated = train[train["date_sold"].notna()].sort_values("date_sold")
    n_val = int(len(dated) * frac)
    val = dated.iloc[len(dated) - n_val:]
    core = train.drop(val.index)
    return core, val


def train_lgbm(Xc, yc, Xv, yv):
    # Boosters trained on core, early-stopped on val. The same held-out val set
    # then calibrates the conformal widening (honest: val is unseen by the fit).
    import lightgbm as lgb
    base = dict(objective="quantile", learning_rate=0.03, num_leaves=31,
                min_data_in_leaf=40, feature_fraction=0.8, bagging_fraction=0.8,
                bagging_freq=1, max_depth=-1, verbose=-1, seed=42, metric="quantile")
    boosters = {}
    for q in [Q_LO, 0.5, Q_HI]:
        dtr = lgb.Dataset(Xc.to_numpy(float), label=yc)
        dva = lgb.Dataset(Xv.to_numpy(float), label=yv, reference=dtr)
        m = lgb.train(dict(base, alpha=q), dtr, num_boost_round=1500, valid_sets=[dva],
                      callbacks=[lgb.early_stopping(80, verbose=False), lgb.log_evaluation(0)])
        boosters[q] = m
        log(f"  lgbm q={q}: best_iter={m.best_iteration or m.current_iteration()}")
    mq = LgbmQuantile(boosters)
    # CQR: conformity score E_i = max(lo - y, y - hi) in log space on val
    lo, _, hi = mq._log_preds(Xv)
    scores = np.maximum(lo - yv, yv - hi)
    n = len(scores)
    level = min(1.0, np.ceil((n + 1) * 0.90) / n)
    mq.cqr_delta = float(np.quantile(scores, level))
    log(f"  lgbm CQR delta (log)={mq.cqr_delta:.4f}")
    return mq


def train_ebm(Xc, yc, Xv, yv, feat_names, outer_bags, interactions):
    from interpret.glassbox import ExplainableBoostingRegressor
    ebm = ExplainableBoostingRegressor(random_state=42, interactions=interactions,
                                       outer_bags=outer_bags, n_jobs=1, feature_names=feat_names)
    ebm.fit(Xc.to_numpy(float), yc)
    resid = yv - ebm.predict(Xv.to_numpy(float))
    q_lo, q_hi = float(np.quantile(resid, 0.05)), float(np.quantile(resid, 0.95))
    log(f"  ebm conformal residual band (log): [{q_lo:.3f}, {q_hi:.3f}] bags={outer_bags}")
    return EbmConformal(ebm, q_lo, q_hi)


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=ALL_MODELS, choices=ALL_MODELS)
    ap.add_argument("--ebm-bags", type=int, default=8, help="EBM outer_bags (lower = faster/less memory)")
    ap.add_argument("--ebm-interactions", type=int, default=6)
    ap.add_argument("--test-frac", type=float, default=0.15)
    args = ap.parse_args()

    os.makedirs(MODELS, exist_ok=True)
    os.makedirs(REPORTS, exist_ok=True)
    log(f"loading data; training {args.models}")
    df = pd.read_csv(DATA, dtype={"postcode": str}, parse_dates=["date_sold"])
    df["y_log"] = np.log(df["sold_price"].astype(float))

    train, test, cutoff = time_split(df, test_frac=args.test_frac)
    core, val = internal_val(train)
    log(f"train={len(train)} (core={len(core)}, val={len(val)}) test={len(test)} cutoff={cutoff}")

    pipe = FeaturePipeline().fit(train, train["y_log"])
    Xtr, Xte = pipe.transform(train), pipe.transform(test)
    Xc, Xv = pipe.transform(core), pipe.transform(val)
    ytr, yc, yv = train["y_log"].to_numpy(), core["y_log"].to_numpy(), val["y_log"].to_numpy()
    actual = test["sold_price"].to_numpy(float)
    joblib.dump(pipe, os.path.join(MODELS, "feature_pipeline.joblib"))

    # load any existing results so separate invocations accumulate
    results = load_json(os.path.join(REPORTS, "metrics.json"), {})
    preds_path = os.path.join(REPORTS, "test_predictions.csv")
    preds = pd.read_csv(preds_path) if os.path.exists(preds_path) else pd.DataFrame({"actual": actual})
    if len(preds) != len(actual):
        preds = pd.DataFrame({"actual": actual})

    def record(name, p, lo, hi):
        results[name] = regression_metrics(actual, p, lo, hi)
        preds[f"{name}_point"], preds[f"{name}_low"], preds[f"{name}_high"] = p, lo, hi

    if "linear" in args.models:
        log("training Linear")
        m = LinearPI().fit(Xtr, train["y_log"])
        record("linear", *m.predict_interval(Xte))
        joblib.dump(m, os.path.join(MODELS, "linear.joblib"))

    if "lightgbm" in args.models:
        log("training LightGBM quantile")
        m = train_lgbm(Xc, yc, Xv, yv)
        record("lightgbm", *m.predict_interval(Xte))
        joblib.dump(m, os.path.join(MODELS, "lightgbm.joblib"))

    if "knn" in args.models:
        log("training KNN comparables")
        m = KnnComparables().fit(train[KNN_COLS], train["y_log"])
        record("knn", *m.predict_interval(None, df=test[KNN_COLS]))
        joblib.dump(m, os.path.join(MODELS, "knn.joblib"))

    if "ebm" in args.models:
        log("training EBM")
        m = train_ebm(Xc, yc, Xv, yv, pipe.feature_names_, args.ebm_bags, args.ebm_interactions)
        record("ebm", *m.predict_interval(Xte))
        joblib.dump(m, os.path.join(MODELS, "ebm.joblib"))

    # persist
    meta = {
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_train": int(len(train)), "n_test": int(len(test)),
        "test_cutoff_date": str(cutoff), "feature_names": pipe.feature_names_,
        "global_log_mean": pipe.global_mean_, "knn_cols": KNN_COLS,
        "metrics": results,
    }
    with open(os.path.join(MODELS, "metadata.json"), "w") as fh:
        json.dump(meta, fh, indent=2, default=str)
    with open(os.path.join(REPORTS, "metrics.json"), "w") as fh:
        json.dump(results, fh, indent=2)
    preds.to_csv(preds_path, index=False)
    test[["sold_price", "property_type", "region", "suburb", "date_sold"]].to_csv(
        os.path.join(REPORTS, "test_rows.csv"), index=False)

    log("comparison (all models with results so far):")
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
