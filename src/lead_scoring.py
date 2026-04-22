#!/usr/bin/env python3
import re
from dataclasses import dataclass
from typing import List, Tuple

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

CRM_TOOL_PATTERNS = {
    "hubspot": ["hubspot", "hsforms", "hubspotusercontent"],
    "gohighlevel": ["gohighlevel", "leadconnectorhq", "msgsndr"],
    "salesforce": ["salesforce", "force.com", "pardot"],
    "zoho": ["zoho", "zohopublic", "salesiq"],
    "activecampaign": ["activecampaign", "acems", "activehosted"],
    "mailchimp": ["mailchimp", "list-manage.com"],
    "jobber": ["jobber", "getjobber.com"],
    "servicem8": ["servicem8"],
    "housecall_pro": ["housecallpro"],
    "calendly": ["calendly"],
    "typeform": ["typeform"],
    "jotform": ["jotform"],
    "gravity_forms": ["gform_wrapper", "gravity forms"],
    "wpforms": ["wpforms"],
    "tawk": ["tawk.to"],
    "intercom": ["intercom"],
    "drift": ["drift.com"],
}

FORM_PATTERNS = {
    "contact_form": ["<form", "contact form"],
    "quote_form": ["request a quote", "get a quote", "free quote", "quote form"],
    "booking_form": ["book now", "make a booking", "schedule service", "schedule now"],
    "callback_request": ["request a callback", "call me back"],
}

BOOKING_PATTERNS = [
    "book now",
    "online booking",
    "schedule service",
    "book online",
    "appointment",
    "calendly",
]

CHAT_PATTERNS = ["live chat", "chat with us", "tawk.to", "intercom", "drift"]
PORTAL_PATTERNS = ["client portal", "customer portal", "member login", "account login", "portal login"]
COMPLEXITY_PATTERNS = {
    "emergency_service": ["24/7", "emergency service", "same day service", "after hours"],
    "multi_service": ["services", "our services", "what we do"],
    "service_areas": ["service areas", "areas we service", "suburbs we service"],
    "team_signals": ["our team", "meet the team", "our technicians", "our electricians", "our plumbers"],
}

DEEP_PAGE_HINTS = ["contact", "about", "quote", "book", "booking", "service", "services", "emergency"]
MAX_DEEP_PAGES = 4
STRONG_HOMEPAGE_SIGNAL_SCORE = 5


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
    crm_maturity_score: int = 0
    crm_maturity_level: str = "unknown"
    crm_detected_tools: str = ""
    crm_detected_forms: str = ""
    crm_detected_booking_signals: str = ""
    crm_detected_chat_widgets: str = ""
    crm_detected_portal_signals: str = ""
    crm_operational_complexity: str = ""
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


def extract_internal_links(base_url: str, html: str) -> List[str]:
    links = re.findall(r'href=["\']([^"\'#]+)["\']', html, re.I)
    found = []
    for href in links:
        if href.startswith('mailto:') or href.startswith('tel:'):
            continue
        if href.startswith('http://') or href.startswith('https://'):
            absolute = href
        elif href.startswith('/'):
            absolute = base_url.rstrip('/') + href
        else:
            absolute = base_url.rstrip('/') + '/' + href.lstrip('./')
        lowered = absolute.lower()
        if any(lowered.endswith(ext) for ext in ['.css', '.js', '.png', '.jpg', '.jpeg', '.svg', '.webp', '.gif', '.pdf', '.xml']):
            continue
        if any(hint in lowered for hint in DEEP_PAGE_HINTS):
            found.append(absolute)
    deduped = []
    seen = set()
    for link in found:
        if link not in seen:
            seen.add(link)
            deduped.append(link)
    return deduped[:MAX_DEEP_PAGES]


def detect_signal_set(html_lower: str) -> dict:
    detected_tools = []
    for tool, patterns in CRM_TOOL_PATTERNS.items():
        if any(pattern in html_lower for pattern in patterns):
            detected_tools.append(tool)

    detected_forms = []
    for form_name, patterns in FORM_PATTERNS.items():
        if any(pattern in html_lower for pattern in patterns):
            detected_forms.append(form_name)

    booking_signals = sorted({pattern for pattern in BOOKING_PATTERNS if pattern in html_lower})
    chat_widgets = sorted({pattern for pattern in CHAT_PATTERNS if pattern in html_lower})
    portal_signals = sorted({pattern for pattern in PORTAL_PATTERNS if pattern in html_lower})
    complexity_signals = sorted({name for name, patterns in COMPLEXITY_PATTERNS.items() if any(pattern in html_lower for pattern in patterns)})

    return {
        "detected_tools": detected_tools,
        "detected_forms": detected_forms,
        "booking_signals": booking_signals,
        "chat_widgets": chat_widgets,
        "portal_signals": portal_signals,
        "complexity_signals": complexity_signals,
    }


def signal_maturity_score(signal_set: dict) -> int:
    maturity_score = 0
    if signal_set["detected_tools"]:
        maturity_score += min(4, len(signal_set["detected_tools"]))
    if signal_set["detected_forms"]:
        maturity_score += min(3, len(signal_set["detected_forms"]))
    if signal_set["booking_signals"]:
        maturity_score += 2
    if signal_set["chat_widgets"]:
        maturity_score += 1
    if signal_set["portal_signals"]:
        maturity_score += 2
    return maturity_score


def merge_signal_sets(base: dict, extra: dict) -> dict:
    merged = {}
    for key in ["detected_tools", "detected_forms", "booking_signals", "chat_widgets", "portal_signals", "complexity_signals"]:
        merged[key] = sorted(set(base.get(key, [])) | set(extra.get(key, [])))
    return merged


def scan_crm_signals(final_url: str, html: str) -> dict:
    homepage_signals = detect_signal_set(html.lower())
    combined_signals = homepage_signals

    if signal_maturity_score(homepage_signals) < STRONG_HOMEPAGE_SIGNAL_SCORE:
        for link in extract_internal_links(final_url, html):
            fetched_url, fetched_html = fetch_website(link)
            if fetched_url and fetched_html:
                deep_signals = detect_signal_set(fetched_html.lower())
                combined_signals = merge_signal_sets(combined_signals, deep_signals)
                if signal_maturity_score(combined_signals) >= STRONG_HOMEPAGE_SIGNAL_SCORE:
                    break

    maturity_score = signal_maturity_score(combined_signals)

    if maturity_score >= 7:
        maturity_level = "high"
    elif maturity_score >= 4:
        maturity_level = "medium"
    else:
        maturity_level = "low"

    complexity_count = len(combined_signals["complexity_signals"])
    if complexity_count >= 3:
        operational_complexity = "high"
    elif complexity_count >= 1:
        operational_complexity = "medium"
    else:
        operational_complexity = "low"

    return {
        "crm_maturity_score": maturity_score,
        "crm_maturity_level": maturity_level,
        "crm_detected_tools": ", ".join(combined_signals["detected_tools"]),
        "crm_detected_forms": ", ".join(combined_signals["detected_forms"]),
        "crm_detected_booking_signals": ", ".join(combined_signals["booking_signals"]),
        "crm_detected_chat_widgets": ", ".join(combined_signals["chat_widgets"]),
        "crm_detected_portal_signals": ", ".join(combined_signals["portal_signals"]),
        "crm_operational_complexity": operational_complexity,
    }


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

    crm_signals = scan_crm_signals(final_url, html)

    audit = LeadAudit(
        website_status="has_website",
        website_quality=quality,
        website_quality_score=score,
        website_notes="; ".join(notes),
        has_contact_form=has_contact_form,
        has_quote_intent=has_quote_intent,
        has_recent_year_signal=recent_signal,
        crm_maturity_score=crm_signals["crm_maturity_score"],
        crm_maturity_level=crm_signals["crm_maturity_level"],
        crm_detected_tools=crm_signals["crm_detected_tools"],
        crm_detected_forms=crm_signals["crm_detected_forms"],
        crm_detected_booking_signals=crm_signals["crm_detected_booking_signals"],
        crm_detected_chat_widgets=crm_signals["crm_detected_chat_widgets"],
        crm_detected_portal_signals=crm_signals["crm_detected_portal_signals"],
        crm_operational_complexity=crm_signals["crm_operational_complexity"],
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
        crm_reasons.append("No website suggests weak digital lead handling stack")
    elif audit.website_quality == "weak":
        website_score += 4
        website_reasons.append("Weak or unreachable website")
        crm_score += 3
        crm_reasons.append("Weak website often means weak process layer")
    elif audit.website_quality == "basic":
        website_score += 2
        website_reasons.append("Basic website")
        crm_score += 3
        crm_reasons.append("Basic website may hide weak lead handling")
    elif audit.website_quality == "modern":
        website_score -= 2
        website_reasons.append("Modern website lowers redesign urgency")

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
        crm_score += 2
        website_reasons.append("No visible quote funnel")
        crm_reasons.append("No visible quote funnel")

    if audit.has_contact_form == "no" and audit.website_status == "has_website":
        website_score += 1
        crm_score += 2
        website_reasons.append("No visible contact form")
        crm_reasons.append("No visible contact capture")

    if audit.crm_maturity_level == "low" and audit.website_status == "has_website":
        crm_score += 3
        crm_reasons.append("Low CRM/process maturity detected")
    elif audit.crm_maturity_level == "medium":
        crm_score += 1
        crm_reasons.append("Medium CRM/process maturity leaves room for improvement")
    elif audit.crm_maturity_level == "high":
        crm_score -= 3
        crm_reasons.append("High CRM/process maturity lowers urgency")

    if audit.crm_operational_complexity == "high":
        crm_score += 3
        crm_reasons.append("High operational complexity")
    elif audit.crm_operational_complexity == "medium":
        crm_score += 2
        crm_reasons.append("Moderate operational complexity")

    website_priority = priority_from_score(website_score)
    crm_priority = priority_from_score(crm_score)

    if website_priority == "high" and crm_priority == "high":
        best_offer_type = "website_and_crm"
        outreach_angle = "Lead with website improvement, then position CRM and quoting automation as the next lift."
    elif website_score > crm_score:
        best_offer_type = "website"
        outreach_angle = "Lead with website upgrade, trust, and conversion improvements."
    elif crm_score > website_score:
        best_offer_type = "crm"
        outreach_angle = "Lead with quoting, booking, follow-up, and CRM workflow improvements."
    else:
        best_offer_type = "website_and_crm"
        outreach_angle = "Present website and CRM together as one growth system."

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
