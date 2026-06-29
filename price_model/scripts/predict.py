"""
Inference interface for the Alethia price models.

A customer supplies the same fields they enter when posting a listing; the
predictor geocodes the suburb, builds features, and returns an expected price,
a 90% price band, a confidence score, and (for the comparable-sales view) the
actual nearby sold properties the estimate is based on.

Programmatic use:
    from predict import PricePredictor
    pp = PricePredictor()
    pp.estimate({"suburb": "PADDINGTON", "postcode": "4064",
                 "property_type": "house", "bedrooms": 3, "bathrooms": 2,
                 "car_spaces": 1, "land_size_m2": 405})

CLI:
    python predict.py --suburb PADDINGTON --postcode 4064 --property-type house \
        --bedrooms 3 --bathrooms 2 --car-spaces 1 --land-size 405
    echo '{"suburb":"ROBINA","postcode":"4226","property_type":"apartment","bedrooms":2,"bathrooms":2,"car_spaces":1}' | python predict.py --json
"""
import argparse
import json
import os
import sys

import joblib
import numpy as np
import pandas as pd

from common import canonical_platform_type, normalize_suburb

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(HERE, "..", "models")
DATA_DIR = os.path.join(HERE, "..", "data")
MODEL_FILES = {"linear": "linear.joblib", "lightgbm": "lightgbm.joblib",
               "knn": "knn.joblib", "ebm": "ebm.joblib"}
RECOMMENDED = "lightgbm"
KNN_INPUT_COLS = ["address", "suburb", "property_type", "lat", "lng", "bedrooms",
                  "bathrooms", "car_spaces", "land_size_m2", "building_size_m2",
                  "sold_price", "date_sold"]


class PricePredictor:
    def __init__(self, models_dir=MODELS_DIR, data_dir=DATA_DIR):
        self.pipe = joblib.load(os.path.join(models_dir, "feature_pipeline.joblib"))
        self.models = {k: joblib.load(os.path.join(models_dir, f))
                       for k, f in MODEL_FILES.items() if os.path.exists(os.path.join(models_dir, f))}
        self.meta = json.load(open(os.path.join(models_dir, "metadata.json")))

        # geocoding: suburb(+postcode) -> centroid
        cen = pd.read_csv(os.path.join(data_dir, "suburb_centroids.csv"), dtype={"postcode": str})
        self.cen_sp = {(r.suburb, r.postcode): (r.lat, r.lng)
                       for r in cen[cen.level == "suburb_postcode"].itertuples()}
        self.cen_s = {r.suburb: (r.lat, r.lng) for r in cen[cen.level == "suburb"].itertuples()}

        # locality + comparable-density lookups from the clean training table
        clean = pd.read_csv(os.path.join(data_dir, "clean.csv"), dtype={"postcode": str})
        self.suburb_region = clean.groupby("suburb")["region"].agg(lambda s: s.mode().iloc[0]).to_dict()
        self.postcode_region = clean.groupby("postcode")["region"].agg(lambda s: s.mode().iloc[0]).to_dict()
        self.suburb_type_count = clean.groupby(["suburb", "property_type"]).size().to_dict()
        self.lat_med, self.lng_med = float(clean["lat"].median()), float(clean["lng"].median())

    # ---- build a single-row feature frame from raw customer input -----------
    def _row(self, d):
        suburb = normalize_suburb(d.get("suburb"))
        postcode = str(d.get("postcode") or "").strip()
        ptype = canonical_platform_type(d.get("property_type"))
        lat, lng = self._geocode(suburb, postcode)
        region = (self.suburb_region.get(suburb)
                  or self.postcode_region.get(postcode) or "regional_qld")
        return pd.DataFrame([{
            "address": d.get("address", ""), "suburb": suburb, "postcode": postcode,
            "region": region, "property_type": ptype,
            "bedrooms": _num(d.get("bedrooms")), "bathrooms": _num(d.get("bathrooms")),
            "car_spaces": _num(d.get("car_spaces")),
            "land_size_m2": _num(d.get("land_size_m2")), "building_size_m2": _num(d.get("building_size_m2")),
            "lat": lat, "lng": lng, "sold_price": np.nan, "date_sold": pd.NaT,
        }]), suburb, ptype

    def _geocode(self, suburb, postcode):
        if (suburb, postcode) in self.cen_sp:
            return self.cen_sp[(suburb, postcode)]
        if suburb in self.cen_s:
            return self.cen_s[suburb]
        return self.lat_med, self.lng_med

    # ---- single model prediction -------------------------------------------
    def predict_model(self, details, model=RECOMMENDED):
        row, suburb, ptype = self._row(details)
        if model == "knn":
            p, lo, hi = self.models["knn"].predict_interval(None, df=row[KNN_INPUT_COLS])
        else:
            X = self.pipe.transform(row)
            p, lo, hi = self.models[model].predict_interval(X)
        return {"model": model, "point": float(p[0]), "low": float(lo[0]), "high": float(hi[0])}

    # ---- full estimate: recommended price + band + confidence + comparables --
    def estimate(self, details):
        row, suburb, ptype = self._row(details)
        X = self.pipe.transform(row)

        per_model = {}
        for name, mdl in self.models.items():
            if name == "knn":
                p, lo, hi = mdl.predict_interval(None, df=row[KNN_INPUT_COLS])
            else:
                p, lo, hi = mdl.predict_interval(X)
            per_model[name] = {"point": float(p[0]), "low": float(lo[0]), "high": float(hi[0])}

        rec = per_model[RECOMMENDED]
        comparables, n_comp = ([], 0)
        if "knn" in self.models:
            comparables, n_comp = self.models["knn"].comparables(row[KNN_INPUT_COLS], n=5)

        conf = self._confidence(rec, suburb, ptype)
        return {
            "expected_price": round(rec["point"], -3),
            "price_low": round(rec["low"], -3),
            "price_high": round(rec["high"], -3),
            "confidence_score": conf["score"],
            "confidence_label": conf["label"],
            "confidence_factors": conf["factors"],
            "recommended_model": RECOMMENDED,
            "models": per_model,
            "comparable_sales": comparables,
            "n_comparables_considered": n_comp,
            "resolved": {"suburb": suburb, "property_type": ptype,
                         "region": row["region"].iloc[0],
                         "lat": float(row["lat"].iloc[0]), "lng": float(row["lng"].iloc[0])},
        }

    def _confidence(self, rec, suburb, ptype):
        width_rel = (rec["high"] - rec["low"]) / max(rec["point"], 1)
        n_same = self.suburb_type_count.get((suburb, ptype), 0)
        data_score = min(1.0, n_same / 40.0)                       # >=40 same-type sales = full
        precision_score = float(np.clip(1 - (width_rel - 0.20) / 0.80, 0, 1))  # band <=20% = full
        score = int(round(100 * (0.5 * data_score + 0.5 * precision_score)))
        label = "High" if score >= 70 else "Medium" if score >= 45 else "Low"
        return {"score": score, "label": label,
                "factors": {"comparable_sales_in_suburb": int(n_same),
                            "band_width_pct": round(width_rel * 100, 1)}}


def _num(v):
    try:
        if v is None or v == "":
            return np.nan
        return float(v)
    except (ValueError, TypeError):
        return np.nan


def _cli():
    ap = argparse.ArgumentParser(description="Estimate a QLD property price.")
    ap.add_argument("--json", action="store_true", help="read a JSON property dict from stdin")
    ap.add_argument("--suburb"); ap.add_argument("--postcode")
    ap.add_argument("--property-type", dest="property_type")
    ap.add_argument("--bedrooms", type=float); ap.add_argument("--bathrooms", type=float)
    ap.add_argument("--car-spaces", dest="car_spaces", type=float)
    ap.add_argument("--land-size", dest="land_size_m2", type=float)
    ap.add_argument("--building-size", dest="building_size_m2", type=float)
    ap.add_argument("--model", choices=list(MODEL_FILES), help="single-model output only")
    args = ap.parse_args()

    if args.json:
        details = json.load(sys.stdin)
    else:
        details = {k: v for k, v in vars(args).items()
                   if k not in ("json", "model") and v is not None}

    pp = PricePredictor()
    out = pp.predict_model(details, args.model) if args.model else pp.estimate(details)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    _cli()
