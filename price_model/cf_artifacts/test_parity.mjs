/**
 * Proves evaluator.mjs reproduces the Python models end to end.
 *   node test_parity.mjs
 */
import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";
import { featurize, predictEbm, predictLinear, predictLgbm } from "./evaluator.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const J = (f) => JSON.parse(readFileSync(join(here, f), "utf8"));

const pipeline = J("pipeline.json");
const ebm = J("ebm.json");
const linear = J("linear.json");
const lightgbm = J("lightgbm.json");
const cases = J("parity_fixture.json");

// Fixture rows come from the sold data where property_type is already
// canonical; featurize expects platform input but the maps are identity for
// canonical values, so the same fixture exercises both paths.

let worst = { linear: 0, lightgbm: 0, ebm: 0 };
for (const c of cases) {
  const vec = featurize(c.input, pipeline);
  const got = {
    linear: predictLinear(vec, linear, pipeline.feature_names),
    lightgbm: predictLgbm(vec, lightgbm),
    ebm: predictEbm(vec, ebm),
  };
  for (const m of Object.keys(worst)) {
    const [p, lo, hi] = c.expected[m];
    for (const [g, e] of [[got[m].point, p], [got[m].low, lo], [got[m].high, hi]]) {
      const rel = Math.abs(g - e) / e;
      if (rel > worst[m]) worst[m] = rel;
    }
  }
}

let ok = true;
for (const [m, w] of Object.entries(worst)) {
  const pass = w < 5e-4; // < 0.05% price difference
  ok &&= pass;
  console.log(`${m.padEnd(9)} worst rel diff = ${(w * 100).toFixed(4)}%  ${pass ? "PASS" : "FAIL"}`);
}
console.log(ok ? `\nAll ${cases.length} cases within tolerance.` : "\nPARITY FAILURE");
process.exit(ok ? 0 : 1);
