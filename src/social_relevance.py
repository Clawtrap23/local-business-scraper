#!/usr/bin/env python3
import re
from dataclasses import dataclass
from urllib.parse import urlparse


def normalize_name(value: str) -> str:
    value = (value or '').lower()
    value = re.sub(r'[^a-z0-9]+', ' ', value)
    value = re.sub(r'\b(pty|ltd|services|service|brisbane|city|and|the|group)\b', ' ', value)
    value = re.sub(r'\s+', ' ', value).strip()
    return value


def slug_from_url(url: str) -> str:
    parsed = urlparse(url or '')
    parts = [p for p in parsed.path.split('/') if p]
    if not parts:
        return ''
    if parsed.netloc.endswith('facebook.com') and parts[0] == 'profile.php':
        return 'profile'
    if parsed.netloc.endswith('linkedin.com') and len(parts) >= 2:
        return parts[1]
    if parts[0].startswith('@'):
        return parts[0][1:]
    return parts[0]


def token_set(value: str) -> set[str]:
    return {token for token in normalize_name(value).split() if token}


@dataclass
class SocialRelevance:
    score: int
    confidence: str
    reason: str


def score_social_relevance(business_name: str, social_url: str) -> SocialRelevance:
    if not social_url:
        return SocialRelevance(0, 'none', 'No social URL')

    business_tokens = token_set(business_name)
    slug = slug_from_url(social_url)
    slug_tokens = token_set(slug)

    if not slug_tokens:
        return SocialRelevance(1, 'low', 'Could not parse social profile slug')

    overlap = business_tokens & slug_tokens
    score = 0
    reasons = []

    if overlap:
        score += len(overlap) * 2
        reasons.append(f'Token overlap: {", ".join(sorted(overlap))}')

    joined_business = ''.join(sorted(business_tokens))
    joined_slug = ''.join(sorted(slug_tokens))
    if joined_business and joined_slug and (joined_slug in joined_business or joined_business in joined_slug):
        score += 2
        reasons.append('Strong compact name similarity')

    if slug == 'profile':
        score -= 1
        reasons.append('Generic profile URL is less trustworthy')

    if score >= 4:
        confidence = 'high'
    elif score >= 2:
        confidence = 'medium'
    else:
        confidence = 'low'

    return SocialRelevance(score, confidence, '; '.join(reasons) or 'Weak name match')
