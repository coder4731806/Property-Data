"""
Export the trained models as Cloudflare-servable artifacts (no Python needed
at inference time).

    python export_cf.py models    # pipeline.json, linear.json, ebm.json (+ parity check)
    python export_cf.py lgbm      # lightgbm.json (flat tree arrays) + gz (+ parity check)
    python export_cf.py extras    # price_index.json copy + manifest.json

Outputs -> ../cf_artifacts/

Deployment model:
  * ebm.json + linear.json + pipeline.json are small: evaluate INSIDE the
    Worker (sum of lookup-table contributions, well under the 10ms CPU limit).
  * lightgbm.json(.gz) is a few MB: serve as a static asset and evaluate in the
    BROWSER with evaluator.mjs (same file runs in both places).
  * comparables come from D1 (see export_d1.py), not from the knn joblib.
"""
import argparse
import gzip
import json
import os

import joblib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "..", "models_full")
OUT = os.path.join(HERE, "..", "cf_artifacts")
DATA = os.path.join(HERE, "..", "data")


def rnd(x, p=6):
    if isinstance(x, (list, tuple)):
        return [rnd(v, p) for v in x]
    return round(float(x), p)


# --------------------------------------------------------------------------- #
def export_pipeline():
    pipe = joblib.load(os.path.join(MODELS, "feature_pipeline.joblib"))
    out = {
        "feature_names": pipe.feature_names_,
        "global_mean": rnd(pipe.global_mean_),
        "medians": {k: rnd(v) for k, v in pipe.medians_.items()},
        "lat_med": rnd(pipe.lat_med_), "lng_med": rnd(pipe.lng_med_),
        "types": pipe.types_,
        "suburb_te": {k: rnd(v) for k, v in pipe.suburb_te_.items()},
        "postcode_te": {k: rnd(v) for k, v in pipe.postcode_te_.items()},
        "region_te": {k: rnd(v) for k, v in pipe.region_te_.items()},
        "suburb_postcode": pipe.suburb_postcode_,
        "postcode_region": pipe.postcode_region_,
    }
    with open(os.path.join(OUT, "pipeline.json"), "w") as fh:
        json.dump(out, fh)
    return pipe


def export_linear():
    m = joblib.load(os.path.join(MODELS, "linear.joblib"))
    out = {
        "cols": m.cols_, "drop_dummy": m.drop_dummy,
        "mean": rnd(list(m.mean_)), "std": rnd(list(m.std_)),
        "beta": rnd(list(m.beta_), 8),
        "xtx_inv": [rnd(list(r), 10) for r in m.XtX_inv_],
        "s2": rnd(m.s2_, 8), "tcrit": rnd(m.tcrit_, 6),
    }
    with open(os.path.join(OUT, "linear.json"), "w") as fh:
        json.dump(out, fh)
    return m


def export_ebm():
    m = joblib.load(os.path.join(MODELS, "ebm.joblib"))
    e = m.ebm
    terms = []
    for tf, scores in zip(e.term_features_, e.term_scores_):
        level = len(tf) - 1
        cuts = []
        for f in tf:
            lv = e.bins_[f]
            c = lv[min(level, len(lv) - 1)]
            cuts.append(rnd(list(np.asarray(c, float)), 6))
        terms.append({
            "features": list(map(int, tf)),
            "cuts": cuts,
            "scores": rnd(np.asarray(scores, float).tolist(), 5),
        })
    out = {
        "intercept": rnd(float(e.intercept_), 6),
        "terms": terms,
        "conformal_lo": rnd(m.q_lo, 6), "conformal_hi": rnd(m.q_hi, 6),
    }
    with open(os.path.join(OUT, "ebm.json"), "w") as fh:
        json.dump(out, fh)
    return m


# ---- python reference scorers (must match evaluator.mjs exactly) ----------- #
def ebm_bin(v, cuts):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return 0
    return 1 + int(np.searchsorted(np.asarray(cuts), v, side="right"))


def ebm_score(row, art):
    s = art["intercept"]
    for t in art["terms"]:
        idx = [ebm_bin(row[f], c) for f, c in zip(t["features"], t["cuts"])]
        v = t["scores"]
        for i in idx:
            v = v[i]
        s += v
    return s


def linear_score(row_vec, art):
    z = [(v - m) / s for v, m, s in zip(row_vec, art["mean"], art["std"])]
    a = [1.0] + z
    yhat = sum(ai * bi for ai, bi in zip(a, art["beta"]))
    quad = sum(a[i] * sum(art["xtx_inv"][i][j] * a[j] for j in range(len(a)))
               for i in range(len(a)))
    se = (art["s2"] * (1.0 + quad)) ** 0.5
    return yhat, yhat - art["tcrit"] * se, yhat + art["tcrit"] * se


def parity_models():
    import pandas as pd
    b = joblib.load(os.path.join(MODELS, "_work", "arrays.joblib"))
    X = b["Xte"].head(400)
    feat = list(X.columns)

    ebm_m = joblib.load(os.path.join(MODELS, "ebm.joblib"))
    art = json.load(open(os.path.join(OUT, "ebm.json")))
    ref = ebm_m.ebm.predict(X.to_numpy(float))
    mine = np.array([ebm_score({i: r[i] for i in range(len(feat))}, art)
                     for r in X.to_numpy(float)])
    print(f"EBM parity: max |diff| log = {np.abs(ref - mine).max():.6f}")

    lin_m = joblib.load(os.path.join(MODELS, "linear.joblib"))
    lart = json.load(open(os.path.join(OUT, "linear.json")))
    p_ref, lo_ref, hi_ref = lin_m.predict_interval(X)
    cols = [feat.index(c) for c in lart["cols"]]
    outs = np.array([linear_score([r[c] for c in cols], lart)
                     for r in X.to_numpy(float)])
    print(f"Linear parity: max |diff| log = "
          f"{np.abs(np.log(p_ref) - outs[:, 0]).max():.6f}")


# --------------------------------------------------------------------------- #
def export_lgbm():
    m = joblib.load(os.path.join(MODELS, "lightgbm.joblib"))
    out = {"cqr_delta": rnd(m.cqr_delta, 6), "quantiles": {}}
    for q, booster in m.boosters.items():
        d = booster.dump_model()
        trees = []
        for t in d["tree_info"]:
            sf, th, lc, rc, dl, lv = [], [], [], [], [], []

            def walk(node):
                if "leaf_value" in node and "split_feature" not in node:
                    i = len(sf)
                    sf.append(-1); th.append(0.0); lc.append(-1); rc.append(-1)
                    dl.append(0); lv.append(round(node["leaf_value"], 7))
                    return i
                i = len(sf)
                sf.append(node["split_feature"]); th.append(round(node["threshold"], 7))
                lc.append(-2); rc.append(-2)
                dl.append(1 if node.get("default_left") else 0); lv.append(0.0)
                li = walk(node["left_child"]); ri = walk(node["right_child"])
                lc[i], rc[i] = li, ri
                return i

            walk(t["tree_structure"])
            trees.append({"sf": sf, "th": th, "lc": lc, "rc": rc, "dl": dl, "lv": lv})
        out["quantiles"][str(q)] = trees
        print(f"  q={q}: {len(trees)} trees")
    raw = json.dumps(out, separators=(",", ":"))
    p = os.path.join(OUT, "lightgbm.json")
    with open(p, "w") as fh:
        fh.write(raw)
    with gzip.open(p + ".gz", "wb", compresslevel=9) as fh:
        fh.write(raw.encode())
    print(f"lightgbm.json {os.path.getsize(p)/1e6:.1f} MB, "
          f".gz {os.path.getsize(p + '.gz')/1e6:.1f} MB")


def lgbm_predict_flat(row, trees):
    s = 0.0
    for t in trees:
        i = 0
        while t["sf"][i] >= 0:
            v = row[t["sf"][i]]
            if v is None or (isinstance(v, float) and np.isnan(v)):
                i = t["lc"][i] if t["dl"][i] else t["rc"][i]
            elif v <= t["th"][i]:
                i = t["lc"][i]
            else:
                i = t["rc"][i]
        s += t["lv"][i]
    return s


def parity_lgbm():
    b = joblib.load(os.path.join(MODELS, "_work", "arrays.joblib"))
    X = b["Xte"].head(150).to_numpy(float)
    m = joblib.load(os.path.join(MODELS, "lightgbm.joblib"))
    art = json.load(open(os.path.join(OUT, "lightgbm.json")))
    for q, booster in m.boosters.items():
        ref = booster.predict(X)
        mine = np.array([lgbm_predict_flat(list(r), art["quantiles"][str(q)]) for r in X])
        print(f"LGBM q={q} parity: max |diff| log = {np.abs(ref - mine).max():.6f}")


# --------------------------------------------------------------------------- #
def export_extras():
    import shutil
    shutil.copy(os.path.join(DATA, "price_index.json"), os.path.join(OUT, "price_index.json"))
    meta = json.load(open(os.path.join(MODELS, "metadata.json")))
    manifest = {
        "trained_at": meta["trained_at"], "n_train": meta["n_train"],
        "n_test": meta["n_test"], "index_base_month": meta.get("base_month") or meta.get("index_base_month"),
        "metrics": meta["metrics"],
        "files": {
            "worker": ["pipeline.json", "ebm.json", "linear.json", "price_index.json"],
            "browser": ["lightgbm.json.gz"],
            "d1": "run export_d1.py",
        },
    }
    with open(os.path.join(OUT, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    print("extras written")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["models", "lgbm", "extras"])
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if args.step == "models":
        export_pipeline(); export_linear(); export_ebm(); parity_models()
        for f in ["pipeline.json", "linear.json", "ebm.json"]:
            print(f"{f}: {os.path.getsize(os.path.join(OUT, f))/1024:.0f} KB")
    elif args.step == "lgbm":
        export_lgbm(); parity_lgbm()
    else:
        export_extras()


if __name__ == "__main__":
    main()
