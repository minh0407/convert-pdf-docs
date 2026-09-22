import re
from typing import List, Dict

SPECIAL_SYMBOLS = set('±≤≥≠ØΩµ°²³×÷Σ√')


def region_risks(text: str, confidence: float) -> List[str]:
    flags: List[str] = []
    if confidence < 0.60:
        flags.append('LOW_CONFIDENCE')
    elif confidence < 0.80:
        flags.append('MEDIUM_CONFIDENCE')

    if any(ch in text for ch in SPECIAL_SYMBOLS):
        flags.append('SPECIAL_SYMBOL')

    compact = text.replace('.', '').replace(',', '').replace(' ', '')
    if re.search(r'\d+[A-Za-z]+\d*|[A-Za-z]+\d+', compact) and any(c.isdigit() for c in compact):
        # useful for catching O/0, I/1 ambiguity; can be tuned per document type.
        if not re.match(r'^[A-Za-z]+\d+[A-Za-z0-9.-]*$', compact):
            flags.append('ALPHANUMERIC_AMBIGUITY')

    return sorted(set(flags))


def classify_page(regions: List[Dict], quality: Dict) -> Dict:
    if not regions:
        return {'difficulty': 'hard', 'average_confidence': 0.0, 'risk_flags': ['NO_TEXT_DETECTED']}

    avg = sum(r['confidence'] for r in regions) / len(regions)
    flags = set()
    for r in regions:
        rr = region_risks(r['text'], r['confidence'])
        r['risk_flags'] = rr
        flags.update(rr)

    if quality.get('blur_score', 999) < 50:
        flags.add('BLURRY_SCAN')
    if quality.get('dark_ratio', 0) > 0.20:
        flags.add('DARK_BACKGROUND')

    if avg >= 0.90 and not {'BLURRY_SCAN', 'LOW_CONFIDENCE'} & flags:
        difficulty = 'easy'
    elif avg >= 0.75 and 'LOW_CONFIDENCE' not in flags:
        difficulty = 'medium'
    else:
        difficulty = 'hard'

    return {
        'difficulty': difficulty,
        'average_confidence': round(avg, 4),
        'risk_flags': sorted(flags)
    }
