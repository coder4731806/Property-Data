"""
Feature pipeline shared by training and inference.

Key design choices
------------------
* Target is log(sold_price); all models predict in log space and we exp() back.
* Locality is encoded with HIERARCHICAL shrinkage: a suburb's price level is
  smoothed toward its postcode, the postcode toward its region, the region
  toward the global mean. Sparse suburbs therefore "borrow strength" from
  their neighbours instead of overfitting on a handful of sales -- this is the
  statistically correct version of "nearby suburbs have related prices".
* Suburb centroid lat/lng are included as raw geographic features (and power
  the KNN comparable-sales model).
* Missing land/building size -> median imputation + an explicit missing flag.

The fitted pipeline is pickled so inference applies the identical transform.
"""
import numpy as np
import pandas as pd

from common import (CANON_TYPES, NUMERIC_FEATURES)

SMOOTH_REGION = 50.0
SMOOTH_POSTCODE = 25.0
SMOOTH_SUBURB = 12.0


class FeaturePipeline:
    def __init__(self):
        self.fitted = False

    def fit(self, df, y_log):
        d = df.copy()
        d["_y"] = y_log.values
        self.global_mean_ = float(d["_y"].mean())

        # ---- hierarchical target encoding (region -> postcode -> suburb) ----
        reg = d.groupby("region")["_y"].agg(["mean", "count"])
        reg["te"] = (reg["count"] * reg["mean"] + SMOOTH_REGION * self.global_mean_) / (reg["count"] + SMOOTH_REGION)
        self.region_te_ = reg["te"].to_dict()

        # each postcode's parent = region_te of its modal region
        pc_region = d.groupby("postcode")["region"].agg(lambda s: s.mode().iloc[0])
        self.postcode_region_ = pc_region.to_dict()
        pc = d.groupby("postcode")["_y"].agg(["mean", "count"])
        pc["parent"] = pc.index.map(lambda c: self.region_te_.get(self.postcode_region_.get(c), self.global_mean_))
        pc["te"] = (pc["count"] * pc["mean"] + SMOOTH_POSTCODE * pc["parent"]) / (pc["count"] + SMOOTH_POSTCODE)
        self.postcode_te_ = pc["te"].to_dict()

        # each suburb's parent = postcode_te of its modal postcode
        sub_pc = d.groupby("suburb")["postcode"].agg(lambda s: s.mode().iloc[0])
        self.suburb_postcode_ = sub_pc.to_dict()
        sub = d.groupby("suburb")["_y"].agg(["mean", "count"])
        sub["parent"] = sub.index.map(lambda s: self.postcode_te_.get(self.suburb_postcode_.get(s), self.global_mean_))
        sub["te"] = (sub["count"] * sub["mean"] + SMOOTH_SUBURB * sub["parent"]) / (sub["count"] + SMOOTH_SUBURB)
        self.suburb_te_ = sub["te"].to_dict()

        # ---- numeric imputation medians ----
        self.medians_ = {c: float(np.nanmedian(pd.to_numeric(d[c], errors="coerce"))) for c in NUMERIC_FEATURES}
        # suburb centroid fallback
        self.lat_med_, self.lng_med_ = float(d["lat"].median()), float(d["lng"].median())

        self.types_ = CANON_TYPES
        self.feature_names_ = (
            NUMERIC_FEATURES
            + ["land_size_missing", "building_size_missing"]
            + ["lat", "lng"]
            + ["suburb_te", "postcode_te", "region_te"]
            + [f"type_{t}" for t in self.types_]
        )
        self.fitted = True
        return self

    # ---- encoders with hierarchical fallback ----
    def _suburb_te(self, suburb, postcode, region):
        if suburb in self.suburb_te_:
            return self.suburb_te_[suburb]
        return self._postcode_te(postcode, region)

    def _postcode_te(self, postcode, region):
        if postcode in self.postcode_te_:
            return self.postcode_te_[postcode]
        return self._region_te(region)

    def _region_te(self, region):
        return self.region_te_.get(region, self.global_mean_)

    def transform(self, df):
        d = df.copy()
        X = pd.DataFrame(index=d.index)

        land = pd.to_numeric(d.get("land_size_m2"), errors="coerce")
        bld = pd.to_numeric(d.get("building_size_m2"), errors="coerce")
        X["land_size_missing"] = land.isna().astype(float)
        X["building_size_missing"] = bld.isna().astype(float)

        for c in NUMERIC_FEATURES:
            col = pd.to_numeric(d.get(c), errors="coerce")
            X[c] = col.fillna(self.medians_[c])

        X["lat"] = pd.to_numeric(d.get("lat"), errors="coerce").fillna(self.lat_med_)
        X["lng"] = pd.to_numeric(d.get("lng"), errors="coerce").fillna(self.lng_med_)

        reg = d["region"].astype(str) if "region" in d else pd.Series(["__none__"] * len(d), index=d.index)
        pc = d["postcode"].astype(str) if "postcode" in d else pd.Series([""] * len(d), index=d.index)
        sub = d["suburb"].astype(str) if "suburb" in d else pd.Series([""] * len(d), index=d.index)
        X["suburb_te"] = [self._suburb_te(s, p, r) for s, p, r in zip(sub, pc, reg)]
        X["postcode_te"] = [self._postcode_te(p, r) for p, r in zip(pc, reg)]
        X["region_te"] = [self._region_te(r) for r in reg]

        ptype = d["property_type"].astype(str)
        for t in self.types_:
            X[f"type_{t}"] = (ptype == t).astype(float)

        return X[self.feature_names_]


def time_split(df, test_frac=0.15):
    """Temporal holdout: newest `test_frac` of dated rows -> test. Undated -> train."""
    d = df.copy()
    dated = d[d["date_sold"].notna()].sort_values("date_sold")
    undated = d[d["date_sold"].isna()]
    n_test = int(len(dated) * test_frac)
    test = dated.iloc[len(dated) - n_test:]
    train = pd.concat([undated, dated.iloc[:len(dated) - n_test]])
    cutoff = dated["date_sold"].iloc[len(dated) - n_test] if n_test else None
    return train.reset_index(drop=True), test.reset_index(drop=True), cutoff
