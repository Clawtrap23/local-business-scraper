#!/usr/bin/env python3
import re
from typing import Iterable, List


def digits_only(value: str) -> str:
    return re.sub(r'\D', '', value or '')


def normalize_au_phone(value: str) -> str:
    digits = digits_only(value)
    if not digits:
        return ''

    if digits.startswith('61') and len(digits) == 11:
        digits = '0' + digits[2:]

    if len(digits) == 10 and digits.startswith('0'):
        if digits.startswith('04'):
            return f'{digits[:4]} {digits[4:7]} {digits[7:]}'
        return f'{digits[:2]} {digits[2:6]} {digits[6:]}'

    if len(digits) == 8:
        return f'{digits[:4]} {digits[4:]}'

    if len(digits) == 10 and digits.startswith('13'):
        return f'{digits[:4]} {digits[4:7]} {digits[7:]}'

    return value.strip()


def dedupe_phone_variants(values: Iterable[str]) -> List[str]:
    by_digits = {}
    for value in values:
        clean = normalize_au_phone(value)
        digits = digits_only(clean)
        if len(digits) < 8 or len(digits) > 11:
            continue
        if digits not in by_digits or (' ' in clean and ' ' not in by_digits[digits]):
            by_digits[digits] = clean
    return list(by_digits.values())


def choose_best_phone(values: Iterable[str], fallback: str = '') -> str:
    phones = dedupe_phone_variants(values)
    if not phones and fallback:
        phones = dedupe_phone_variants([fallback])
    if not phones:
        return ''

    def score(phone: str) -> int:
        digits = digits_only(phone)
        s = 0
        if phone.startswith('04'):
            s += 1
        if phone.startswith('13'):
            s += 2
        if len(digits) == 10 and phone.startswith('0'):
            s += 3
        if ' ' in phone:
            s += 1
        return s

    phones.sort(key=score, reverse=True)
    return phones[0]
