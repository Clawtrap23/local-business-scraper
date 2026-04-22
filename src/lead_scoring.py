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
    website_lead_score: int = 0
    website_lead_priority: str = "unknown"
    website_lead_reason: str = ""
    crm_lead_score: int = 0
    crm_lead_priority: str = "unknown"
    crm_lead_reason: str = ""
    best_offer_type: str = "unknown"
    outreach_angle: str = ""


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


def priority_from_score(score: int) -> str:
    if score >= 7:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def score_lead(business: Business, audit: LeadAudit) -> LeadAudit:
    category = clean_text(business.category).lower()
    rating_text = clean_text(business.rating)
    try:
        rating_value = float(re.findall(r"\d+(?:\.\d+)?", rating_text)[0]) if rating_text else 0.0
    except Exception:
        rating_value = 0.0

    is_high_value_tradie = category in HIGH_VALUE_CATEGORIES or any(k in category for k in ["plumb", "electric", "locksmith", "roof", "waterproof", "solar", "security", "carpenter"])

    website_score = 0
    website_reasons = []
    crm_score = 0
    crm_reasons = []

    if is_high_value_tradie:
        website_score += 2
        crm_score += 2
        website_reasons.append("High-value tradie category")
        crm_reasons.append("High-value tradie category")

    if audit.website_status == "no_website":
        website_score += 5
        website_reasons.append("No website")
        crm_score += 2
        crm_reasons.append("No website suggests weak lead handling stack")
    elif audit.website_quality == "weak":
        website_score += 4
        website_reasons.append("Weak or unreachable website")
        crm_score += 2
        crm_reasons.append("Weak website often means weak process layer")
    elif audit.website_quality == "basic":
        website_score += 2
        website_reasons.append("Basic website")
        crm_score += 3
        crm_reasons.append("Basic website may hide weak lead handling")
    elif audit.website_quality == "modern":
        website_score -= 2
        website_reasons.append("Modern website lowers redesign urgency")
        crm_score += 2
        crm_reasons.append("Modern website may still need better CRM process")

    if business.phone:
        website_score += 1
        crm_score += 1
        website_reasons.append("Phone listed")
        crm_reasons.append("Phone listed")

    if rating_value >= 4.5:
        website_score += 1
        crm_score += 2
        website_reasons.append("Strong reviews imply active business")
        crm_reasons.append("Strong reviews imply active lead flow")

    if audit.has_quote_intent == "no" and audit.website_status == "has_website":
        website_score += 1
        crm_score += 3
        website_reasons.append("No visible quote funnel")
        crm_reasons.append("No visible quote funnel")

    if audit.has_contact_form == "no" and audit.website_status == "has_website":
        website_score += 1
        crm_score += 2
        website_reasons.append("No visible contact form")
        crm_reasons.append("No visible contact capture")

    website_priority = priority_from_score(website_score)
    crm_priority = priority_from_score(crm_score)

    if website_priority == "high" and crm_priority == "high":
        best_offer_type = "website_and_crm"
        outreach_angle = "Lead with website improvement and follow with CRM/process automation."
    elif website_score > crm_score:
        best_offer_type = "website"
        outreach_angle = "Lead with website upgrade, conversion, and trust improvements."
    elif crm_score > website_score:
        best_offer_type = "crm"
        outreach_angle = "Lead with lead capture, quoting, follow-up, and CRM automation."
    else:
        best_offer_type = "website_and_crm"
        outreach_angle = "Present both website and CRM as a combined growth system."

    combined_score = max(website_score, crm_score)
    combined_priority = priority_from_score(combined_score)
    combined_reasons = sorted(set(website_reasons + crm_reasons))

    audit.lead_score = combined_score
    audit.lead_priority = combined_priority
    audit.target_reason = "; ".join(combined_reasons)
    audit.website_lead_score = website_score
    audit.website_lead_priority = website_priority
    audit.website_lead_reason = "; ".join(website_reasons)
    audit.crm_lead_score = crm_score
    audit.crm_lead_priority = crm_priority
    audit.crm_lead_reason = "; ".join(crm_reasons)
    audit.best_offer_type = best_offer_type
    audit.outreach_angle = outreach_angle
    return audit
