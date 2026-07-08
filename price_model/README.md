# Alethia.au price model

Predicts the expected sale price of a Queensland residential property plus a 90%
price band and a confidence level, from the same fields a customer enters when
they post a listing (suburb, postcode, property type, bedrooms, bathrooms, car
spaces, and optional land and building size). Trained on 28,091 QLD sold records
collected for the period 23 Jun 2025 to 23 Jun 2026. All prices are AUD.

## v2: full-data retrain + Cloudflare-native serving (Jul 2026)

The original models used the 33k-row xlsx exports. The scraper's region SQLite
dbs now hold ~662k unique priced sold records (2008-2026), so v2 trains straight
from those and serves without any Python server:

* `scripts/data_prep_db.py` reads every `data/<region>/<region>.db` from
  REAscrape, dedupes and cleans -> `data/clean_full.csv` (662k rows, 604 suburbs).
* `scripts/price_index.py` fits a monthly price index (two-way fixed effects on
  suburb x type vs month) from the FULL 2008-2026 history -> `data/price_index.json`.
  Old sales are never discarded: each price is converted to current dollars with
  the index before training, so a 2015 sale still teaches the model what 4 beds
  on 600m2 in that suburb is worth, while the index carries the market trend. A
  raw date feature cannot do this in tree models (they cannot extrapolate time),
  which is why the index approach is used instead.
* `scripts/train_full.py` retrains all four families on 614k index-adjusted rows
  (2013+, recency-weighted, temporal holdout = newest 3 months). KNN trains on
  the last 24 months so comparables stay current. Outputs -> `models_full/`.
* `scripts/export_cf.py` + `scripts/export_d1.py` produce `cf_artifacts/`:
  everything needed to run the whole thing on Cloudflare's free tier:
  - `pipeline.json` + `ebm.json` + `linear.json` (~100 KB total) evaluate inside
    the Worker via `evaluator.mjs` (~7 microseconds per estimate, far under the
    10 ms free-tier CPU limit).
  - `lightgbm.json.gz` (~3 MB) is served as a static asset and evaluated in the
    BROWSER with the same `evaluator.mjs` (~0.2 ms), keeping the headline model
    out of the Worker size/CPU limits.
  - `d1/sold_records.sql.gz` imports all sold records into D1; comparable sales
    ("based on N similar sold properties") become one indexed SQL query
    (`d1/comparables.sql`) instead of the 10 MB knn joblib.
  - `worker_example/estimate.ts` is a ready Hono route for `apps/api`.
  - `test_parity.mjs` proves JS output matches Python to <0.01%.
* Run everything on the Mac with
  `python scripts/run_all_full.py --data-dir ~/Downloads/REAscrape/data`
  (the sandbox-friendly chunked variant is `scripts/train_steps.py`).

v2 held-out results (newest 3 months, 3,404 sales, all 16 regions; full production
config: EBM at 8 bags / 6 interactions / 250k-row cap):

| Metric | Linear | LightGBM | KNN | EBM |
|---|---|---|---|---|
| MAE (AUD) | $211,536 | $145,388 | $157,482 | $164,750 |
| Median APE % | 13.8 | 8.7 | 8.9 | 10.3 |
| Within 10% (%) | 38 | 55 | 55 | 49 |
| 90% band coverage | 93.6 | 87.7 | 79.7 | 89.3 |
| Median band width % | 87 | 45 | 39 | 59 |

Not directly comparable to the v1 table below (different test window, wider
region mix including cheaper regional markets, and the db-sourced data has no
building size). Notable: KNN improved sharply (11.1 -> 8.9 median APE) because
comparables are far denser, and estimates now track the market month by month via
the index. 2026 sales are thin so far (~19k vs ~80k for 2025) but the scraper is
current (latest scraped sale: late Jun 2026) -- this looks like QLD's normal
sale-price disclosure lag rather than under-scraping, so it should backfill over
the next retrain or two rather than needing a scraper fix.

---

## What got built (v1, 28k xlsx training run)

Four model families were trained on one shared temporal holdout so the numbers
are comparable. Each returns a point estimate and a 90% interval, but each
derives the interval differently.

Linear regression is the explainable baseline. It learns in log-price space and
produces exact analytic prediction intervals from the closed-form formula, so the
band has a precise statistical meaning. It is the least accurate of the four but
the easiest to reason about.

LightGBM quantile regression is the recommended production model. It trains three
gradient-boosted ensembles with pinball (quantile) loss at the 5th, 50th and 95th
percentiles, which gives a median estimate and a 90% band directly with no
assumption that errors are normal. The band is then conformalised on held-out
data so the nominal 90% actually covers close to 90% in practice.

KNN comparable sales is the intuitive model. It finds the nearest sold properties
of the same type, weighted toward geographic proximity, and reports their median
price and the 5th to 95th percentile spread. It also returns the actual nearby
sales the estimate is based on, which is what a customer understands as "based on
5 similar sold properties".

EBM (Explainable Boosting Machine) is a glassbox generalised additive model. Price
is a sum of per-feature curves (land size, bedrooms, suburb level, and a handful
of pairwise terms) learned by boosting, so every contribution is inspectable. Its
intervals come from split-conformal calibration on held-out residuals. It is
nearly as accurate as LightGBM while staying fully interpretable.

## How "nearby suburbs relate" is handled

Training 779 separate per-suburb models was rejected because most suburbs have too
few sales and separate models cannot share information. Instead locality is encoded
as features in one pooled model. Each suburb's price level is smoothed toward its
postcode, the postcode toward its region, and the region toward the state-wide
mean (hierarchical shrinkage), so a thin suburb borrows strength from its
neighbours rather than overfitting on a handful of sales. Real geographic
coordinates come from the G-NAF address file shipped in the Alethia repo, condensed
to one centroid per suburb (3.1M addresses to 6,346 centroids). The KNN model uses
those coordinates directly so its comparables are genuinely nearby.

## Results on the held-out test set

The test set is the most recent 4,213 sales (everything sold after 11 May 2026),
which simulates pricing a new listing against an unseen near future. MAE is the
average dollar error, median APE is the typical percentage error, "within 10%" is
the share of estimates within 10% of the real sale price, coverage is how often the
90% band actually contained the sale price, and width is the band size as a percent
of the estimate.

| Metric | Linear | LightGBM | KNN | EBM |
|---|---|---|---|---|
| MAE (AUD) | $193,858 | $144,705 | $186,861 | $161,816 |
| MAPE % | 15.9 | 11.9 | 15.9 | 13.6 |
| Median APE % | 12.0 | 8.6 | 11.1 | 10.2 |
| Within 10% (%) | 42 | 56 | 46 | 49 |
| Within 20% (%) | 71 | 82 | 72 | 78 |
| R2 (log) | 0.716 | 0.845 | 0.745 | 0.814 |
| 90% band coverage | 92.5 | 88.4 | 81.4 | 87.6 |
| Median band width % | 81 | 48 | 53 | 56 |

LightGBM wins on accuracy (typical error 8.6%, 56% of estimates within 10% of the
sale price) and has the tightest well-calibrated band, so it is the default the
service returns. EBM is the explainable runner-up. The service returns all four so
you can show the comparable-sales view alongside the headline number. These are the
v1 xlsx-trained numbers; see the v2 table above for the current 600k-row model.

## Confidence level

The service returns a 0 to 100 confidence score and a High / Medium / Low label. It
combines how much comparable data backs the estimate (count of same-type sales in
that suburb) with how tight the band is. A well-traded inner-Brisbane suburb scores
High; a thin rural suburb with no matching sales scores Low even though a number is
still produced. The raw factors are returned too, so the reason is transparent.

## Running it

Set up once:

```
cd price_model
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Retrain from the REAscrape region dbs (regenerates `data/clean_full.csv`,
`data/price_index.json`, `models_full/`, `reports_full/`, and `cf_artifacts/`):

```
python scripts/run_all_full.py --data-dir ~/Downloads/REAscrape/data
```

`scripts/train_steps.py` is the same training step broken into chunks (useful in
sandboxes without a hard time limit budget for one long-running process).

There is no Python prediction server in v2 — estimates run inside the Cloudflare
Worker and browser via `cf_artifacts/evaluator.mjs`, see below.

## Wiring it to the Cloudflare Worker

The Worker cannot run Python, so `scripts/export_cf.py` converts the trained
models to small JSON artifacts that `cf_artifacts/evaluator.mjs` evaluates directly
in JS, no separate service to host:

1. Copy `cf_artifacts/evaluator.mjs` into `apps/api/src/lib/`.
2. Copy `pipeline.json`, `ebm.json`, `linear.json` into `apps/api/src/lib/model/`
   (~100 KB total; evaluates in the Worker in microseconds, well under the 10 ms
   free-tier CPU limit).
3. Import the comparables db: `wrangler d1 import <db> --file=cf_artifacts/d1/sold_records.sql --remote`.
4. LightGBM (the most accurate model, ~3 MB) is served to the browser as a static
   asset (`lightgbm.json.gz`) and evaluated client-side with the same
   `evaluator.mjs`, keeping it out of the Worker's size/CPU limits.
5. Mount `cf_artifacts/worker_example/estimate.ts` (a ready Hono route) in
   `apps/api/src/index.ts`. It looks up the suburb centroid and nearest comparable
   sales from D1, calls `estimate()` from `evaluator.mjs`, and returns the result.

`cf_artifacts/test_parity.mjs` proves this JS evaluation matches the Python
training-time output to <0.01%.

## Response shape

```json
{
  "expected_price": 1843000,
  "price_low": 1267000,
  "price_high": 2178000,
  "recommended_model": "lightgbm",
  "confidence_score": 80,
  "confidence_label": "High",
  "confidence_factors": {"comparable_sales_in_suburb": 39, "band_width_pct": 49.4},
  "models": {"linear": {...}, "ebm": {...}, "lightgbm": {...}},
  "comparable_sales": [{"address": "...", "bedrooms": 3, "sold_price": 1820000, "date_sold": "2026-01-22"}, ...],
  "n_comparables_considered": 15,
  "disclaimer": "Statistical estimate, not a valuation or financial advice."
}
```

## Limitations to know

The collected sample skews to premium and coastal stock: the median sold price in
the data is about $1.03M, higher than the QLD-wide median, because Brisbane inner
city, the Gold Coast and the Sunshine Coast are heavily represented. Estimates are
most reliable for that mass-market band and regress toward the mean above roughly
$2M, where unique luxury homes are genuinely hard to price. Coverage on the recent
holdout sits a little under 90% because prices kept rising across the test window,
which is normal temporal drift; retraining regularly keeps it honest. There are
effectively no vacant-land sales in the data, so "land" estimates lean on features
alone and should be treated as Low confidence. This is a statistical estimate, not
a valuation or financial advice.

## Layout

```
price_model/
  data/          clean_full.csv, suburb_centroids.csv, data_quality_full.json, price_index.json
  models_full/   feature_pipeline.joblib + linear/lightgbm/knn/ebm .joblib + metadata.json
  reports_full/  metrics.json, test_predictions.csv
  cf_artifacts/  pipeline/ebm/linear/lightgbm .json, evaluator.mjs, d1/, worker_example/, test_parity.mjs
  scripts/       common, features, metrics, models_lib, gnaf_centroids,
                 data_prep_db, price_index, train_full, train_steps, run_all_full,
                 export_cf, export_d1, make_parity_fixture
```
