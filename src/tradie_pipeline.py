#!/usr/bin/env python3
import argparse
import csv
from dataclasses import asdict
from pathlib import Path
from typing import List, Set, Tuple

from openpyxl import Workbook

from src.google_maps_scraper import Business, GoogleMapsScraper, clean_text

DEFAULT_SUBURBS_FILE = "config/brisbane-cbd-nearby-suburbs.txt"
DEFAULT_KEYWORDS_FILE = "config/tradie-keywords.txt"
DEFAULT_OUTPUT_DIR = "output"


def read_lines(path: Path) -> List[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")]


def dedupe_businesses(rows: List[Business]) -> List[Business]:
    seen: Set[Tuple[str, str, str]] = set()
    deduped: List[Business] = []
    for row in rows:
        key = (
            clean_text(row.name).lower(),
            clean_text(row.phone).lower(),
            clean_text(row.website).lower(),
        )
        fallback_key = (
            clean_text(row.name).lower(),
            clean_text(row.address).lower(),
            clean_text(row.category).lower(),
        )
        final_key = key if any(key[1:]) else fallback_key
        if final_key in seen:
            continue
        seen.add(final_key)
        deduped.append(row)
    return deduped


def write_csv(path: Path, rows: List[Business]) -> None:
    fieldnames = list(asdict(rows[0]).keys()) if rows else list(Business().__dict__.keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_xlsx(path: Path, rows: List[Business]) -> None:
    fieldnames = list(asdict(rows[0]).keys()) if rows else list(Business().__dict__.keys())
    wb = Workbook()
    ws = wb.active
    ws.title = "Tradies"
    ws.append(fieldnames)
    for row in rows:
        ws.append([asdict(row)[field] for field in fieldnames])
    wb.save(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run tradie Google Maps searches across a suburb list and deduplicate results.")
    parser.add_argument("--suburbs-file", default=DEFAULT_SUBURBS_FILE)
    parser.add_argument("--keywords-file", default=DEFAULT_KEYWORDS_FILE)
    parser.add_argument("--total-per-query", type=int, default=8)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--headed", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    suburbs = read_lines(Path(args.suburbs_file))
    keywords = read_lines(Path(args.keywords_file))
    scraper = GoogleMapsScraper(headless=not args.headed)
    all_rows: List[Business] = []
    for suburb in suburbs:
        for keyword in keywords:
            query = f"{keyword} in {suburb} Brisbane"
            print(f"Running: {query}")
            all_rows.extend(scraper.scrape_query(query, args.total_per_query))
    deduped = dedupe_businesses(all_rows)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "tradies-brisbane-cbd-nearby-suburbs.csv"
    xlsx_path = output_dir / "tradies-brisbane-cbd-nearby-suburbs.xlsx"
    write_csv(csv_path, deduped)
    write_xlsx(xlsx_path, deduped)
    print(f"Raw rows: {len(all_rows)}")
    print(f"Deduped rows: {len(deduped)}")
    print(f"CSV: {csv_path}")
    print(f"XLSX: {xlsx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
