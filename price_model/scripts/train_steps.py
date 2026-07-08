"""
Resumable step-by-step version of train_full.py for environments with short
execution windows (each step finishes fast and persists state to disk).
On a normal machine just run train_full.py instead -- same results.

    python train_steps.py prep
    python train_steps.py linear
    python train_steps.py lgbm --q 0.5 --rounds 400      # repeat to add rounds
    python train_steps.py lgbm-finalize
    python train_steps.py knn
    python train_steps.py ebm --cap 80000 --bags 2 --interactions 4
    python train_steps.py report
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
from train_full import DATA, INDEX, MODELS, REPORTS, KNN_COLS, attach_index, trim_by_type, month_split

WORK = os.path.join(MODELS, "_work")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def pinball(y, p, q):
    d = y - p
    return float(np.mean(np.maximum(q * d, (q - 1) * d)))


# --------------------------------------------------------------------------- #
def step_prep(args):
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(REPORTS, exist_ok=True)
    df = pd.read_csv(DATA, dtype={"postcode": str}, parse_dates=["date_sold"])
    with open(INDEX) as fh:
        index = json.load(fh)
    df = df[df["date_sold"].dt.year >= args.min_year]
    df = attach_index(df, index)
    df = trim_by_type(df).sort_values("date_sold").reset_index(drop=True)
    df["y_log"] = np.log(df["price_adj"])
    age_m = (df["date_sold"].max() - df["date_sold"]).dt.days / 30.44
    df["w"] = 0.5 ** (age_m / args.half_life_months)

    core, val, test, cutoff = month_split(df)
    train = pd.concat([core, val])
    log(f"rows={len(df):,} core={len(core):,} val={len(val):,} test={len(test):,} cutoff={cutoff.date()}")

    pipe = FeaturePipeline().fit(train, train["y_log"])
    joblib.dump(pipe, os.path.join(MODELS, "feature_pipeline.joblib"))
    blobs = {
        "Xc": pipe.transform(core), "Xv": pipe.transform(val),
        "Xte": pipe.transform(test), "Xtr": pipe.transform(train),
        "yc": core["y_log"].to_numpy(), "yv": val["y_log"].to_numpy(),
        "ytr": train["y_log"].to_numpy(), "wc": core["w"].to_numpy(),
        "test": test.reset_index(drop=True),
        "train_knn": train[KNN_COLS + ["y_log", "date_sold"]].reset_index(drop=True),
        "meta": {"cutoff": str(cutoff), "base_month": index["base_month"],
                 "min_year": args.min_year, "half_life_months": args.half_life_months,
                 "n_train": int(len(train)), "n_test": int(len(test))},
    }
    joblib.dump(blobs, os.path.join(WORK, "arrays.joblib"))
    log("prep done")


def load_work():
    return joblib.load(os.path.join(WORK, "arrays.joblib"))


def record(name, p, lo, hi, test):
    mult = test["idx"].to_numpy(float)
    actual = test["sold_price"].to_numpy(float)
    p, lo, hi = p * mult, lo * mult, hi * mult
    res_path = os.path.join(REPORTS, "metrics.json")
    results = json.load(open(res_path)) if os.path.exists(res_path) else {}
    results[name] = regression_metrics(actual, p, lo, hi)
    with open(res_path, "w") as fh:
        json.dump(results, fh, indent=2)
    preds_path = os.path.join(REPORTS, "test_predictions.csv")
    preds = pd.read_csv(preds_path) if os.path.exists(preds_path) else pd.DataFrame({"actual": actual})
    preds[f"{name}_point"], preds[f"{name}_low"], preds[f"{name}_high"] = p, lo, hi
    preds.to_csv(preds_path, index=False)
    m = results[name]
    log(f"{name}: MAE=${m['mae']:,.0f} MedAPE={m['median_ape_pct']:.1f}% "
        f"<10%={m['within_10pct']:.0f} cover90={m['coverage_90_pct']:.1f} "
        f"width={m['median_rel_interval_width_pct']:.0f}%")


# --------------------------------------------------------------------------- #
def step_linear(args):
    b = load_work()
    m = LinearPI().fit(b["Xtr"], pd.Series(b["ytr"]))
    record("linear", *m.predict_interval(b["Xte"]), b["test"])
    joblib.dump(m, os.path.join(MODELS, "linear.joblib"))


# --------------------------------------------------------------------------- #
def lgbm_params():
    return dict(objective="quantile", learning_rate=0.05, num_leaves=63,
                min_data_in_leaf=60, feature_fraction=0.8, bagging_fraction=0.8,
                bagging_freq=1, max_depth=-1, verbose=-1, seed=42, metric="quantile")


def step_lgbm(args):
    import lightgbm as lgb
    b = load_work()
    q = float(args.q)
    tag = f"lgbm_q{q}".replace(".", "")
    model_path = os.path.join(WORK, f"{tag}.txt")
    hist_path = os.path.join(WORK, f"{tag}_hist.json")
    hist = json.load(open(hist_path)) if os.path.exists(hist_path) else {"rounds": 0, "val": []}

    dtr = lgb.Dataset(b["Xc"].to_numpy(float), label=b["yc"], weight=b["wc"])
    init = model_path if os.path.exists(model_path) else None
    m = lgb.train(dict(lgbm_params(), alpha=q), dtr, num_boost_round=args.rounds,
                  init_model=init, keep_training_booster=True)
    m.save_model(model_path)
    hist["rounds"] += args.rounds
    v = pinball(b["yv"], m.predict(b["Xv"].to_numpy(float)), q)
    hist["val"].append(v)
    with open(hist_path, "w") as fh:
        json.dump(hist, fh)
    log(f"q={q} total_rounds={hist['rounds']} val_pinball={v:.5f} (history: {['%.5f' % x for x in hist['val']]})")


def step_lgbm_finalize(args):
    import lightgbm as lgb
    b = load_work()
    boosters = {}
    for q in [Q_LO, 0.5, Q_HI]:
        tag = f"lgbm_q{q}".replace(".", "")
        boosters[q] = lgb.Booster(model_file=os.path.join(WORK, f"{tag}.txt"))
    mq = LgbmQuantile(boosters)
    lo, _, hi = mq._log_preds(b["Xv"])
    scores = np.maximum(lo - b["yv"], b["yv"] - hi)
    n = len(scores)
    level = min(1.0, np.ceil((n + 1) * 0.90) / n)
    mq.cqr_delta = float(np.quantile(scores, level))
    log(f"CQR delta={mq.cqr_delta:.4f}")
    record("lightgbm", *mq.predict_interval(b["Xte"]), b["test"])
    joblib.dump(mq, os.path.join(MODELS, "lightgbm.joblib"))


# --------------------------------------------------------------------------- #
def step_knn(args):
    b = load_work()
    tr = b["train_knn"]
    tr = tr.loc[:, ~tr.columns.duplicated()]
    ds = pd.to_datetime(tr["date_sold"])
    cut = ds.max() - pd.DateOffset(months=args.knn_months)
    recent = tr[ds > cut].reset_index(drop=True)
    log(f"KNN training rows: {len(recent):,}")
    m = KnnComparables().fit(recent[KNN_COLS], recent["y_log"])
    joblib.dump(m, os.path.join(MODELS, "knn.joblib"))
    log("KNN fitted + saved; run knn-eval next")


def step_knn_eval(args):
    b = load_work()
    m = joblib.load(os.path.join(MODELS, "knn.joblib"))
    test = b["test"]
    dfk = test[KNN_COLS]
    # batched eval: vectorise per property type (much faster than row loop)
    points = np.empty(len(dfk)); los = np.empty(len(dfk)); his = np.empty(len(dfk))
    Z = m._vec(dfk)
    types = dfk["property_type"].astype(str).to_numpy()
    done = np.zeros(len(dfk), bool)
    for t, idx_obj in m.type_idx_.items():
        sel = np.where(types == t)[0]
        if len(sel) == 0:
            continue
        dist, idx = idx_obj.kneighbors(Z[sel])
        rows = m.type_rows_[t][idx]
        w = 1.0 / (dist + 1e-6)
        logp = m.y_[rows]
        points[sel] = np.exp((logp * w).sum(1) / w.sum(1))
        prices = m.price_[rows]
        los[sel] = np.percentile(prices, 5, axis=1)
        his[sel] = np.percentile(prices, 95, axis=1)
        done[sel] = True
    rest = np.where(~done)[0]
    if len(rest):
        dist, idx = m.index_all_.kneighbors(Z[rest])
        w = 1.0 / (dist + 1e-6)
        logp = m.y_[idx]
        points[rest] = np.exp((logp * w).sum(1) / w.sum(1))
        prices = m.price_[idx]
        los[rest] = np.percentile(prices, 5, axis=1)
        his[rest] = np.percentile(prices, 95, axis=1)
    record("knn", points, los, his, test)


# --------------------------------------------------------------------------- #
def step_ebm(args):
    from interpret.glassbox import ExplainableBoostingRegressor
    b = load_work()
    Xc, yc, wc = b["Xc"], b["yc"], b["wc"]
    if args.cap and len(Xc) > args.cap:
        Xc, yc, wc = Xc.iloc[-args.cap:], yc[-args.cap:], wc[-args.cap:]
        log(f"ebm capped to newest {args.cap:,} rows")
    ebm = ExplainableBoostingRegressor(random_state=42, interactions=args.interactions,
                                       outer_bags=args.bags, n_jobs=-1,
                                       feature_names=list(b["Xc"].columns),
                                       max_rounds=args.max_rounds)
    t0 = time.time()
    ebm.fit(Xc.to_numpy(float), yc, sample_weight=wc)
    log(f"ebm fit in {time.time()-t0:.0f}s")
    resid = b["yv"] - ebm.predict(b["Xv"].to_numpy(float))
    q_lo, q_hi = float(np.quantile(resid, 0.05)), float(np.quantile(resid, 0.95))
    m = EbmConformal(ebm, q_lo, q_hi)
    record("ebm", *m.predict_interval(b["Xte"]), b["test"])
    joblib.dump(m, os.path.join(MODELS, "ebm.joblib"))


# --------------------------------------------------------------------------- #
def step_report(args):
    b = load_work()
    results = json.load(open(os.path.join(REPORTS, "metrics.json")))
    pipe = joblib.load(os.path.join(MODELS, "feature_pipeline.joblib"))
    meta = dict(b["meta"])
    meta.update({"trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "feature_names": pipe.feature_names_,
                 "global_log_mean": pipe.global_mean_,
                 "knn_cols": KNN_COLS, "metrics": results})
    with open(os.path.join(MODELS, "metadata.json"), "w") as fh:
        json.dump(meta, fh, indent=2, default=str)
    hdr = f"{'model':<11}{'MAE':>12}{'MAPE%':>8}{'MedAPE%':>9}{'<10%':>7}{'<20%':>7}{'R2log':>7}{'Cover90':>9}{'Width%':>8}"
    print(hdr); print("-" * len(hdr))
    for name in ["linear", "lightgbm", "knn", "ebm"]:
        if name in results:
            m = results[name]
            print(f"{name:<11}{m['mae']:>12,.0f}{m['mape_pct']:>8.1f}{m['median_ape_pct']:>9.1f}"
                  f"{m['within_10pct']:>7.0f}{m['within_20pct']:>7.0f}{m['r2_log']:>7.3f}"
                  f"{m['coverage_90_pct']:>9.1f}{m['median_rel_interval_width_pct']:>8.0f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["prep", "linear", "lgbm", "lgbm-finalize",
                                     "knn", "knn-eval", "ebm", "report"])
    ap.add_argument("--min-year", type=int, default=2013)
    ap.add_argument("--half-life-months", type=float, default=24.0)
    ap.add_argument("--q", default="0.5")
    ap.add_argument("--rounds", type=int, default=400)
    ap.add_argument("--knn-months", type=int, default=24)
    ap.add_argument("--cap", type=int, default=80_000)
    ap.add_argument("--bags", type=int, default=2)
    ap.add_argument("--interactions", type=int, default=4)
    ap.add_argument("--max-rounds", type=int, default=4000)
    args = ap.parse_args()
    os.makedirs(MODELS, exist_ok=True)
    {"prep": step_prep, "linear": step_linear, "lgbm": step_lgbm,
     "lgbm-finalize": step_lgbm_finalize, "knn": step_knn, "knn-eval": step_knn_eval,
     "ebm": step_ebm, "report": step_report}[args.step](args)


if __name__ == "__main__":
    main()
