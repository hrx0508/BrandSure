import re
import unicodedata

_STOP = set("the a an and or of to in on for with is are was be by as at it this that from our your their its not".split())


def norm(s: str) -> str:
    """Defined normalisation for quote matching: NFKC, smart quotes, soft hyphens,
    hyphenated line breaks, whitespace collapse, casefold."""
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("\u00ad", "")
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)
    s = s.translate({0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"', 0x2013: "-", 0x2014: "-"})
    return re.sub(r"\s+", " ", s).strip().casefold()


def tokens(s: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]+", norm(s)) if len(t) > 2 and t not in _STOP}


def locate(draft: str, quote: str):
    """Find quote in draft tolerating whitespace/quote-style differences. Returns (start, end) or None."""
    i = draft.find(quote)
    if i >= 0:
        return i, i + len(quote)
    parts, prev_space = [], False
    for ch in quote.strip():
        if ch.isspace():
            if not prev_space:
                parts.append(r"\s+")
            prev_space = True
            continue
        prev_space = False
        if ch in "'\u2018\u2019":
            parts.append("['\u2018\u2019]")
        elif ch in '"\u201c\u201d':
            parts.append('["\u201c\u201d]')
        else:
            parts.append(re.escape(ch))
    m = re.search("".join(parts), draft) if parts else None
    return (m.start(), m.end()) if m else None
