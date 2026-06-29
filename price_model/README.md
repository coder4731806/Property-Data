# Alethia.au price model

Predicts the expected sale price of a Queensland residential property plus a 90%
price band and a confidence level, from the same fields a customer enters when
they post a listing (suburb, postcode, property type, bedrooms, bathrooms, car
spaces, and optional land and building size). Trained on 28,091 QLD sold records
collected for the period 23 Jun 2025 to 23 Jun 2026. All prices are AUD.

## What got built

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
you can show the comparable-sales view alongside the headline number. Charts are in
`charts/`.

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

Retrain from the Excel files (regenerates everything in `models/`, `charts/`,
`reports/`). This is the path you said you would run on your Mac, and it has no
time limit there:

```
python scripts/run_all.py
```

One-off estimate from the command line:

```
python scripts/predict.py --suburb PADDINGTON --postcode 4064 \
  --property-type house --bedrooms 3 --bathrooms 2 --car-spaces 1 --land-size 405
```

Start the local prediction API the platform calls:

```
uvicorn predict_service:app --host 127.0.0.1 --port 8008   # from scripts/
```

Then `POST /estimate` with a JSON body of the property details returns the expected
price, band, confidence and comparables. `GET /health` reports which models loaded.

## Wiring it to the Cloudflare Worker

The Worker cannot run Python, so the model runs as this separate service and the
Worker calls it over HTTP. In development, run `wrangler dev` and the service on
the same machine and point the Worker at `http://127.0.0.1:8008`. In production,
host the service (a small container on Fly.io, Render, or a box of your own, or a
Cloudflare Tunnel back to a machine that runs it) and store its URL as a Worker
secret. The Worker side is a short fetch, for example a Hono route:

```ts
// apps/api/src/routes/estimate.ts (example)
import { Hono } from "hono";
export const estimate = new Hono<{ Bindings: Env }>();

estimate.post("/estimate", async (c) => {
  const body = await c.req.json(); // { suburb, postcode, property_type, bedrooms, ... }
  const res = await fetch(`${c.env.PRICE_MODEL_URL}/estimate`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) return c.json({ error: "price model unavailable" }, 502);
  return c.json(await res.json());
});
```

`PRICE_MODEL_URL` is set with `wrangler secret put PRICE_MODEL_URL`. I have not
touched the Alethia repo; this snippet is a starting point for when you want to add
the route.

## Response shape

```json
{
  "expected_price": 1843000,
  "price_low": 1267000,
  "price_high": 2178000,
  "confidence_score": 80,
  "confidence_label": "High",
  "confidence_factors": {"comparable_sales_in_suburb": 39, "band_width_pct": 49.4},
  "recommended_model": "lightgbm",
  "models": {"linear": {...}, "lightgbm": {...}, "knn": {...}, "ebm": {...}},
  "comparable_sales": [{"address": "...", "bedrooms": 3, "sold_price": 1820000, "date_sold": "2026-01-22"}, ...],
  "n_comparables_considered": 15
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
  data/      clean.csv, suburb_centroids.csv, data_quality.json
  models/    feature_pipeline.joblib + linear/lightgbm/knn/ebm .joblib + metadata.json
  scripts/   common, features, models_lib, data_prep, gnaf_centroids,
             train, evaluate, predict, predict_service, run_all
  reports/   metrics.json, comparison.md, test_predictions.csv
  charts/    accuracy, interval quality, predicted vs actual, error breakdown
```
