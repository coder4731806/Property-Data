"""
Model wrappers. Each exposes .predict_interval(X) -> (point, low, high) in
DOLLAR space for a 90% band. Defined as importable classes so the joblib
pickles created in training load identically at inference time.

All models learn in log(price) space; intervals are exponentiated back, which
makes them multiplicative (wider in dollars for expensive homes) -- the right
shape for property prices.
"""
import numpy as np
import pandas as pd
from scipy import stats

ALPHA = 0.10          # 90% interval
Q_LO, Q_HI = 0.05, 0.95


# --------------------------------------------------------------------------- #
# 1. Linear regression with EXACT analytic prediction intervals
# --------------------------------------------------------------------------- #
class LinearPI:
    """OLS in log space with closed-form prediction intervals.

    PI for a new x: yhat +/- t(1-a/2, dof) * sqrt(s2 * (1 + x (X'X)^-1 x')).
    Stored as numpy arrays so no statsmodels dependency at inference.
    """

    def __init__(self, drop_dummy="type_house"):
        self.drop_dummy = drop_dummy

    def _design(self, X):
        cols = [c for c in X.columns if c != self.drop_dummy]
        Z = X[cols].to_numpy(dtype=float)
        Z = (Z - self.mean_) / self.std_
        return np.column_stack([np.ones(len(Z)), Z]), cols

    def fit(self, X, y_log):
        cols = [c for c in X.columns if c != self.drop_dummy]
        Z = X[cols].to_numpy(dtype=float)
        self.mean_ = Z.mean(axis=0)
        self.std_ = Z.std(axis=0)
        self.std_[self.std_ == 0] = 1.0
        self.cols_ = cols
        A, _ = self._design(X)
        y = y_log.to_numpy(dtype=float)
        self.XtX_inv_ = np.linalg.pinv(A.T @ A)
        self.beta_ = self.XtX_inv_ @ A.T @ y
        resid = y - A @ self.beta_
        n, p = A.shape
        self.dof_ = max(n - p, 1)
        self.s2_ = float(resid @ resid) / self.dof_
        self.tcrit_ = float(stats.t.ppf(1 - ALPHA / 2, self.dof_))
        return self

    def predict_interval(self, X):
        A, _ = self._design(X)
        yhat = A @ self.beta_
        quad = np.einsum("ij,jk,ik->i", A, self.XtX_inv_, A)
        se = np.sqrt(self.s2_ * (1.0 + quad))
        lo, hi = yhat - self.tcrit_ * se, yhat + self.tcrit_ * se
        return np.exp(yhat), np.exp(lo), np.exp(hi)


# --------------------------------------------------------------------------- #
# 2. LightGBM quantile regression (native 5/50/95 band) -- recommended
# --------------------------------------------------------------------------- #
class LgbmQuantile:
    def __init__(self, boosters, cqr_delta=0.0):
        # dict {0.05: booster, 0.5: booster, 0.95: booster}
        self.boosters = boosters
        # Conformalized Quantile Regression widening (log space) so the nominal
        # 90% band achieves ~90% empirical coverage on held-out data.
        self.cqr_delta = float(cqr_delta)

    def _log_preds(self, X):
        Xv = X.to_numpy(dtype=float) if isinstance(X, pd.DataFrame) else np.asarray(X, float)
        lo = self.boosters[Q_LO].predict(Xv)
        mid = self.boosters[0.5].predict(Xv)
        hi = self.boosters[Q_HI].predict(Xv)
        stacked = np.sort(np.column_stack([lo, mid, hi]), axis=1)  # non-crossing
        return stacked[:, 0], stacked[:, 1], stacked[:, 2]

    def predict_interval(self, X):
        lo, mid, hi = self._log_preds(X)
        return np.exp(mid), np.exp(lo - self.cqr_delta), np.exp(hi + self.cqr_delta)


# --------------------------------------------------------------------------- #
# 3. Explainable Boosting Machine + split-conformal intervals
# --------------------------------------------------------------------------- #
class EbmConformal:
    def __init__(self, ebm, q_lo, q_hi):
        self.ebm = ebm
        self.q_lo = q_lo      # signed residual quantiles (log space) from calibration
        self.q_hi = q_hi

    def predict_interval(self, X):
        Xv = X.to_numpy(dtype=float) if isinstance(X, pd.DataFrame) else np.asarray(X, float)
        yhat = self.ebm.predict(Xv)
        return np.exp(yhat), np.exp(yhat + self.q_lo), np.exp(yhat + self.q_hi)


# --------------------------------------------------------------------------- #
# 4. KNN "comparable sales"
# --------------------------------------------------------------------------- #
class KnnComparables:
    """Finds the nearest sold properties (same type, geographically close, similar
    size/beds) and reports their median price and empirical 5-95 spread.

    Returns real comparable sales for explainability ("based on N similar sold
    properties").
    """

    GEO_WEIGHT = 2.5          # up-weight location in the distance metric
    K = 15
    MIN_TYPE = 60             # if a type has fewer rows, fall back to all types

    def __init__(self):
        from sklearn.neighbors import NearestNeighbors  # noqa
        self._NN = NearestNeighbors

    def _vec(self, df):
        d = df
        land = np.log1p(pd.to_numeric(d.get("land_size_m2"), errors="coerce").fillna(self.land_med_))
        bld = np.log1p(pd.to_numeric(d.get("building_size_m2"), errors="coerce").fillna(self.bld_med_))
        feats = np.column_stack([
            pd.to_numeric(d["lat"], errors="coerce").fillna(self.lat_med_),
            pd.to_numeric(d["lng"], errors="coerce").fillna(self.lng_med_),
            pd.to_numeric(d["bedrooms"], errors="coerce").fillna(self.bed_med_),
            pd.to_numeric(d["bathrooms"], errors="coerce").fillna(self.bath_med_),
            pd.to_numeric(d["car_spaces"], errors="coerce").fillna(self.car_med_),
            land, bld,
        ])
        Z = (feats - self.mu_) / self.sd_
        Z[:, 0:2] *= self.GEO_WEIGHT          # prioritise geography
        return Z

    def fit(self, df, y_log):
        d = df.reset_index(drop=True).copy()

        def _med(col):
            v = float(pd.to_numeric(d[col], errors="coerce").median())
            return 0.0 if np.isnan(v) else v   # all-missing column -> neutral 0

        self.land_med_ = _med("land_size_m2")
        self.bld_med_ = _med("building_size_m2")
        self.lat_med_ = float(d["lat"].median()); self.lng_med_ = float(d["lng"].median())
        self.bed_med_ = float(pd.to_numeric(d["bedrooms"], errors="coerce").median())
        self.bath_med_ = float(pd.to_numeric(d["bathrooms"], errors="coerce").median())
        self.car_med_ = float(pd.to_numeric(d["car_spaces"], errors="coerce").median())

        raw = np.column_stack([
            d["lat"], d["lng"], d["bedrooms"], d["bathrooms"], d["car_spaces"],
            np.log1p(pd.to_numeric(d["land_size_m2"], errors="coerce").fillna(self.land_med_)),
            np.log1p(pd.to_numeric(d["building_size_m2"], errors="coerce").fillna(self.bld_med_)),
        ]).astype(float)
        self.mu_ = raw.mean(axis=0); self.sd_ = raw.std(axis=0); self.sd_[self.sd_ == 0] = 1.0

        self.df_ = d
        self.y_ = y_log.to_numpy(dtype=float)
        self.price_ = np.exp(self.y_)
        Z = self._vec(d)
        # one global index + per-type indices
        self.index_all_ = self._NN(n_neighbors=min(self.K, len(d)), algorithm="ball_tree").fit(Z)
        self.type_idx_ = {}
        self.type_rows_ = {}
        for t, grp in d.groupby("property_type"):
            rows = grp.index.to_numpy()
            if len(rows) >= self.MIN_TYPE:
                self.type_idx_[t] = self._NN(n_neighbors=min(self.K, len(rows)), algorithm="ball_tree").fit(Z[rows])
                self.type_rows_[t] = rows
        self._Z_cache = Z
        return self

    def _neighbors(self, df_row):
        t = str(df_row["property_type"].iloc[0])
        z = self._vec(df_row)
        if t in self.type_idx_:
            dist, idx = self.type_idx_[t].kneighbors(z)
            rows = self.type_rows_[t][idx[0]]
        else:
            dist, idx = self.index_all_.kneighbors(z)
            rows = idx[0]
        return rows, dist[0]

    def predict_interval(self, X_ignored, df=None):
        # df: raw rows (must contain the KNN columns). Vectorised over rows.
        points, los, his = [], [], []
        for i in range(len(df)):
            rows, dist = self._neighbors(df.iloc[[i]])
            prices = self.price_[rows]
            w = 1.0 / (dist + 1e-6)
            logp = self.y_[rows]
            point = np.exp(np.average(logp, weights=w))
            lo, hi = np.percentile(prices, [5, 95])
            points.append(point); los.append(lo); his.append(hi)
        return np.array(points), np.array(los), np.array(his)

    def comparables(self, df_row, n=5):
        rows, dist = self._neighbors(df_row)
        sub = self.df_.iloc[rows].head(n)
        out = []
        for (_, r), dd in zip(sub.iterrows(), dist[:n]):
            out.append({
                "address": r.get("address"), "suburb": r.get("suburb"),
                "property_type": r.get("property_type"),
                "bedrooms": _intnan(r.get("bedrooms")), "bathrooms": _intnan(r.get("bathrooms")),
                "car_spaces": _intnan(r.get("car_spaces")),
                "land_size_m2": _intnan(r.get("land_size_m2")),
                "sold_price": int(r.get("sold_price")), "date_sold": str(r.get("date_sold"))[:10],
            })
        return out, int(len(rows))


def _intnan(v):
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return None
        return int(v)
    except (ValueError, TypeError):
        return None
