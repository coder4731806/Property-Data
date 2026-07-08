"""
Dump raw inputs + expected model outputs so cf_artifacts/test_parity.mjs can
prove the JS evaluator matches the Python models end to end (including the
feature pipeline, TE fallbacks and interval math).
"""
import json
import os

import joblib
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "..", "models_full")
OUT = os.path.join(HERE, "..", "cf_artifacts")

b = joblib.load(os.path.join(MODELS, "_work", "arrays.joblib"))
test = b["test"].loc[:, ~b["test"].columns.duplicated()]
rows = test.sample(60, random_state=7).reset_index(drop=True)

pipe = joblib.load(os.path.join(MODELS, "feature_pipeline.joblib"))
lin = joblib.load(os.path.join(MODELS, "linear.joblib"))
lgbm = joblib.load(os.path.join(MODELS, "lightgbm.joblib"))
ebm = joblib.load(os.path.join(MODELS, "ebm.joblib"))

X = pipe.transform(rows)
cases = []
for i in range(len(rows)):
    r = rows.iloc[i]
    Xi = X.iloc[[i]]
    p_l, lo_l, hi_l = lin.predict_interval(Xi)
    p_g, lo_g, hi_g = lgbm.predict_interval(Xi)
    p_e, lo_e, hi_e = ebm.predict_interval(Xi)
    cases.append({
        "input": {
            "suburb": r["suburb"], "postcode": str(r["postcode"]),
            "region": r["region"], "property_type": r["property_type"],
            "bedrooms": None if pd.isna(r["bedrooms"]) else float(r["bedrooms"]),
            "bathrooms": None if pd.isna(r["bathrooms"]) else float(r["bathrooms"]),
            "car_spaces": None if pd.isna(r["car_spaces"]) else float(r["car_spaces"]),
            "land_size_m2": None if pd.isna(r["land_size_m2"]) else float(r["land_size_m2"]),
            "building_size_m2": None if pd.isna(r["building_size_m2"]) else float(r["building_size_m2"]),
            "lat": None if pd.isna(r["lat"]) else float(r["lat"]),
            "lng": None if pd.isna(r["lng"]) else float(r["lng"]),
        },
        "expected": {
            "linear": [float(p_l[0]), float(lo_l[0]), float(hi_l[0])],
            "lightgbm": [float(p_g[0]), float(lo_g[0]), float(hi_g[0])],
            "ebm": [float(p_e[0]), float(lo_e[0]), float(hi_e[0])],
        },
    })

with open(os.path.join(OUT, "parity_fixture.json"), "w") as fh:
    json.dump(cases, fh)
print(f"wrote {len(cases)} parity cases")
