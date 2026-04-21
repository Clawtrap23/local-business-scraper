#!/usr/bin/env python3
import argparse
import csv
import re
from pathlib import Path
from typing import Dict, List

import requests
from openpyxl import Workbook

TIMEOUT = 20
HEADERS = {"User-Agent": "local-business-scraper/enrichment/1.0"}
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")

CONTACT_HINTS = ["contact", "quote", "book", "booking", "enquiry", "inquiry", "service"]
SOCIAL_HINTS = ["facebook.com", "instagram.com", "linkedin.com", "youtube.com", "tiktok.com"]
DIRECTORY_HINTS = ["tripadvisor.com", "yelp.com", "yellowpages", "oneflare", "hipages"]


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"https://{url}"


def fetch(url: str) -> tuple[str, str]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        response.raise_for_status()
        return response.url, response.text
    except Exception:
        return "", ""


def extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def extract_emails(html: str) -> str:
    return " ; ".join(sorted(set(EMAIL_RE.findall(html))))


def extract_phones(html: str) -> str:
    found = sorted(set(p.strip() for p in PHONE_RE.findall(html)))
    return " ; ".join(found[:5])


def detect_contact_hints(html_lower: str) -> str:
    return "yes" if any(hint in html_lower for hint in CONTACT_HINTS) else "no"


def detect_socials(html_lower: str) -> str:
    found = [hint for hint in SOCIAL_HINTS if hint in html_lower]
    return ", ".join(found) if found else ""


def detect_directories(html_lower: str) -> str:
    found = [hint for hint in DIRECTORY_HINTS if hint in html_lower]
    return ", ".join(found) if found else ""


def enrich_row(row: Dict[str, str]) -> Dict[str, str]:
    website = normalize_url(row.get("website", ""))
    if not website:
        row["enriched_final_url"] = ""
        row["enriched_page_title"] = ""
        row["enriched_emails_found"] = ""
        row["enriched_phones_found"] = ""
        row["enriched_contact_hints"] = "no"
        row["enriched_social_links"] = ""
        row["enriched_directory_mentions"] = ""
        row["enriched_notes"] = "No website to enrich"
        return row

    final_url, html = fetch(website)
    if not final_url or not html:
        row["enriched_final_url"] = ""
        row["enriched_page_title"] = ""
        row["enriched_emails_found"] = ""
        row["enriched_phones_found"] = ""
        row["enriched_contact_hints"] = "unknown"
        row["enriched_social_links"] = ""
        row["enriched_directory_mentions"] = ""
        row["enriched_notes"] = "Website listed but page could not be loaded"
        return row

    html_lower = html.lower()
    row["enriched_final_url"] = final_url
    row["enriched_page_title"] = extract_title(html)
    row["enriched_emails_found"] = extract_emails(html)
    row["enriched_phones_found"] = extract_phones(html)
    row["enriched_contact_hints"] = detect_contact_hints(html_lower)
    row["enriched_social_links"] = detect_socials(html_lower)
    row["enriched_directory_mentions"] = detect_directories(html_lower)
    row["enriched_notes"] = "Website enrichment completed"
    return row


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(path: Path, rows: List[Dict[str, str]]) -> None:
    fieldnames = list(rows[0].keys()) if rows else []
    wb = Workbook()
    ws = wb.active
    ws.title = "Enriched"
    if fieldnames:
        ws.append(fieldnames)
        for row in rows:
            ws.append([row.get(field, "") for field in fieldnames])
    wb.save(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich existing scraped data by visiting each business website.")
    parser.add_argument("input_csv", help="Input CSV file")
    parser.add_argument("--output-csv", default="output/enriched-results.csv")
    parser.add_argument("--output-xlsx", default="output/enriched-results.xlsx")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_csv(Path(args.input_csv))
    enriched = [enrich_row(dict(row)) for row in rows]
    write_csv(Path(args.output_csv), enriched)
    write_xlsx(Path(args.output_xlsx), enriched)
    print(f"Input rows: {len(rows)}")
    print(f"Output CSV: {args.output_csv}")
    print(f"Output XLSX: {args.output_xlsx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
