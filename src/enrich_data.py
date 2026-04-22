#!/usr/bin/env python3
import argparse
import csv
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from urllib.parse import unquote, urljoin, urlparse

import requests
from openpyxl import Workbook

from src.phone_utils import choose_best_phone, dedupe_phone_variants
from src.social_relevance import score_social_relevance

TIMEOUT = 20
HEADERS = {"User-Agent": "local-business-scraper/enrichment/1.0"}
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
HREF_RE = re.compile(r"href=[\"']([^\"'#]+)[\"']", re.I)
EMAIL_CLEAN_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)
TEL_RE = re.compile(r"tel:([^\"'>\s]+)", re.I)
MAILTO_RE = re.compile(r"mailto:([^\"'>\s?]+)", re.I)

CONTACT_HINTS = ["contact", "quote", "book", "booking", "enquiry", "inquiry", "service"]
CONTACT_LINK_HINTS = ["contact", "quote", "book", "booking", "enquiry", "inquiry"]
SOCIAL_HINTS = ["facebook.com", "instagram.com", "linkedin.com", "youtube.com", "tiktok.com"]
SOCIAL_DOMAINS = {
    "facebook": "facebook.com",
    "instagram": "instagram.com",
    "linkedin": "linkedin.com",
    "youtube": "youtube.com",
    "tiktok": "tiktok.com",
}
DIRECTORY_HINTS = ["tripadvisor.com", "yelp.com", "yellowpages", "oneflare", "hipages"]
DEEP_PAGE_HINTS = ["contact", "about", "quote", "book", "booking", "enquiry", "inquiry", "service", "services"]
MAX_DEEP_PAGES = 5


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


def extract_emails(html: str) -> Set[str]:
    found = set()
    for email in EMAIL_RE.findall(html):
        email = email.strip().strip('.,;:')
        if not EMAIL_CLEAN_RE.match(email):
            continue
        if any(email.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.svg', '.webp', '.gif']):
            continue
        found.add(email)
    for raw in MAILTO_RE.findall(html):
        email = unquote(raw).strip().strip('.,;:')
        if EMAIL_CLEAN_RE.match(email):
            found.add(email)
    return found


def normalize_phone(value: str) -> str:
    value = unquote(value).strip()
    value = re.sub(r"[A-Za-z]", "", value)
    value = re.sub(r"\s+", " ", value)
    digits = re.sub(r"\D", "", value)
    if len(digits) < 8 or len(digits) > 15:
        return ""
    if value.count('.') >= 2:
        return ""
    if digits.startswith("61") and not value.startswith("+"):
        return f"+{digits}"
    if value.startswith("+"):
        return "+" + digits
    return value.strip()


def extract_phones(html: str) -> Set[str]:
    cleaned = set()
    tel_links = []
    for raw in TEL_RE.findall(html):
        phone = normalize_phone(raw)
        if phone:
            tel_links.append(phone)
            cleaned.add(phone)
    if tel_links:
        return set(tel_links)

    for raw in PHONE_RE.findall(html):
        phone = normalize_phone(raw)
        if not phone:
            continue
        digits = re.sub(r'\D', '', phone)
        if digits.startswith('0') or digits.startswith('61') or len(digits) in {8, 10, 11}:
            cleaned.add(phone)
    return cleaned


def detect_contact_hints(html_lower: str) -> str:
    return "yes" if any(hint in html_lower for hint in CONTACT_HINTS) else "no"


def detect_socials(html_lower: str) -> Set[str]:
    return {hint for hint in SOCIAL_HINTS if hint in html_lower}


def detect_directories(html_lower: str) -> Set[str]:
    return {hint for hint in DIRECTORY_HINTS if hint in html_lower}


def extract_all_links(base_url: str, html: str) -> List[str]:
    links = []
    for href in HREF_RE.findall(html):
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        links.append(absolute)
    deduped = []
    seen = set()
    for link in links:
        if link not in seen:
            seen.add(link)
            deduped.append(link)
    return deduped


def normalize_social_url(key: str, url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    if not path:
        return url

    if key == 'facebook':
        parts = [p for p in path.split('/') if p]
        if parts and parts[0] in {'profile.php'}:
            return f'{parsed.scheme}://{parsed.netloc}/{parts[0]}' + (f'?{parsed.query}' if parsed.query else '')
        if parts:
            return f'{parsed.scheme}://{parsed.netloc}/{parts[0]}/'

    if key == 'instagram':
        parts = [p for p in path.split('/') if p and p not in {'reel', 'p', 'tv', 'stories'}]
        if parts:
            return f'{parsed.scheme}://{parsed.netloc}/{parts[0]}/'

    if key == 'linkedin':
        parts = [p for p in path.split('/') if p]
        if len(parts) >= 2 and parts[0] in {'company', 'in', 'school'}:
            return f'{parsed.scheme}://{parsed.netloc}/{parts[0]}/{parts[1]}/'

    if key == 'youtube':
        parts = [p for p in path.split('/') if p]
        if len(parts) >= 2 and parts[0] in {'channel', 'c', 'user'}:
            return f'{parsed.scheme}://{parsed.netloc}/{parts[0]}/{parts[1]}'
        if parts and parts[0].startswith('@'):
            return f'{parsed.scheme}://{parsed.netloc}/{parts[0]}'

    if key == 'tiktok':
        parts = [p for p in path.split('/') if p and p not in {'video'}]
        if parts and parts[0].startswith('@'):
            return f'{parsed.scheme}://{parsed.netloc}/{parts[0]}'

    return f'{parsed.scheme}://{parsed.netloc}{parsed.path}' + (f'?{parsed.query}' if parsed.query and key == 'facebook' and 'profile.php' in parsed.path else '')


def extract_social_urls(base_url: str, html: str) -> Dict[str, str]:
    social_urls = {key: "" for key in SOCIAL_DOMAINS}
    for link in extract_all_links(base_url, html):
        lowered = link.lower()
        for key, domain in SOCIAL_DOMAINS.items():
            if domain in lowered and not social_urls[key]:
                social_urls[key] = normalize_social_url(key, link)
    return social_urls


def extract_internal_links(base_url: str, html: str) -> List[str]:
    parsed_base = urlparse(base_url)
    links = []
    for href in HREF_RE.findall(html):
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc != parsed_base.netloc:
            continue
        target = absolute.lower()
        if any(target.endswith(ext) for ext in ['.css', '.js', '.png', '.jpg', '.jpeg', '.svg', '.webp', '.gif', '.pdf', '.xml']):
            continue
        if '/wp-content/' in target or '/wp-json/' in target or '/feed/' in target:
            continue
        if any(hint in target for hint in DEEP_PAGE_HINTS):
            links.append(absolute)
    deduped = []
    seen = set()
    for link in links:
        if link not in seen:
            seen.add(link)
            deduped.append(link)
    return deduped[:MAX_DEEP_PAGES]


def extract_contact_links(base_url: str, html: str) -> List[str]:
    parsed_base = urlparse(base_url)
    links = []
    for link in extract_all_links(base_url, html):
        parsed = urlparse(link)
        lowered = link.lower()
        if parsed.netloc != parsed_base.netloc:
            continue
        if any(lowered.endswith(ext) for ext in ['.css', '.js', '.png', '.jpg', '.jpeg', '.svg', '.webp', '.gif', '.pdf', '.xml']):
            continue
        if '/wp-content/' in lowered or '/wp-json/' in lowered or '/feed/' in lowered:
            continue
        if any(hint in lowered for hint in CONTACT_LINK_HINTS):
            links.append(link)
    deduped = []
    seen = set()
    for link in links:
        if link not in seen:
            seen.add(link)
            deduped.append(link)
    return deduped[:5]


def set_empty_enrichment(row: Dict[str, str], notes: str, contact_hints: str) -> Dict[str, str]:
    row["enriched_final_url"] = ""
    row["enriched_page_title"] = ""
    row["enriched_emails_found"] = ""
    row["enriched_phones_found"] = ""
    row["enriched_best_phone"] = ""
    row["enriched_contact_hints"] = contact_hints
    row["enriched_contact_page_urls"] = ""
    row["enriched_contact_page_best_url"] = ""
    row["enriched_social_links"] = ""
    row["enriched_facebook_url"] = ""
    row["enriched_instagram_url"] = ""
    row["enriched_linkedin_url"] = ""
    row["enriched_youtube_url"] = ""
    row["enriched_tiktok_url"] = ""
    row["enriched_directory_mentions"] = ""
    row["enriched_deep_pages_checked"] = "0"
    row["enriched_deep_page_urls"] = ""
    row["enriched_notes"] = notes
    return row


def choose_best_contact_url(contact_links: List[str]) -> str:
    if not contact_links:
        return ""
    ranked: List[Tuple[int, str]] = []
    for link in contact_links:
        score = 0
        lowered = link.lower()
        if 'contact' in lowered:
            score += 3
        if 'quote' in lowered or 'book' in lowered or 'enquiry' in lowered or 'inquiry' in lowered:
            score += 2
        ranked.append((score, link))
    ranked.sort(reverse=True)
    return ranked[0][1]


def enrich_row(row: Dict[str, str]) -> Dict[str, str]:
    website = normalize_url(row.get("website", ""))
    if not website:
        return set_empty_enrichment(row, "No website to enrich", "no")

    final_url, html = fetch(website)
    if not final_url or not html:
        return set_empty_enrichment(row, "Website listed but page could not be loaded", "unknown")

    emails = extract_emails(html)
    phones = extract_phones(html)
    html_lower = html.lower()
    socials = detect_socials(html_lower)
    directories = detect_directories(html_lower)
    social_urls = extract_social_urls(final_url, html)
    deep_links = extract_internal_links(final_url, html)
    contact_links = extract_contact_links(final_url, html)

    for link in deep_links:
        _, deep_html = fetch(link)
        if not deep_html:
            continue
        deep_lower = deep_html.lower()
        emails |= extract_emails(deep_html)
        phones |= extract_phones(deep_html)
        socials |= detect_socials(deep_lower)
        directories |= detect_directories(deep_lower)
        deep_socials = extract_social_urls(link, deep_html)
        for key, value in deep_socials.items():
            if value and not social_urls.get(key):
                social_urls[key] = value
        if detect_contact_hints(deep_lower) == "yes":
            html_lower += " contact"

    row["enriched_final_url"] = final_url
    row["enriched_page_title"] = extract_title(html)
    normalized_phones = dedupe_phone_variants(phones)
    row["enriched_emails_found"] = " ; ".join(sorted(emails))
    row["enriched_phones_found"] = " ; ".join(normalized_phones[:8])
    row["enriched_best_phone"] = choose_best_phone(normalized_phones, row.get("phone", ""))
    row["enriched_contact_hints"] = detect_contact_hints(html_lower)
    row["enriched_contact_page_urls"] = " ; ".join(contact_links)
    row["enriched_contact_page_best_url"] = choose_best_contact_url(contact_links)
    row["enriched_social_links"] = ", ".join(sorted(socials))
    row["enriched_facebook_url"] = social_urls.get("facebook", "")
    row["enriched_instagram_url"] = social_urls.get("instagram", "")
    row["enriched_linkedin_url"] = social_urls.get("linkedin", "")
    row["enriched_youtube_url"] = social_urls.get("youtube", "")
    row["enriched_tiktok_url"] = social_urls.get("tiktok", "")

    best_confidence = "none"
    best_reason = "No social URL"
    best_score = 0
    for key in ["facebook", "instagram", "linkedin", "youtube", "tiktok"]:
        url = social_urls.get(key, "")
        result = score_social_relevance(row.get("name", ""), url)
        row[f"enriched_{key}_relevance_score"] = str(result.score)
        row[f"enriched_{key}_relevance_confidence"] = result.confidence
        row[f"enriched_{key}_relevance_reason"] = result.reason
        if result.score > best_score:
            best_score = result.score
            best_confidence = result.confidence
            best_reason = f"{key}: {result.reason}"

    row["enriched_social_relevance_best_score"] = str(best_score)
    row["enriched_social_relevance_best_confidence"] = best_confidence
    row["enriched_social_relevance_best_reason"] = best_reason
    row["enriched_directory_mentions"] = ", ".join(sorted(directories))
    row["enriched_deep_pages_checked"] = str(len(deep_links))
    row["enriched_deep_page_urls"] = " ; ".join(deep_links)
    row["enriched_notes"] = "Deep website enrichment completed"
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
