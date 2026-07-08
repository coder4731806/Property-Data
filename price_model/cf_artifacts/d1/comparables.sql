-- Comparable sales for the estimator ("based on N similar sold properties").
-- Bind: :suburb :type :beds :lat :lng
-- Geo ranking uses a degree-space distance; at QLD latitudes 1 deg lng ~ 99km,
-- 1 deg lat ~ 111km, close enough for ranking nearby sales.
SELECT address, suburb, property_type, bedrooms, bathrooms, car_spaces,
       land_size_m2, sold_price, date_sold,
       ((lat - :lat)*(lat - :lat) + (lng - :lng)*(lng - :lng)) AS d2
FROM sold_records
WHERE property_type = :type
  AND bedrooms BETWEEN :beds - 1 AND :beds + 1
  AND date_sold >= date('now', '-24 months')
  AND lat BETWEEN :lat - 0.15 AND :lat + 0.15
  AND lng BETWEEN :lng - 0.15 AND :lng + 0.15
ORDER BY d2 ASC, date_sold DESC
LIMIT 15;
