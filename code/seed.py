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

def load_all_responses(path):
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    decoder = json.JSONDecoder()
    pos = 0
    responses = []
    while pos < len(content):
        stripped = content[pos:].lstrip()
        if not stripped:
            break
        pos = len(content) - len(stripped)
        obj, end = decoder.raw_decode(content, pos)
        responses.append(obj)
        pos += end
    return responses


def detect_items(response):
    root = response.get("data", {})

    # Structure 1: soldSearch (search results page)
    try:
        found = root["soldSearch"]["results"]["exact"]["items"]
        print("Detected structure: soldSearch")
        return "soldSearch", found
    except (KeyError, TypeError):
        pass

    # Structure 2: details.recentSales (property detail page)
    try:
        found = root["details"]["recentSales"]["items"]
        print("Detected structure: details.recentSales")
        return "recentSales", found
    except (KeyError, TypeError):
        pass

    # Structure 3: components (component-based page)
    try:
        components = root["components"]["details"]["components"]
        for comp in components:
            if comp.get("__typename") == "RecentSales":
                print("Detected structure: components.recentSales")
                return "recentSales", comp["items"]
    except (KeyError, TypeError):
        pass

    raise ValueError(f"Unknown response structure. Top-level keys: {list(root.keys())}")


def parse_sold_search(raw):
    listing = raw["listing"]
    land = listing["propertySizes"]["land"]
    building = listing["propertySizes"]["building"]
    price_raw = listing.get("price", {})
    return {
        "id": listing["id"],
        "address": listing["address"]["display"]["fullAddress"],
        "suburb": listing["address"].get("suburb"),
        "postcode": listing["address"].get("postcode"),
        "state": listing["address"].get("state"),
        "price_display": price_raw.get("display") if price_raw else None,
        "property_type": listing["propertyType"]["id"],
        "bedrooms": listing["generalFeatures"]["bedrooms"]["value"],
        "bathrooms": listing["generalFeatures"]["bathrooms"]["value"],
        "parking": listing["generalFeatures"]["parkingSpaces"]["value"],
        "land_m2": land["displayValue"].replace(",", "") if land else None,
        "building_m2": building["displayValue"].replace(",", "") if building else None,
        "date_sold": listing["dateSold"]["display"],
        "agency": listing["listingCompany"]["name"],
        "listing_url": listing["_links"]["canonical"]["href"],
    }


def parse_recent_sales(raw):
    path = raw["_links"]["canonical"]["path"]
    listing_id = path.split("-")[-1]
    price_raw = raw.get("price", {})
    return {
        "id": listing_id,
        "address": raw["address"]["display"]["fullAddress"],
        "suburb": None,
        "postcode": None,
        "state": None,
        "price_display": price_raw.get("display") if price_raw else None,
        "property_type": None,
        "bedrooms": raw["generalFeatures"]["bedrooms"]["value"],
        "bathrooms": raw["generalFeatures"]["bathrooms"]["value"],
        "parking": raw["generalFeatures"]["parkingSpaces"]["value"],
        "land_m2": None,
        "building_m2": None,
        "date_sold": raw["dateSold"]["display"],
        "agency": None,
        "listing_url": "https://www.realestate.com.au" + path,
    }


parsers = {
    "soldSearch": parse_sold_search,
    "recentSales": parse_recent_sales,
}

all_responses = load_all_responses("response.json")
print(f"Found {len(all_responses)} response block(s) in response.json")

new_listings = []
for response_block in all_responses:
    structure, items = detect_items(response_block)
    parse = parsers[structure]
    for item in items:
        parsed = parse(item)
        if parsed["id"] in existing_ids:
            continue
        existing_ids.add(parsed["id"])
        new_listings.append(parsed)

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
