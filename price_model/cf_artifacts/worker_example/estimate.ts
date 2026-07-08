/**
 * Example Hono route for apps/api: POST /api/estimate
 *
 * Free-tier friendly: EBM + linear evaluate in-Worker in ~0.1ms; comparables
 * are one indexed D1 query. LightGBM (the most accurate model) is served to
 * the BROWSER as a static asset (lightgbm.json.gz, ~3MB) and evaluated
 * client-side with the same evaluator.mjs, so it never touches Worker CPU.
 *
 * Wiring:
 *   1. copy evaluator.mjs into apps/api/src/lib/
 *   2. copy pipeline.json, ebm.json, linear.json into apps/api/src/lib/model/
 *      (about 100 KB total; bundles fine inside the 3MB Worker limit)
 *   3. import the D1 dump: wrangler d1 import <db> --file=sold_records.sql --remote
 *   4. mount this route in src/index.ts:  app.route("/api", estimate)
 */
import { Hono } from "hono";
import { featurize, estimate as runEstimate } from "../lib/evaluator.mjs";
import pipeline from "../lib/model/pipeline.json";
import ebm from "../lib/model/ebm.json";
import linear from "../lib/model/linear.json";

type Env = { DB_QLD: D1Database };

export const estimate = new Hono<{ Bindings: Env }>();

estimate.post("/estimate", async (c) => {
  const body = await c.req.json<{
    suburb: string; postcode: string; property_type: string;
    bedrooms?: number; bathrooms?: number; car_spaces?: number;
    land_size_m2?: number; building_size_m2?: number;
  }>();
  if (!body?.suburb || !body?.property_type) {
    return c.json({ error: "suburb and property_type are required" }, 400);
  }

  // suburb centroid for the comparables geo filter (median of that suburb's sales)
  const cent = await c.env.DB_QLD.prepare(
    `SELECT AVG(lat) AS lat, AVG(lng) AS lng FROM sold_records WHERE suburb = ?1`
  ).bind(body.suburb.toUpperCase()).first<{ lat: number; lng: number }>();

  const input = { ...body, lat: cent?.lat, lng: cent?.lng };

  // comparable sales: same type, beds +/-1, last 24 months, nearest first
  const beds = body.bedrooms ?? 3;
  const comps = cent?.lat
    ? await c.env.DB_QLD.prepare(
        `SELECT address, suburb, property_type, bedrooms, bathrooms, car_spaces,
                land_size_m2, sold_price, date_sold,
                ((lat-?1)*(lat-?1) + (lng-?2)*(lng-?2)) AS d2
         FROM sold_records
         WHERE property_type = ?3 AND bedrooms BETWEEN ?4 - 1 AND ?4 + 1
           AND date_sold >= date('now','-24 months')
           AND lat BETWEEN ?1 - 0.15 AND ?1 + 0.15
           AND lng BETWEEN ?2 - 0.15 AND ?2 + 0.15
         ORDER BY d2 ASC, date_sold DESC LIMIT 15`
      ).bind(cent.lat, cent.lng, body.property_type.toLowerCase(), beds).all()
    : { results: [] as Record<string, unknown>[] };

  const result = runEstimate(input, { pipeline, ebm, linear },
    { comparableCount: comps.results.length });

  return c.json({
    ...result,
    comparable_sales: comps.results.slice(0, 5).map(({ d2, ...r }) => r),
    n_comparables_considered: comps.results.length,
    disclaimer: "Statistical estimate, not a valuation or financial advice.",
  });
});
