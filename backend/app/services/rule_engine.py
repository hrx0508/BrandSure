"""Deterministic checks: same draft + same rules + same date => same findings. No AI here."""
import re
from datetime import date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))  # decision: offers are valid through end of day IST

_M = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
DATE_RE = re.compile(
    rf"(?<!\w)(?:(\d{{1,2}})(?:st|nd|rd|th)?\s+({_M})\.?,?\s+(\d{{4}})"
    rf"|({_M})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})"
    rf"|(\d{{4}})-(\d{{2}})-(\d{{2}}))(?!\w)", re.I)
AMBIGUOUS_DATE_RE = re.compile(r"(?<![\w/])\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}(?![\w/])")
MONTHS = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}

CLAIM_PATTERNS = [
    r"(?:\b[A-Z][\w]*['\u2019]s\s+)?(?<!\w)(?:no\.?\s*1|number\s+one|#\s*1)(?!\w)(?:\s+[A-Za-z\-]+){0,2}",
    r"(?:\b(?:world|india|industry)['\u2019]?s\s+)(?:leading|best|largest|fastest|most\s+\w+)(?:\s+[A-Za-z\-]+){0,2}",
    r"\bmarket\s+leader\b", r"\bbest[- ]in[- ]class\b", r"\bmost\s+trusted\b",
    r"\b(?:100%\s+)?guaranteed\b", r"\baward[- ]winning\b",
]
EXAGGERATION = ["revolutionary", "unbeatable", "best ever", "game-changing", "game changer", "life-changing", "magical", "mind-blowing"]


def today_ist() -> date:
    return datetime.now(IST).date()


def parse_match(m) -> date | None:
    try:
        if m.group(1):
            return date(int(m.group(3)), MONTHS[m.group(2)[:3].lower()], int(m.group(1)))
        if m.group(4):
            return date(int(m.group(6)), MONTHS[m.group(4)[:3].lower()], int(m.group(5)))
        return date(int(m.group(7)), int(m.group(8)), int(m.group(9)))
    except ValueError:
        return None


def find_dates(text: str):
    out = []
    for m in DATE_RE.finditer(text):
        d = parse_match(m)
        if d:
            out.append((d, m.start(), m.end()))
    return out


def parse_date_text(text: str):
    ds = find_dates(text)
    return ds[0][0] if ds else None


def _sentence_bounds(text: str, pos: int):
    start, end = 0, len(text)
    for b in re.finditer(r"[.!?]+(?:\s|$)|\n", text):
        if b.end() <= pos:
            start = b.end()
        elif b.start() >= pos:
            end = b.start()
            break
    while start < end and text[start].isspace():
        start += 1
    return start, end


def _finding(type_, severity, span, text, explanation, rule_ids, fix=None, replacement=None, human=False):
    return {"type": type_, "severity": severity, "verdict": None,
            "span": {"start": span[0], "end": span[1]} if span else None,
            "quoted_text": text[span[0]:span[1]] if span else "(whole draft)",
            "explanation": explanation, "source_ids": rule_ids, "suggested_fix": fix, "replacement": replacement,
            "origin": "rule", "evidence_status": "approved_rule", "requires_human_review": human, "uncertainty": None}


def _phrase_regex(phrase: str):
    return re.compile(r"(?<!\w)" + r"\s+".join(re.escape(w) for w in phrase.split()) + r"(?!\w)", re.I)


def _preferred_regexes(rule):
    pref = rule["params"]["preferred"]
    words = re.findall(r"[A-Z][a-z0-9]*|[a-z0-9]+|[A-Z]+(?![a-z])", pref)
    pats = [_phrase_regex(v) for v in rule["params"].get("variants", []) if v.strip()]
    if len(words) > 1:  # TechNova -> Tech Nova / Technova / TECHNOVA
        pats.append(re.compile(r"(?<!\w)" + r"\s?".join(re.escape(w) for w in words) + r"(?!\w)", re.I))
    else:
        pats.append(re.compile(r"(?<!\w)" + re.escape(pref) + r"(?!\w)", re.I))
    return pats


def check_terms(draft, rules):
    out, seen = [], set()
    for r in rules:
        if r["type"] == "preferred_term":
            pref = r["params"]["preferred"]
            for rx in _preferred_regexes(r):
                for m in rx.finditer(draft):
                    if m.group(0) == pref or (m.start(), m.end()) in seen:
                        continue
                    seen.add((m.start(), m.end()))
                    out.append(_finding("terminology", r["severity"], (m.start(), m.end()), draft,
                                        f"Approved spelling is \u201c{pref}\u201d.", [r["id"]],
                                        f"Use \u201c{pref}\u201d.", pref))
        elif r["type"] == "banned_term":
            for m in _phrase_regex(r["params"]["banned"]).finditer(draft):
                if (m.start(), m.end()) in seen:
                    continue
                seen.add((m.start(), m.end()))
                out.append(_finding("banned_term", r["severity"], (m.start(), m.end()), draft,
                                    f"\u201c{m.group(0)}\u201d is a banned term in this Brand Kit.", [r["id"]],
                                    "Remove or rephrase this term.", None))
    return out


def check_expiry(draft, rules, today: date):
    out = []
    for r in rules:
        if r["type"] != "expiry" or not r.get("valid_until"):
            continue
        until = date.fromisoformat(r["valid_until"])
        kws = r["params"].get("keywords") or re.findall(r"\d+\s?%", r["content"])
        for kw in kws:
            flagged_sentence = set()
            for m in re.finditer(re.escape(kw), draft, re.I):
                s, e = _sentence_bounds(draft, m.start())
                for d, ds, de in find_dates(draft[s:e]):
                    if d > until:
                        out.append(_finding(
                            "date_conflict", "high", (s + ds, s + de), draft,
                            f"Draft gives {d:%d %B %Y}, but the approved offer is valid through {until:%d %B %Y}.",
                            [r["id"]], f"Use a date on or before {until:%d %B %Y}, or get the offer extended in the Brand Kit.",
                            f"{until:%d %B %Y}"))
                if today > until and (s, e) not in flagged_sentence:
                    flagged_sentence.add((s, e))
                    out.append(_finding(
                        "expired_offer", "high", (s, e), draft,
                        f"This offer was valid through {until:%d %B %Y}; checked on {today:%d %B %Y}.",
                        [r["id"]], "Remove the offer or replace it with a current one.", None, human=True))
    return out


def check_disclaimers(draft, rules):
    out = []
    for r in rules:
        if r["type"] == "required_disclaimer":
            phrase = r["params"]["phrase"]
            if re.sub(r"\s+", " ", phrase).strip() not in re.sub(r"\s+", " ", draft):
                out.append(_finding("missing_disclaimer", r["severity"], None, draft,
                                    f"Required wording is missing: \u201c{phrase}\u201d.", [r["id"]],
                                    f"Add: {phrase}", None))
    return out


def detect_claims(draft):
    """Deterministic claim spotting. Whether a claim is *supported* is judged later."""
    spans = []
    for p in CLAIM_PATTERNS:
        for m in re.finditer(p, draft, re.I):
            spans.append((m.start(), m.end()))
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(e, merged[-1][1]))
        else:
            merged.append((s, e))
    return [{"quoted_text": draft[s:e].strip(), "span": {"start": s, "end": e}} for s, e in merged]


HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def contrast_ratio(a: str, b: str) -> float:
    """WCAG 2.x contrast ratio between two #RRGGBB colours."""
    def lum(h):
        c = [v / 255 for v in _rgb(h)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(_rgb(a), _rgb(b))) ** 0.5


def _is_neutral(h):
    r, g, b = _rgb(h)
    return max(r, g, b) - min(r, g, b) < 30  # white/black/grey are not judged against the palette


def check_images(images, rules):
    """Alt text, contrast and palette checks for attached images (only when the kit has matching rules)."""
    acc = next((r for r in rules if r["type"] == "accessibility"), None)
    palette = [c.upper() for r in rules if r["type"] == "palette" for c in r["params"].get("colors", [])]
    pal_rule = next((r for r in rules if r["type"] == "palette"), None)
    out = []

    def add(im, type_, sev, text, why, rule, fix, human=False, unc=None):
        f = _finding(type_, sev, None, "", why, [rule["id"]], fix, None, human)
        f.update(quoted_text=im["filename"], meta={"image_id": im["id"]}, uncertainty=unc)
        out.append(f)

    for im in images:
        if acc and acc["params"].get("require_alt", True) and not (im.get("alt_text") or "").strip():
            add(im, "missing_alt", "high", "", "This image has no alt text, so screen-reader users cannot tell what it shows.",
                acc, "Describe what the image shows in one short sentence.")
        if acc and im.get("text_color") and im.get("bg_color") and HEX_RE.match(im["text_color"]) and HEX_RE.match(im["bg_color"]):
            need = float(acc["params"].get("min_contrast", 4.5))
            cr = contrast_ratio(im["text_color"], im["bg_color"])
            if cr < need:
                best = max(("#111111", "#FFFFFF"), key=lambda c: contrast_ratio(c, im["bg_color"]))
                add(im, "low_contrast", "high" if cr < 3 else "medium", "",
                    f"Text {im['text_color'].upper()} on {im['bg_color'].upper()} has a contrast ratio of {cr:.1f}:1; the guideline needs at least {need:g}:1.",
                    acc, f"Use {best} text here ({contrast_ratio(best, im['bg_color']):.1f}:1).")
        if palette:
            for d in im.get("dominant", []):
                if d["share"] < 0.2 or _is_neutral(d["hex"]):
                    continue
                near = min(palette, key=lambda p: _dist(d["hex"], p))
                if _dist(d["hex"], near) > 70:
                    add(im, "visual_palette", "low", "",
                        f"A main colour in this image ({d['hex']}, about {round(d['share'] * 100)}% of it) is not in the approved palette; the nearest approved colour is {near}.",
                        pal_rule, "Check this image with the brand team or use an approved colour.", human=True,
                        unc="Dominant-colour matching is approximate. A palette match does not prove the whole image is compliant.")
                    break
    return out


def run_checks(draft, rules, today: date):
    findings = check_terms(draft, rules) + check_expiry(draft, rules, today) + check_disclaimers(draft, rules)
    return sorted(findings, key=lambda f: (f["span"]["start"] if f["span"] else -1))
