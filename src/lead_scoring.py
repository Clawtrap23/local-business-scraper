#!/usr/bin/env python3
import re
from dataclasses import dataclass
from typing import Tuple

import requests

from src.google_maps_scraper import Business, clean_text

TIMEOUT = 20
HEADERS = {"User-Agent": "local-business-scraper/lead-audit/1.0"}

HIGH_VALUE_CATEGORIES = {
    "plumber",
    "electrician",
    "locksmith",
    "roofer",
    "roofing contractor",
    "waterproofing service",
    "solar energy contractor",
    "security system supplier",
    "security system installer",
    "garage door supplier",
    "carpenter",
    "contractor",
}


@dataclass
class LeadAudit:
    website_status: str = "unknown"
    website_quality: str = "unknown"
    website_quality_score: int = 0
    website_notes: str = ""
    has_contact_form: str = "unknown"
    has_quote_intent: str = "unknown"
    has_recent_year_signal: str = "unknown"
    lead_score: int = 0
    lead_priority: str = "unknown"
    target_reason: str = ""


def normalize_website(url: str) -> str:
    url = clean_text(url)
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"https://{url}"


def fetch_website(url: str) -> Tuple[str, str]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        response.raise_for_status()
        return response.url, response.text
    except Exception:
        return "", ""


def detect_recent_year_signal(html: str) -> str:
    years = re.findall(r"20(1[8-9]|2[0-9]|3[0-5])", html)
    return "yes" if years else "no"


def classify_website(business: Business) -> LeadAudit:
    url = normalize_website(business.website)
    if not url:
        audit = LeadAudit(
            website_status="no_website",
            website_quality="none",
            website_quality_score=0,
            website_notes="No website listed in Google Maps",
            has_contact_form="no",
            has_quote_intent="no",
            has_recent_year_signal="no",
        )
        return score_lead(business, audit)

    final_url, html = fetch_website(url)
    if not final_url or not html:
        audit = LeadAudit(
            website_status="website_unreachable",
            website_quality="weak",
            website_quality_score=1,
            website_notes="Website listed but could not be loaded",
            has_contact_form="unknown",
            has_quote_intent="unknown",
            has_recent_year_signal="unknown",
        )
        return score_lead(business, audit)

    html_lower = html.lower()
    has_contact_form = "yes" if "<form" in html_lower and any(k in html_lower for k in ["contact", "quote", "enquiry", "inquiry"]) else "no"
    has_quote_intent = "yes" if any(k in html_lower for k in ["request a quote", "get a quote", "free quote", "book now", "call now"]) else "no"
    recent_signal = detect_recent_year_signal(html)
    is_https = final_url.startswith("https://")

    score = 1
    notes = []
    if is_https:
        score += 1
        notes.append("Uses HTTPS")
    else:
        notes.append("No HTTPS")
    if has_contact_form == "yes":
        score += 1
        notes.append("Has contact form")
    if has_quote_intent == "yes":
        score += 1
        notes.append("Has quote or booking intent")
    if recent_signal == "yes":
        score += 1
        notes.append("Recent year signal found")

    if score <= 2:
        quality = "weak"
    elif score == 3:
        quality = "basic"
    else:
        quality = "modern"

    audit = LeadAudit(
        website_status="has_website",
        website_quality=quality,
        website_quality_score=score,
        website_notes="; ".join(notes),
        has_contact_form=has_contact_form,
        has_quote_intent=has_quote_intent,
        has_recent_year_signal=recent_signal,
    )
    return score_lead(business, audit)


def score_lead(business: Business, audit: LeadAudit) -> LeadAudit:
    score = 0
    reasons = []

    category = clean_text(business.category).lower()
    if category in HIGH_VALUE_CATEGORIES or any(k in category for k in ["plumb", "electric", "locksmith", "roof", "waterproof", "solar", "security", "carpenter"]):
        score += 2
        reasons.append("High-value tradie category")

    if audit.website_status == "no_website":
        score += 5
        reasons.append("No website")
    elif audit.website_quality == "weak":
        score += 4
        reasons.append("Weak or unreachable website")
    elif audit.website_quality == "basic":
        score += 2
        reasons.append("Basic website")
    elif audit.website_quality == "modern":
        score -= 2
        reasons.append("Modern website lowers website-redesign urgency")

    if business.phone:
        score += 1
        reasons.append("Phone listed")

    rating_text = clean_text(business.rating)
    try:
        rating_value = float(re.findall(r"\d+(?:\.\d+)?", rating_text)[0]) if rating_text else 0.0
    except Exception:
        rating_value = 0.0
    if rating_value >= 4.5:
        score += 1
        reasons.append("Strong reviews imply active business")

    if audit.has_quote_intent == "no" and audit.website_status == "has_website":
        score += 1
        reasons.append("No visible quote funnel")

    if audit.has_contact_form == "no" and audit.website_status == "has_website":
        score += 1
        reasons.append("No visible contact form")

    if score >= 7:
        priority = "high"
    elif score >= 4:
        priority = "medium"
    else:
        priority = "low"

    audit.lead_score = score
    audit.lead_priority = priority
    audit.target_reason = "; ".join(reasons)
    return audit
