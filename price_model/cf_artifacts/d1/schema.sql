DROP TABLE IF EXISTS sold_records;
CREATE TABLE sold_records (
  id            TEXT PRIMARY KEY,
  region        TEXT,
  suburb        TEXT,
  postcode      TEXT,
  address       TEXT,
  property_type TEXT,
  bedrooms      INTEGER,
  bathrooms     INTEGER,
  car_spaces    INTEGER,
  land_size_m2  REAL,
  sold_price    INTEGER,
  date_sold     TEXT,          -- ISO yyyy-mm-dd
  lat           REAL,
  lng           REAL,
  agency_name   TEXT,          -- marketing agency (~91% coverage)
  agent_names   TEXT           -- comma-separated agent(s) (~61% coverage)
);
CREATE INDEX idx_sold_suburb_type ON sold_records(suburb, property_type, date_sold);
CREATE INDEX idx_sold_postcode    ON sold_records(postcode, date_sold);
CREATE INDEX idx_sold_date        ON sold_records(date_sold);
CREATE INDEX idx_sold_agency      ON sold_records(agency_name);
