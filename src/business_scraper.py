#!/usr/bin/env python3
import argparse
import csv
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests
from openpyxl import Workbook

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_USER_AGENT = "local-business-scraper/0.1 (OpenClaw project)"

TARGET_QUERIES = [
    ('amenity', 'restaurant'),
    ('shop', 'hairdresser'),
    ('shop', 'beauty'),
    ('craft', 'electrician'),
    ('craft', 'plumber'),
    ('craft', 'locksmith'),
    ('shop', 'car_repair'),
    ('office', 'company'),
    ('shop', 'bakery'),
    ('shop', 'florist'),
    ('shop', 'laundry'),
    ('amenity', 'cafe'),
    ('amenity', 'fast_food'),
]

CATEGORY_LABELS = {
    ('amenity', 'restaurant'): 'Restaurant',
    ('shop', 'hairdresser'): 'Hairdresser',
    ('shop', 'beauty'): 'Beauty / Nail salon',
    ('craft', 'electrician'): 'Electrician',
    ('craft', 'plumber'): 'Plumber',
    ('craft', 'locksmith'): 'Locksmith',
    ('shop', 'car_repair'): 'Car repair',
    ('office', 'company'): 'Company / Office',
    ('shop', 'bakery'): 'Bakery',
    ('shop', 'florist'): 'Florist',
    ('shop', 'laundry'): 'Laundry',
    ('amenity', 'cafe'): 'Cafe',
    ('amenity', 'fast_food'): 'Fast food',
}

EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)


def geocode_location(location: str, user_agent: str) -> Tuple[float, float, str]:
    response = requests.get(
        NOMINATIM_URL,
        params={"q": location, "format": "jsonv2", "limit": 1},
        headers={"User-Agent": user_agent},
        timeout=30,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        raise ValueError(f"Location not found: {location}")
    first = results[0]
    return float(first["lat"]), float(first["lon"]), first.get("display_name", location)


def build_overpass_query(lat: float, lon: float, radius_m: int) -> str:
    parts = []
    for key, value in TARGET_QUERIES:
        parts.append(f'node["{key}"="{value}"](around:{radius_m},{lat},{lon});')
        parts.append(f'way["{key}"="{value}"](around:{radius_m},{lat},{lon});')
        parts.append(f'relation["{key}"="{value}"](around:{radius_m},{lat},{lon});')
    return "[out:json][timeout:90];(" + "".join(parts) + ");out center tags;"


def fetch_overpass(query: str, user_agent: str) -> List[dict]:
    response = requests.post(
        OVERPASS_URL,
        data=query.encode("utf-8"),
        headers={"User-Agent": user_agent, "Content-Type": "text/plain"},
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("elements", [])


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def infer_category(tags: Dict[str, str]) -> str:
    for key, value in TARGET_QUERIES:
        if tags.get(key) == value:
            return CATEGORY_LABELS.get((key, value), value.replace('_', ' ').title())
    for fallback_key in ("amenity", "shop", "craft", "office"):
        if tags.get(fallback_key):
            return tags[fallback_key].replace('_', ' ').title()
    return "Unknown"


def format_address(tags: Dict[str, str]) -> str:
    pieces = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb"),
        tags.get("addr:city"),
        tags.get("addr:state"),
        tags.get("addr:postcode"),
    ]
    address = ", ".join([p for p in pieces if p])
    return address or tags.get("addr:full") or ""


def clean_website(url: str) -> str:
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"https://{url}"


def valid_email(value: str) -> str:
    if not value:
        return ""
    value = value.strip()
    return value if EMAIL_RE.match(value) else ""


def infer_business_size(tags: Dict[str, str]) -> str:
    employees = tags.get("employees") or tags.get("staff_count")
    if employees:
        return employees
    if tags.get("brand"):
        return "Likely chain / branded business"
    if tags.get("operator") and tags.get("operator") != tags.get("name"):
        return "Operated by a larger entity"
    if tags.get("building") in {"commercial", "retail"}:
        return "Commercial premises"
    return "Unknown"


def infer_website_quality(website: str) -> Tuple[str, str]:
    if not website:
        return "no", "No website listed"
    recent = "Likely modern" if website.startswith("https://") else "Possibly older/basic"
    return "yes", recent


def normalize_element(element: dict, origin_lat: float, origin_lon: float) -> Optional[dict]:
    tags = element.get("tags", {})
    name = tags.get("name")
    if not name:
        return None
    lat = element.get("lat") or (element.get("center") or {}).get("lat")
    lon = element.get("lon") or (element.get("center") or {}).get("lon")
    if lat is None or lon is None:
        return None
    website = clean_website(tags.get("website") or tags.get("contact:website") or tags.get("url") or "")
    email = valid_email(tags.get("email") or tags.get("contact:email") or "")
    website_present, website_quality = infer_website_quality(website)
    phone = tags.get("phone") or tags.get("contact:phone") or tags.get("mobile") or ""
    category = infer_category(tags)
    address = format_address(tags)
    size = infer_business_size(tags)
    distance = round(haversine_km(origin_lat, origin_lon, float(lat), float(lon)), 3)
    return {
        "business_name": name,
        "category_type": category,
        "address_location": address,
        "phone_number": phone,
        "website_url": website,
        "email_address": email,
        "business_size": size,
        "has_website": website_present,
        "website_quality": website_quality,
        "osm_id": f'{element.get("type", "")}/{element.get("id", "")}',
        "latitude": lat,
        "longitude": lon,
        "distance_km": distance,
    }


def dedupe(rows: Iterable[dict]) -> List[dict]:
    seen = {}
    for row in rows:
        key = (
            row["business_name"].strip().lower(),
            row["address_location"].strip().lower(),
            row["phone_number"].strip().lower(),
        )
        if key not in seen:
            seen[key] = row
        else:
            existing = seen[key]
            if len(row["website_url"]) + len(row["email_address"]) > len(existing["website_url"]) + len(existing["email_address"]):
                seen[key] = row
    return sorted(seen.values(), key=lambda item: (item["category_type"], item["business_name"]))


def write_csv(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Businesses"
    ws.append(fieldnames)
    for row in rows:
        ws.append([row.get(field, "") for field in fieldnames])
    wb.save(path)


def summarize(rows: List[dict]) -> str:
    counts = Counter(row["category_type"] for row in rows)
    top = ", ".join(f"{k}: {v}" for k, v in counts.most_common(8))
    return f"Collected {len(rows)} businesses. Top categories: {top}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect local business data around a location and export to CSV/XLSX.")
    parser.add_argument("location", help="Free-form location, e.g. 'Brisbane CBD'")
    parser.add_argument("--radius-km", type=float, default=2.0, help="Search radius in kilometers (default: 2.0)")
    parser.add_argument("--output-dir", default="output", help="Directory for generated files")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="HTTP User-Agent for API requests")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    radius_m = int(args.radius_km * 1000)
    try:
        lat, lon, resolved_name = geocode_location(args.location, args.user_agent)
        query = build_overpass_query(lat, lon, radius_m)
        elements = fetch_overpass(query, args.user_agent)
        normalized = [normalize_element(el, lat, lon) for el in elements]
        rows = dedupe([row for row in normalized if row])
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = re.sub(r"[^a-z0-9]+", "-", args.location.lower()).strip("-") or "businesses"
        csv_path = output_dir / f"{stem}.csv"
        xlsx_path = output_dir / f"{stem}.xlsx"
        fieldnames = [
            "business_name",
            "category_type",
            "address_location",
            "phone_number",
            "website_url",
            "email_address",
            "business_size",
            "has_website",
            "website_quality",
            "distance_km",
            "latitude",
            "longitude",
            "osm_id",
        ]
        write_csv(csv_path, rows, fieldnames)
        write_xlsx(xlsx_path, rows, fieldnames)
        print(f"Resolved location: {resolved_name} ({lat}, {lon})")
        print(summarize(rows))
        print(f"CSV: {csv_path}")
        print(f"XLSX: {xlsx_path}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
