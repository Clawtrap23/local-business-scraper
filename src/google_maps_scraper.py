#!/usr/bin/env python3
import argparse
import csv
import logging
import re
import sys
import urllib.parse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List

from openpyxl import Workbook
from playwright.sync_api import Browser, Page, sync_playwright

DEFAULT_OUTPUT_DIR = "output"
DEFAULT_QUERIES = [
    "plumbers in Brisbane CBD",
    "locksmiths in Brisbane CBD",
    "carpenters in Brisbane CBD",
    "solar panel installers in Brisbane CBD",
    "waterproofing services in Brisbane CBD",
    "roofers in Brisbane CBD",
    "electricians in Brisbane CBD",
    "smart home installers in Brisbane CBD",
    "security system installers in Brisbane CBD",
    "stone masons in Brisbane CBD",
    "asbestos removal in Brisbane CBD",
    "elevator technicians in Brisbane CBD",
]


@dataclass
class Business:
    query: str = ""
    name: str = ""
    category: str = ""
    address: str = ""
    website: str = ""
    phone: str = ""
    rating: str = ""
    reviews_count: str = ""
    services: str = ""
    hours: str = ""
    maps_url: str = ""
    website_status: str = ""
    website_quality: str = ""
    website_quality_score: str = ""
    website_notes: str = ""
    has_contact_form: str = ""
    has_quote_intent: str = ""
    has_recent_year_signal: str = ""
    lead_score: str = ""
    lead_priority: str = ""
    target_reason: str = ""
    website_lead_score: str = ""
    website_lead_priority: str = ""
    website_lead_reason: str = ""
    crm_lead_score: str = ""
    crm_lead_priority: str = ""
    crm_lead_reason: str = ""
    best_offer_type: str = ""
    outreach_angle: str = ""


def clean_text(value: str) -> str:
    if not value:
        return ""
    value = value.replace("\u202f", " ")
    value = re.sub(r"[\ue000-\uf8ff]", "", value)
    value = value.replace("", "").replace("", "").replace("", "").replace("", "")
    value = re.sub(r"\s+", " ", value.replace("\n", " ")).strip()
    return value


class GoogleMapsScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless

    def _launch_browser(self) -> Browser:
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=self.headless)
        browser._openclaw_playwright = playwright
        return browser

    @staticmethod
    def _close_browser(browser: Browser) -> None:
        playwright = getattr(browser, "_openclaw_playwright", None)
        browser.close()
        if playwright:
            playwright.stop()

    @staticmethod
    def _dismiss_consent(page: Page) -> None:
        for label in [
            'button:has-text("Accept all")',
            'button:has-text("I agree")',
            'button[aria-label*="Accept"]',
            'button:has-text("Reject all")',
        ]:
            try:
                locator = page.locator(label)
                if locator.count() > 0:
                    locator.first.click(timeout=2000)
                    page.wait_for_timeout(1000)
                    return
            except Exception:
                continue

    @staticmethod
    def _open_search(page: Page, query: str) -> None:
        encoded_query = urllib.parse.quote_plus(query.strip())
        page.goto(f"https://www.google.com/maps/search/{encoded_query}", timeout=60000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(5000)
        GoogleMapsScraper._dismiss_consent(page)
        page.wait_for_timeout(3000)

    @staticmethod
    def _collect_listing_links(page: Page, total: int) -> List[str]:
        anchor_selector = 'a[href*="/maps/place/"]'
        try:
            results_panel = page.locator('div[role="feed"], div[aria-label*="Results for"], div[aria-label*="Results"]')
            if results_panel.count() > 0:
                results_panel.first.hover(timeout=3000)
        except Exception:
            pass
        previous = -1
        stable_rounds = 0
        max_scrolls = max(8, total * 2)
        scrolls = 0
        while True:
            anchors = page.locator(anchor_selector)
            count = anchors.count()
            logging.info("Found %s listing anchors so far", count)
            if count >= total:
                break
            if count == previous:
                stable_rounds += 1
            else:
                stable_rounds = 0
            if stable_rounds >= 4 or scrolls >= max_scrolls:
                break
            previous = count
            scrolls += 1
            try:
                page.mouse.wheel(0, 18000)
            except Exception:
                pass
            page.wait_for_timeout(2500)
        hrefs = []
        for i in range(min(total, page.locator(anchor_selector).count())):
            try:
                href = page.locator(anchor_selector).nth(i).get_attribute("href")
                if href and href not in hrefs:
                    hrefs.append(href)
            except Exception:
                continue
        return hrefs

    @staticmethod
    def _text(page: Page, selector: str) -> str:
        try:
            locator = page.locator(selector)
            if locator.count() > 0:
                return clean_text(locator.first.inner_text(timeout=4000).strip())
        except Exception:
            return ""
        return ""

    @staticmethod
    def _attr(page: Page, selector: str, attr: str) -> str:
        try:
            locator = page.locator(selector)
            if locator.count() > 0:
                value = locator.first.get_attribute(attr, timeout=4000)
                return clean_text((value or "").strip())
        except Exception:
            return ""
        return ""

    def _extract_business(self, page: Page, query: str, url: str) -> Business:
        page.goto(url, timeout=60000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3500)
        name = self._text(page, 'h1, h1.DUwDvf')
        category = self._text(page, 'button.DkEaL, button[jsaction*="pane.rating.category"]')
        address = self._text(page, 'button[data-item-id="address"] .fontBodyMedium, button[data-item-id="address"]')
        website = self._text(page, 'a[data-item-id="authority"] .fontBodyMedium, a[data-item-id="authority"]')
        phone = self._text(page, 'button[data-item-id^="phone:"] .fontBodyMedium, button[data-item-id^="phone:"]')
        rating = self._text(page, 'div.F7nice span[aria-hidden="true"], span.ceNzKf[role="img"]')
        reviews_count = self._attr(page, 'button[jsaction*="pane.rating.moreReviews"]', 'aria-label') or self._text(page, 'button[jsaction*="pane.rating.moreReviews"]')
        hours = self._text(page, 'button[data-item-id*="oh"] .fontBodyMedium, div.MkV9 span.ZDu9vd span:nth-child(2)')

        service_bits = []
        for selector in ['div.LTs0Rc']:
            try:
                loc = page.locator(selector)
                for i in range(min(loc.count(), 4)):
                    text = loc.nth(i).inner_text(timeout=2000).strip()
                    if text:
                        service_bits.append(clean_text(text.replace('\n', ' | ')))
            except Exception:
                continue

        return Business(
            query=query,
            name=name,
            category=category,
            address=address,
            website=website,
            phone=phone,
            rating=rating,
            reviews_count=reviews_count,
            services=" || ".join(service_bits),
            hours=hours,
            maps_url=url,
        )

    def scrape_query(self, query: str, total: int) -> List[Business]:
        browser = self._launch_browser()
        page = browser.new_page()
        try:
            self._open_search(page, query)
            links = self._collect_listing_links(page, total)
            logging.info("Collected %s links for query: %s", len(links), query)
            businesses = []
            for link in links:
                try:
                    business = self._extract_business(page, query, link)
                    if business.name:
                        businesses.append(business)
                except Exception as exc:
                    logging.warning("Failed to extract %s: %s", link, exc)
            return businesses
        finally:
            self._close_browser(browser)


def write_csv(path: Path, rows: Iterable[Business]) -> None:
    rows = list(rows)
    fieldnames = list(asdict(rows[0]).keys()) if rows else list(Business().__dict__.keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_xlsx(path: Path, rows: Iterable[Business]) -> None:
    rows = list(rows)
    fieldnames = list(asdict(rows[0]).keys()) if rows else list(Business().__dict__.keys())
    wb = Workbook()
    ws = wb.active
    ws.title = "Google Maps"
    ws.append(fieldnames)
    for row in rows:
        ws.append([asdict(row)[field] for field in fieldnames])
    wb.save(path)


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Google Maps listings for tradies and small businesses.")
    parser.add_argument("queries", nargs="*", help="One or more Google Maps search queries")
    parser.add_argument("--total", type=int, default=10, help="Maximum results per query")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--headed", action="store_true", help="Use a visible browser")
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    args = parse_args()
    queries = args.queries or DEFAULT_QUERIES
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    scraper = GoogleMapsScraper(headless=not args.headed)
    all_rows: List[Business] = []
    try:
        for query in queries:
            logging.info("Running query: %s", query)
            all_rows.extend(scraper.scrape_query(query, args.total))
        csv_path = output_dir / "google-maps-results.csv"
        xlsx_path = output_dir / "google-maps-results.xlsx"
        write_csv(csv_path, all_rows)
        write_xlsx(xlsx_path, all_rows)
        print(f"Saved {len(all_rows)} rows")
        print(f"CSV: {csv_path}")
        print(f"XLSX: {xlsx_path}")
        return 0
    except Exception as exc:
        logging.exception("Google Maps scrape failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
