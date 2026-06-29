import json
import csv
import os

# Load existing IDs to avoid duplicates
existing_ids = set()
fieldnames = None
CSV_FILE = "aspley_sold.csv"
JSON_FILE = "aspley_sold.json"

if os.path.exists(CSV_FILE):
    with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            existing_ids.add(row["id"])

existing_json = []
if os.path.exists(JSON_FILE):
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        existing_json = json.load(f)

# Load the response
with open("response.json", "r", encoding="utf-8") as f:
    data = json.load(f)

new_listings = []

items = data["data"]["soldSearch"]["results"]["exact"]["items"]

for item in items:
    l = item["listing"]

    if l["id"] in existing_ids:
        continue

    land = l["propertySizes"]["land"]
    building = l["propertySizes"]["building"]
    price_raw = l.get("price", {})

    new_listings.append({
        "id": l["id"],
        "address": l["address"]["display"]["fullAddress"],
        "suburb": l["address"]["suburb"],
        "postcode": l["address"]["postcode"],
        "state": l["address"]["state"],
        "price_display": price_raw.get("display") if price_raw else None,
        "property_type": l["propertyType"]["id"],
        "bedrooms": l["generalFeatures"]["bedrooms"]["value"],
        "bathrooms": l["generalFeatures"]["bathrooms"]["value"],
        "parking": l["generalFeatures"]["parkingSpaces"]["value"],
        "land_m2": land["displayValue"].replace(",", "") if land else None,
        "building_m2": building["displayValue"].replace(",", "") if building else None,
        "date_sold": l["dateSold"]["display"],
        "agency": l["listingCompany"]["name"],
        "listing_url": l["_links"]["canonical"]["href"],
    })

print(f"Found {len(new_listings)} new listings ({len(existing_ids)} already in file)")

if new_listings:
    # Append to CSV
    write_header = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=new_listings[0].keys())
        if write_header:
            writer.writeheader()
        writer.writerows(new_listings)

    # Rewrite JSON with all listings
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_json + new_listings, f, indent=2)

print("Done. Files: aspley_sold.csv, aspley_sold.json")
