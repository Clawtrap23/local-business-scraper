#!/usr/bin/env python3
import argparse
import csv
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Set

from openpyxl import Workbook

from src.google_maps_scraper import Business, GoogleMapsScraper, clean_text
from src.lead_scoring import classify_website

DEFAULT_SUBURBS_FILE = "config/brisbane-cbd-nearby-suburbs.txt"
DEFAULT_KEYWORDS_FILE = "config/tradie-keywords.txt"
DEFAULT_OUTPUT_DIR = "output"
CHECKPOINT_BASENAME = "tradies-brisbane-cbd-nearby-suburbs"
STATE_FILENAME = f"{CHECKPOINT_BASENAME}-state.json"
AUDIT_CACHE_FILENAME = f"{CHECKPOINT_BASENAME}-audit-cache.json"
METRICS_FILENAME = f"{CHECKPOINT_BASENAME}-metrics.json"
XLSX_CHECKPOINT_EVERY = 5


def read_lines(path: Path) -> List[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")]


def business_key(row: Business) -> str:
    website = clean_text(row.website).lower()
    phone = clean_text(row.phone).lower()
    name = clean_text(row.name).lower()
    address = clean_text(row.address).lower()
    category = clean_text(row.category).lower()
    if website:
        return f"website::{website}"
    if phone and name:
        return f"phone::{name}::{phone}"
    return f"fallback::{name}::{address}::{category}"


def dedupe_businesses(rows: List[Business]) -> List[Business]:
    seen: Set[str] = set()
    deduped: List[Business] = []
    for row in rows:
        key = business_key(row)
        if key in seen:
            continue
        seen.add(key)
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
    parser.add_argument("--fresh", action="store_true", help="Ignore saved run state and start from scratch")
    return parser.parse_args()


def apply_audit(row: Business, audit_cache: Dict[str, dict]) -> Business:
    key = business_key(row)
    cached = audit_cache.get(key)
    if cached:
        for field, value in cached.items():
            setattr(row, field, value)
        return row

    audit = classify_website(row)
    row.website_status = audit.website_status
    row.website_quality = audit.website_quality
    row.website_quality_score = str(audit.website_quality_score)
    row.website_notes = audit.website_notes
    row.has_contact_form = audit.has_contact_form
    row.has_quote_intent = audit.has_quote_intent
    row.has_recent_year_signal = audit.has_recent_year_signal
    row.lead_score = str(audit.lead_score)
    row.lead_priority = audit.lead_priority
    row.target_reason = audit.target_reason
    row.website_lead_score = str(audit.website_lead_score)
    row.website_lead_priority = audit.website_lead_priority
    row.website_lead_reason = audit.website_lead_reason
    row.crm_lead_score = str(audit.crm_lead_score)
    row.crm_lead_priority = audit.crm_lead_priority
    row.crm_lead_reason = audit.crm_lead_reason
    row.crm_maturity_score = str(audit.crm_maturity_score)
    row.crm_maturity_level = audit.crm_maturity_level
    row.crm_detected_tools = audit.crm_detected_tools
    row.crm_detected_forms = audit.crm_detected_forms
    row.crm_detected_booking_signals = audit.crm_detected_booking_signals
    row.crm_detected_chat_widgets = audit.crm_detected_chat_widgets
    row.crm_detected_portal_signals = audit.crm_detected_portal_signals
    row.crm_operational_complexity = audit.crm_operational_complexity
    row.best_offer_type = audit.best_offer_type
    row.outreach_angle = audit.outreach_angle
    audit_cache[key] = {
        "website_status": row.website_status,
        "website_quality": row.website_quality,
        "website_quality_score": row.website_quality_score,
        "website_notes": row.website_notes,
        "has_contact_form": row.has_contact_form,
        "has_quote_intent": row.has_quote_intent,
        "has_recent_year_signal": row.has_recent_year_signal,
        "lead_score": row.lead_score,
        "lead_priority": row.lead_priority,
        "target_reason": row.target_reason,
        "website_lead_score": row.website_lead_score,
        "website_lead_priority": row.website_lead_priority,
        "website_lead_reason": row.website_lead_reason,
        "crm_lead_score": row.crm_lead_score,
        "crm_lead_priority": row.crm_lead_priority,
        "crm_lead_reason": row.crm_lead_reason,
        "crm_maturity_score": row.crm_maturity_score,
        "crm_maturity_level": row.crm_maturity_level,
        "crm_detected_tools": row.crm_detected_tools,
        "crm_detected_forms": row.crm_detected_forms,
        "crm_detected_booking_signals": row.crm_detected_booking_signals,
        "crm_detected_chat_widgets": row.crm_detected_chat_widgets,
        "crm_detected_portal_signals": row.crm_detected_portal_signals,
        "crm_operational_complexity": row.crm_operational_complexity,
        "best_offer_type": row.best_offer_type,
        "outreach_angle": row.outreach_angle,
    }
    return row


def write_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"completed_queries": [], "raw_rows": [], "query_metrics": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"completed_queries": [], "raw_rows": [], "query_metrics": []}


def load_audit_cache(path: Path) -> Dict[str, dict]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_audit_cache(path: Path, cache: Dict[str, dict]) -> None:
    path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


def write_metrics(path: Path, metrics: dict) -> None:
    path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")


def write_checkpoint(output_dir: Path, rows: List[Business], query_index: int, final: bool = False) -> tuple[Path, Path | None]:
    csv_path = output_dir / f"{CHECKPOINT_BASENAME}.csv"
    write_csv(csv_path, rows)

    xlsx_path = output_dir / f"{CHECKPOINT_BASENAME}.xlsx"
    if final or query_index % XLSX_CHECKPOINT_EVERY == 0:
        write_xlsx(xlsx_path, rows)
        return csv_path, xlsx_path
    return csv_path, None


def main() -> int:
    args = parse_args()
    run_started = time.time()
    suburbs = read_lines(Path(args.suburbs_file))
    keywords = read_lines(Path(args.keywords_file))
    scraper = GoogleMapsScraper(headless=not args.headed)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    state_path = output_dir / STATE_FILENAME
    audit_cache_path = output_dir / AUDIT_CACHE_FILENAME
    metrics_path = output_dir / METRICS_FILENAME

    if args.fresh:
        state = {"completed_queries": [], "raw_rows": [], "query_metrics": []}
        audit_cache: Dict[str, dict] = {}
    else:
        state = load_state(state_path)
        audit_cache = load_audit_cache(audit_cache_path)

    completed_queries = set(state.get("completed_queries", []))
    raw_rows = [Business(**row) for row in state.get("raw_rows", [])]
    query_metrics = list(state.get("query_metrics", []))
    all_rows: List[Business] = raw_rows[:]
    processed_queries = len(completed_queries)
    total_queries = len(suburbs) * len(keywords)

    csv_path: Path | None = None
    xlsx_path: Path | None = None
    deduped: List[Business] = dedupe_businesses(all_rows)
    audited: List[Business] = [apply_audit(row, audit_cache) for row in deduped]

    for suburb in suburbs:
        for keyword in keywords:
            query = f"{keyword} in {suburb} Brisbane"
            if query in completed_queries:
                print(f"Skipping completed query: {query}")
                continue

            query_started = time.time()
            print(f"Running ({processed_queries + 1}/{total_queries}): {query}")
            batch_rows = scraper.scrape_query(query, args.total_per_query)
            all_rows.extend(batch_rows)
            completed_queries.add(query)
            processed_queries += 1

            deduped = dedupe_businesses(all_rows)
            audited = [apply_audit(row, audit_cache) for row in deduped]

            csv_path, maybe_xlsx_path = write_checkpoint(output_dir, audited, processed_queries)
            if maybe_xlsx_path:
                xlsx_path = maybe_xlsx_path

            query_duration = round(time.time() - query_started, 3)
            metric = {
                "query": query,
                "query_index": processed_queries,
                "batch_rows": len(batch_rows),
                "deduped_rows_after_query": len(deduped),
                "audited_rows_after_query": len(audited),
                "duration_seconds": query_duration,
                "wrote_xlsx": bool(maybe_xlsx_path),
            }
            query_metrics.append(metric)

            state = {
                "completed_queries": sorted(completed_queries),
                "raw_rows": [asdict(row) for row in all_rows],
                "query_metrics": query_metrics,
            }
            write_state(state_path, state)
            save_audit_cache(audit_cache_path, audit_cache)
            write_metrics(
                metrics_path,
                {
                    "total_duration_seconds": round(time.time() - run_started, 3),
                    "processed_queries": processed_queries,
                    "total_queries": total_queries,
                    "query_metrics": query_metrics,
                },
            )

            print(f"Query duration seconds: {query_duration}")
            print(f"Checkpoint rows after query: {len(audited)}")
            print(f"Checkpoint CSV: {csv_path}")
            if maybe_xlsx_path:
                print(f"Checkpoint XLSX: {maybe_xlsx_path}")
            else:
                print("Checkpoint XLSX: skipped this round")

    total_duration = round(time.time() - run_started, 3)
    csv_path, xlsx_path = write_checkpoint(output_dir, audited, processed_queries or 1, final=True)
    state = {
        "completed_queries": sorted(completed_queries),
        "raw_rows": [asdict(row) for row in all_rows],
        "query_metrics": query_metrics,
    }
    write_state(state_path, state)
    save_audit_cache(audit_cache_path, audit_cache)
    write_metrics(
        metrics_path,
        {
            "total_duration_seconds": total_duration,
            "processed_queries": processed_queries,
            "total_queries": total_queries,
            "query_metrics": query_metrics,
            "raw_rows": len(all_rows),
            "deduped_rows": len(deduped),
            "audited_rows": len(audited),
        },
    )

    print(f"Total duration seconds: {total_duration}")
    print(f"Raw rows: {len(all_rows)}")
    print(f"Deduped rows: {len(deduped)}")
    print(f"Audited rows: {len(audited)}")
    print(f"CSV: {csv_path}")
    print(f"XLSX: {xlsx_path}")
    print(f"State: {state_path}")
    print(f"Audit cache: {audit_cache_path}")
    print(f"Metrics: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
