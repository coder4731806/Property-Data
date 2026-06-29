"""
Build the model comparison table and diagnostic charts from saved test
predictions. Run after train.py.  Outputs -> ../charts/*.png, ../reports/comparison.md
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(HERE, "..", "reports")
CHARTS = os.path.join(HERE, "..", "charts")
MODELS = ["linear", "lightgbm", "knn", "ebm"]
LABELS = {"linear": "Linear", "lightgbm": "LightGBM", "knn": "KNN", "ebm": "EBM"}
COLORS = {"linear": "#9aa0a6", "lightgbm": "#1a73e8", "knn": "#34a853", "ebm": "#a142f4"}
REC = "lightgbm"


def main():
    os.makedirs(CHARTS, exist_ok=True)
    metrics = json.load(open(os.path.join(REPORTS, "metrics.json")))
    preds = pd.read_csv(os.path.join(REPORTS, "test_predictions.csv"))
    rows = pd.read_csv(os.path.join(REPORTS, "test_rows.csv"))
    actual = preds["actual"].to_numpy(float)

    # ---- comparison markdown table ----
    cols = [("mae", "MAE (AUD)", "${:,.0f}"), ("mape_pct", "MAPE %", "{:.1f}"),
            ("median_ape_pct", "Median APE %", "{:.1f}"), ("within_10pct", "Within 10% (%)", "{:.0f}"),
            ("within_20pct", "Within 20% (%)", "{:.0f}"), ("r2_log", "R2 (log)", "{:.3f}"),
            ("coverage_90_pct", "90% band coverage", "{:.1f}"),
            ("median_rel_interval_width_pct", "Median band width %", "{:.0f}")]
    lines = ["| Metric | " + " | ".join(LABELS[m] for m in MODELS) + " |",
             "|" + "---|" * (len(MODELS) + 1)]
    for key, label, fmt in cols:
        lines.append("| " + label + " | " + " | ".join(fmt.format(metrics[m][key]) for m in MODELS) + " |")
    with open(os.path.join(REPORTS, "comparison.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))

    # ---- chart 1: accuracy comparison (Median APE + within-10%) ----
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    x = np.arange(len(MODELS))
    ax[0].bar(x, [metrics[m]["median_ape_pct"] for m in MODELS], color=[COLORS[m] for m in MODELS])
    ax[0].set_xticks(x); ax[0].set_xticklabels([LABELS[m] for m in MODELS])
    ax[0].set_title("Median absolute % error (lower = better)"); ax[0].set_ylabel("%")
    for i, m in enumerate(MODELS):
        ax[0].text(i, metrics[m]["median_ape_pct"] + 0.1, f'{metrics[m]["median_ape_pct"]:.1f}', ha="center")
    ax[1].bar(x, [metrics[m]["within_10pct"] for m in MODELS], color=[COLORS[m] for m in MODELS])
    ax[1].set_xticks(x); ax[1].set_xticklabels([LABELS[m] for m in MODELS])
    ax[1].set_title("Predictions within 10% of sale price (higher = better)"); ax[1].set_ylabel("%")
    for i, m in enumerate(MODELS):
        ax[1].text(i, metrics[m]["within_10pct"] + 0.4, f'{metrics[m]["within_10pct"]:.0f}', ha="center")
    fig.tight_layout(); fig.savefig(os.path.join(CHARTS, "01_accuracy_comparison.png"), dpi=130); plt.close(fig)

    # ---- chart 2: interval coverage vs width ----
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    cov = [metrics[m]["coverage_90_pct"] for m in MODELS]
    wid = [metrics[m]["median_rel_interval_width_pct"] for m in MODELS]
    for m, c, w in zip(MODELS, cov, wid):
        ax.scatter(w, c, s=180, color=COLORS[m], zorder=3)
        ax.annotate(LABELS[m], (w, c), textcoords="offset points", xytext=(8, 6))
    ax.axhline(90, ls="--", color="#ea4335", label="90% target coverage")
    ax.set_xlabel("Median interval width (% of price)  -  narrower = better")
    ax.set_ylabel("Actual coverage of 90% band (%)")
    ax.set_title("Confidence interval quality")
    ax.legend(); fig.tight_layout()
    fig.savefig(os.path.join(CHARTS, "02_interval_quality.png"), dpi=130); plt.close(fig)

    # ---- chart 3: predicted vs actual (recommended) ----
    p = preds[f"{REC}_point"].to_numpy(float)
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    ax.scatter(actual, p, s=6, alpha=0.25, color=COLORS[REC])
    lim = [min(actual.min(), p.min()), np.percentile(actual, 99.5)]
    ax.plot(lim, lim, "k--", lw=1)
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("Actual sale price (AUD)"); ax.set_ylabel("Predicted (AUD)")
    ax.set_title(f"{LABELS[REC]}: predicted vs actual (test set)")
    ax.ticklabel_format(style="plain")
    fig.tight_layout(); fig.savefig(os.path.join(CHARTS, "03_pred_vs_actual.png"), dpi=130); plt.close(fig)

    # ---- chart 4: error by price band & region (recommended) ----
    ape = np.abs(p - actual) / actual * 100
    d = pd.DataFrame({"ape": ape, "price": actual, "region": rows["region"]})
    bands = pd.qcut(d["price"], 5)
    by_band = d.groupby(bands, observed=True)["ape"].median()
    by_region = d.groupby("region")["ape"].median().sort_values()
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    ax[0].bar(range(len(by_band)), by_band.values, color=COLORS[REC])
    ax[0].set_xticks(range(len(by_band)))
    ax[0].set_xticklabels([f"${int(iv.left/1000)}-{int(iv.right/1000)}k" for iv in by_band.index], rotation=30, ha="right")
    ax[0].set_title(f"{LABELS[REC]}: median error by price band"); ax[0].set_ylabel("Median APE %")
    ax[1].barh(range(len(by_region)), by_region.values, color=COLORS[REC])
    ax[1].set_yticks(range(len(by_region))); ax[1].set_yticklabels(by_region.index)
    ax[1].set_title(f"{LABELS[REC]}: median error by region"); ax[1].set_xlabel("Median APE %")
    fig.tight_layout(); fig.savefig(os.path.join(CHARTS, "04_error_breakdown.png"), dpi=130); plt.close(fig)

    print(f"\nWrote 4 charts -> {CHARTS}")


if __name__ == "__main__":
    main()
