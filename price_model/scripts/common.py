"""
Shared helpers used by data prep, training, and inference so the exact same
parsing / canonicalisation logic is applied everywhere.
"""
import re
import unicodedata
from datetime import datetime

# ---- Feature definitions (single source of truth) -------------------------

NUMERIC_FEATURES = ["bedrooms", "bathrooms", "car_spaces", "land_size_m2", "building_size_m2"]
# Missing-value indicator flags (land/building size are frequently missing)
FLAG_FEATURES = ["land_size_missing", "building_size_missing"]
GEO_FEATURES = ["lat", "lng"]
# Hierarchical locality price signal (target-encoded, fit on train only)
ENCODED_FEATURES = ["suburb_te", "postcode_te", "region_te"]
CATEGORICAL_FEATURE = "property_type"

# Canonical property types used by the models. These align with the platform's
# listing property_type enum so a customer's selection maps straight through.
CANON_TYPES = ["house", "townhouse", "apartment", "villa", "acreage", "land", "other"]

# Raw sold-data property type -> canonical
_PTYPE_MAP = {
    "house": "house",
    "townhouse": "townhouse",
    "apartment": "apartment",
    "unit": "apartment",
    "flat": "apartment",
    "studio": "apartment",
    "serviced apartment": "apartment",
    "terrace": "apartment",
    "villa": "villa",
    "duplex/semi-detached": "townhouse",
    "duplex": "townhouse",
    "semi-detached": "townhouse",
    "acreage": "acreage",
    "acreage/semi-rural": "acreage",
    "rural": "acreage",
    "land": "land",
    "vacant land": "land",
    "other": "other",
    "residential-other": "other",
}

# Platform listing enum -> canonical (used at inference time)
PLATFORM_TYPE_MAP = {
    "house": "house",
    "townhouse": "townhouse",
    "apartment": "apartment",
    "villa": "villa",
    "acreage": "acreage",
    "rural": "acreage",
    "land": "land",
    "retirement_living": "apartment",
    "block_of_units": "apartment",
}

# Source Excel file (stem) -> region label
REGION_FROM_FILE = {
    "Brisbane_inner_city": "brisbane_inner_city",
    "brisbane-inner_north": "brisbane_inner_north",
    "brisbane-inner_south": "brisbane_inner_south",
    "brisbane-outer_north": "brisbane_outer_north",
    "brisbane-outer_west_rural": "brisbane_outer_west_rural",
    "brisbane-bayside_east": "brisbane_bayside_east",
    "brisbane-redlands_bayside": "brisbane_redlands_bayside",
    "brisbane-south_west": "brisbane_south_west",
    "goldcoast": "gold_coast",
    "sunshine_coast": "sunshine_coast",
    "logan_ipswich": "logan_ipswich",
    "regional_qld": "regional_qld",
}


def canonical_property_type(raw):
    if raw is None:
        return "other"
    key = str(raw).strip().lower()
    return _PTYPE_MAP.get(key, "other")


def canonical_platform_type(raw):
    """Map a platform listing property_type to the model's canonical type."""
    if raw is None:
        return "other"
    key = str(raw).strip().lower()
    return PLATFORM_TYPE_MAP.get(key, _PTYPE_MAP.get(key, "other"))


def parse_price(raw):
    """'$930,000' -> 930000.0 ; returns None if no digits."""
    if raw is None:
        return None
    digits = re.sub(r"[^0-9.]", "", str(raw))
    if not digits or digits == ".":
        return None
    try:
        return float(digits)
    except ValueError:
        return None


def parse_size(raw):
    """Coerce a land/building size cell ('101', 101, None) to float m2."""
    if raw is None:
        return None
    s = re.sub(r"[^0-9.]", "", str(raw))
    if not s or s == ".":
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return v if v > 0 else None


_DATE_FORMATS = ["%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y"]


def parse_date(raw):
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    s = str(raw).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def normalize_suburb(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return s.strip().upper()
