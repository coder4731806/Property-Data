/**
 * Pure-JS evaluator for the Alethia price models. Zero dependencies.
 * Runs identically in a Cloudflare Worker (ebm/linear, ~0.1ms per estimate)
 * and in the browser (lightgbm, lazy-loaded ~3MB gz asset).
 *
 * Artifacts (JSON): pipeline.json, ebm.json, linear.json, lightgbm.json
 * All models predict log(price) in CURRENT (index base month) dollars.
 *
 * Usage:
 *   import { featurize, predictEbm, predictLinear, predictLgbm, estimate } from "./evaluator.mjs";
 *   const est = estimate(
 *     { suburb: "PADDINGTON", postcode: "4064", property_type: "house",
 *       bedrooms: 3, bathrooms: 2, car_spaces: 1, land_size_m2: 405 },
 *     { pipeline, ebm, linear, lightgbm });   // lightgbm optional
 */

const PLATFORM_TYPE_MAP = {
  house: "house", townhouse: "townhouse", apartment: "apartment", unit: "apartment",
  flat: "apartment", studio: "apartment", villa: "villa", duplex: "townhouse",
  "duplex/semi-detached": "townhouse", "semi-detached": "townhouse",
  acreage: "acreage", "acreage/semi-rural": "acreage", rural: "acreage",
  land: "land", "vacant land": "land", retirement_living: "apartment",
  block_of_units: "apartment", other: "other",
};

const norm = (s) => (s == null ? "" : String(s).trim().toUpperCase());
const num = (v) => {
  if (v == null || v === "") return null;   // Number(null) === 0, guard first
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

/** input {suburb, postcode, region?, property_type, bedrooms, bathrooms,
 *  car_spaces, land_size_m2?, building_size_m2?, lat?, lng?}
 *  -> Float64Array ordered as pipeline.feature_names */
export function featurize(input, P) {
  const suburb = norm(input.suburb);
  const postcode = norm(input.postcode);
  let region = norm(input.region).toLowerCase();
  if (!region) {
    // derive region from suburb/postcode maps shipped in pipeline.json
    const pc = P.suburb_postcode[suburb] || postcode;
    region = P.postcode_region[pc] || "";
  }
  const ptype = PLATFORM_TYPE_MAP[String(input.property_type || "").toLowerCase()] || "other";

  const regionTe = P.region_te[region] ?? P.global_mean;
  const postcodeTe = P.postcode_te[postcode] ?? regionTe;
  const suburbTe = P.suburb_te[suburb] ?? postcodeTe;

  const land = num(input.land_size_m2);
  const bld = num(input.building_size_m2);
  const vals = {
    bedrooms: num(input.bedrooms) ?? P.medians.bedrooms,
    bathrooms: num(input.bathrooms) ?? P.medians.bathrooms,
    car_spaces: num(input.car_spaces) ?? P.medians.car_spaces,
    land_size_m2: land ?? P.medians.land_size_m2,
    building_size_m2: bld ?? P.medians.building_size_m2,
    land_size_missing: land == null ? 1 : 0,
    building_size_missing: bld == null ? 1 : 0,
    lat: num(input.lat) ?? P.lat_med,
    lng: num(input.lng) ?? P.lng_med,
    suburb_te: suburbTe, postcode_te: postcodeTe, region_te: regionTe,
  };
  for (const t of P.types) vals[`type_${t}`] = t === ptype ? 1 : 0;
  return Float64Array.from(P.feature_names.map((f) => vals[f]));
}

// ---------------------------------------------------------------------------
export function predictEbm(vec, E) {
  let s = E.intercept;
  for (const t of E.terms) {
    let v = t.scores;
    for (let k = 0; k < t.features.length; k++) {
      const x = vec[t.features[k]];
      const cuts = t.cuts[k];
      let i;
      if (x == null || Number.isNaN(x)) i = 0;
      else {
        // 1 + upper_bound(cuts, x)  (matches np.searchsorted side="right")
        let lo = 0, hi = cuts.length;
        while (lo < hi) {
          const mid = (lo + hi) >> 1;
          if (cuts[mid] <= x) lo = mid + 1;
          else hi = mid;
        }
        i = 1 + lo;
      }
      v = v[i];
    }
    s += v;
  }
  return { point: Math.exp(s), low: Math.exp(s + E.conformal_lo), high: Math.exp(s + E.conformal_hi) };
}

// One EBM term's scalar contribution (same index walk as predictEbm).
function ebmTermScore(vec, t) {
  let v = t.scores;
  for (let k = 0; k < t.features.length; k++) {
    const x = vec[t.features[k]];
    const cuts = t.cuts[k];
    let i;
    if (x == null || Number.isNaN(x)) i = 0;
    else {
      let lo = 0, hi = cuts.length;
      while (lo < hi) { const mid = (lo + hi) >> 1; if (cuts[mid] <= x) lo = mid + 1; else hi = mid; }
      i = 1 + lo;
    }
    v = v[i];
  }
  return v;
}

// Human-readable grouping of the raw features into buckets a seller
// understands (type_* one-hots + the three target-encoded location features
// collapse into single "Property type" / "Suburb & location" buckets).
const EBM_GROUP = {
  bedrooms: "Bedrooms", bathrooms: "Bathrooms", car_spaces: "Car spaces",
  land_size_m2: "Land size", land_size_missing: "Land size",
  building_size_m2: "Building size", building_size_missing: "Building size",
  lat: "Suburb & location", lng: "Suburb & location",
  suburb_te: "Suburb & location", postcode_te: "Suburb & location", region_te: "Suburb & location",
  type_house: "Property type", type_townhouse: "Property type", type_apartment: "Property type",
  type_villa: "Property type", type_acreage: "Property type", type_land: "Property type",
  type_other: "Property type",
};

/** Glassbox "why this price" breakdown for the EBM. The EBM is additive in
 *  log-price, so each feature group's effect is multiplicative on the baseline;
 *  baseline * PROD(exp(log_effect)) == the EBM point. Factors are sorted by
 *  absolute impact, each with a signed % effect on price. */
export function explainEbm(vec, E, featureNames) {
  const groups = new Map();
  for (const t of E.terms) {
    const c = ebmTermScore(vec, t);
    const label = t.features.length > 1
      ? "Feature combinations"
      : (EBM_GROUP[featureNames[t.features[0]]] ?? "Other");
    groups.set(label, (groups.get(label) ?? 0) + c);
  }
  const baseline = Math.exp(E.intercept);
  const factors = [...groups.entries()]
    .map(([label, log]) => ({ label, log_effect: log, pct: (Math.exp(log) - 1) * 100 }))
    .filter((f) => Math.abs(f.pct) >= 0.5)
    .sort((a, b) => Math.abs(b.log_effect) - Math.abs(a.log_effect));
  return { baseline: Math.round(baseline / 1000) * 1000, factors };
}

// ---------------------------------------------------------------------------
export function predictLinear(vec, L, featureNames) {
  const idx = L.cols.map((c) => featureNames.indexOf(c));
  const a = [1];
  for (let j = 0; j < idx.length; j++) a.push((vec[idx[j]] - L.mean[j]) / L.std[j]);
  let yhat = 0;
  for (let j = 0; j < a.length; j++) yhat += a[j] * L.beta[j];
  let quad = 0;
  for (let i = 0; i < a.length; i++) {
    let r = 0;
    for (let j = 0; j < a.length; j++) r += L.xtx_inv[i][j] * a[j];
    quad += a[i] * r;
  }
  const se = Math.sqrt(L.s2 * (1 + quad));
  return { point: Math.exp(yhat), low: Math.exp(yhat - L.tcrit * se), high: Math.exp(yhat + L.tcrit * se) };
}

// ---------------------------------------------------------------------------
function walkTrees(vec, trees) {
  let s = 0;
  for (const t of trees) {
    let i = 0;
    while (t.sf[i] >= 0) {
      const v = vec[t.sf[i]];
      if (v == null || Number.isNaN(v)) i = t.dl[i] ? t.lc[i] : t.rc[i];
      else i = v <= t.th[i] ? t.lc[i] : t.rc[i];
    }
    s += t.lv[i];
  }
  return s;
}

export function predictLgbm(vec, G) {
  const lo0 = walkTrees(vec, G.quantiles["0.05"]);
  const mid0 = walkTrees(vec, G.quantiles["0.5"]);
  const hi0 = walkTrees(vec, G.quantiles["0.95"]);
  const [lo, mid, hi] = [lo0, mid0, hi0].sort((a, b) => a - b); // non-crossing
  return {
    point: Math.exp(mid),
    low: Math.exp(lo - G.cqr_delta),
    high: Math.exp(hi + G.cqr_delta),
  };
}

// ---------------------------------------------------------------------------
const r1000 = (x) => Math.round(x / 1000) * 1000;

/** Full estimate. artifacts = {pipeline, ebm, linear, lightgbm?}.
 *  comparables (from D1) can be passed in for the confidence score. */
export function estimate(input, artifacts, opts = {}) {
  const vec = featurize(input, artifacts.pipeline);
  const models = {};
  if (artifacts.ebm) models.ebm = predictEbm(vec, artifacts.ebm);
  if (artifacts.linear) models.linear = predictLinear(vec, artifacts.linear, artifacts.pipeline.feature_names);
  if (artifacts.lightgbm) models.lightgbm = predictLgbm(vec, artifacts.lightgbm);

  const best = models.lightgbm || models.ebm || models.linear;
  const bandPct = (100 * (best.high - best.low)) / best.point;
  const nComp = opts.comparableCount ?? null;
  // confidence: comparable-data depth x band tightness (mirrors predict_service)
  let score = 50;
  if (nComp != null) score = Math.min(50, nComp * 2.5);
  score += Math.max(0, 50 - Math.max(0, bandPct - 30));
  score = Math.round(Math.max(5, Math.min(100, score)));
  const label = score >= 70 ? "High" : score >= 40 ? "Medium" : "Low";

  const fmt = (m) => ({ expected_price: r1000(m.point), price_low: r1000(m.low), price_high: r1000(m.high) });
  return {
    ...fmt(best),
    recommended_model: models.lightgbm ? "lightgbm" : models.ebm ? "ebm" : "linear",
    confidence_score: score,
    confidence_label: label,
    confidence_factors: { comparable_sales_in_suburb: nComp, band_width_pct: Math.round(bandPct * 10) / 10 },
    models: Object.fromEntries(Object.entries(models).map(([k, v]) => [k, fmt(v)])),
  };
}
