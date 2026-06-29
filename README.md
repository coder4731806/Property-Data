# Queensland Property Listings & Price Models

This repository contains a snapshot of Queensland residential property
listings data and the price prediction models built on top of it. 

---

## What is in this repository

### Listing data (Excel files)

Sold property records for South-East Queensland, split by region. Each file covers one
geographic area and contains suburb, postcode, property type, bedrooms, bathrooms, car
spaces, land size, building size, sold price, and date sold.

| File | Coverage |
|---|---|
| `Brisbane_inner_city.xlsx` | Inner-city Brisbane suburbs |
| `brisbane-inner_north.xlsx` | Inner north Brisbane |
| `brisbane-inner_south.xlsx` | Inner south Brisbane |
| `brisbane-bayside_east.xlsx` | Eastern bayside suburbs |
| `brisbane-outer_north.xlsx` | Outer northern Brisbane corridor |
| `brisbane-outer_west_rural.xlsx` | Outer west and rural fringe |
| `brisbane-redlands_bayside.xlsx` | Redlands and bayside |
| `brisbane-south_west.xlsx` | South-west Brisbane |
| `goldcoast.xlsx` | Gold Coast |
| `sunshine_coast.xlsx` | Sunshine Coast |
| `logan_ipswich.xlsx` | Logan and Ipswich |
| `regional_qld.xlsx` | Regional Queensland |

The combined dataset is 28,000 sold records covering roughly June 2025 to June 2026. The
sample skews toward premium and coastal stock (inner Brisbane, Gold Coast, Sunshine Coast),
so the median sold price in the data (~$1.03M) is above the QLD-wide median. All prices
are in AUD.

### Price models (`price_model/`)

Four machine-learning models trained on the listing data above. Each takes the same inputs
a seller fills in when posting a listing — suburb, postcode, property type, bedrooms,
bathrooms, car spaces, and optional land and building size — and returns an expected price,
a 90% price band, a confidence score (0–100), and a set of nearby comparable sales.

See [`price_model/README.md`](price_model/README.md) for a full description of each model,
the performance table, and the API response shape.

### Utility scripts (`code/`)


### `suburbCategories.ts`

A TypeScript mapping of suburbs to their regional groupings, used by the Alethia platform.

---

## Running the price models

### Setup 

```bash
cd price_model
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```


### One-off estimate from the command line

```bash
python scripts/predict.py \
  --suburb PADDINGTON \
  --postcode 4064 \
  --property-type house \
  --bedrooms 3 \
  --bathrooms 2 \
  --car-spaces 1 \
  --land-size 405
```

### Model performance on the held-out test set (4,213 most recent sales)

| Metric | Linear | LightGBM | KNN | EBM |
|---|---|---|---|---|
| MAE (AUD) | $193,858 | $144,705 | $186,861 | $161,816 |
| Median error % | 12.0 | **8.6** | 11.1 | 10.2 |
| Within 10% of sale price | 42% | **56%** | 46% | 49% |
| 90% band coverage | 92.5% | 88.4% | 81.4% | 87.6% |

LightGBM is the recommended default. EBM is the fully interpretable runner-up — every
feature contribution is inspectable as a curve.

---

## Richer data and better models at Alethia

This repository is a released snapshot. The full, production-grade dataset and models live
inside **[Alethia](https://alethia.au)**.

### What Alethia is

Alethia is a real estate intelligence platform built for the Australian market. The name
comes from the Greek word for *transparency* — the goal is to put transparent, data-backed
property intelligence in front of buyers, sellers, and agents rather than hiding the
methodology behind a black-box number.

### What Alethia has that this repo does not

- **Historical depth back to 2007.** The data in this repo spans roughly one year.
  Alethia's database goes back nearly two decades of Queensland residential sales, giving
  the models far more signal across full market cycles — the GFC, the COVID boom, the
  rate-rise correction, and everything in between.

- **Broader coverage.** More property types, more regional areas, and richer attribute
  data than what is in the Excel files here.

- **More machine-learning models.** The production stack includes additional model
  families, ensemble methods, and a model selection layer that picks the right estimator
  per property type and suburb density.

- **Full transparency.** Every estimate on Alethia shows which model produced it, why the
  confidence score is what it is, what comparable sales were used, and how each feature
  contributed to the number (via EBM feature curves). There is no black box.

- **Regularly retrained.** The production models are retrained as new sales data comes in,
  so estimates track the current market rather than a fixed historical window.

If you want the full picture — deeper history, broader coverage, more models, and the
transparent explainability layer — visit **[alethia.au](https://alethia.au)**.

---

## Limitations

- The data here skews to premium and coastal stock. Estimates are most reliable in the
  $500K–$2M band and regress toward the mean for rare luxury properties above ~$2M.
- There are effectively no vacant-land-only sales in the dataset; land estimates should be
  treated as Low confidence.
- This is a statistical estimate, not a formal valuation or financial advice.
- Coverage on the test holdout sits just under 90% partly because prices continued rising
  across the test window — a normal temporal-drift effect that regular retraining addresses.
