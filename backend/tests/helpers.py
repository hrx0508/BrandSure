from pathlib import Path

GUIDELINE_PARAS = [
    "TechNova Brand Guidelines",
    "The official company name is TechNova. Never write it as \u201cTech Nova\u201d or \u201cTechnova\u201d.",
    "Our tone is professional, friendly and clear; avoid exaggerated claims.",
    "The current promotion is a 20% discount, valid through 15 October 2026.",
    "Ranking claims such as \u201cNo. 1\u201d require approved evidence before publication.",
    "Never use the word \u201ccheap\u201d in public content.",
    "The approved colour palette is #5B35F5, #1FBF8A, #14112B and #FFFFFF.",
    "Every image needs alt text, and text must meet a contrast ratio of at least 4.5:1.",
]
SAMPLE_DRAFT = "Tech Nova is India's No. 1 productivity platform.\nGet 20% off until October 30, 2026!"


def make_docx(paras=GUIDELINE_PARAS) -> bytes:
    import io
    import docx
    d = docx.Document()
    for p in paras:
        d.add_paragraph(p)
    b = io.BytesIO()
    d.save(b)
    return b.getvalue()


def kit_rules():
    """Rules as the extractor would produce them (ids are stable for tests)."""
    from app.services.candidate_extractor import extract_candidates
    units = [{"ref": {"paragraph": i + 1}, "text": t} for i, t in enumerate(GUIDELINE_PARAS)]
    cands, _, _ = extract_candidates(units)
    rules = []
    for c in cands:
        rules.append({"id": "R_" + c["id"], "type": c["type"], "title": c["title"], "content": c["content"],
                      "severity": c["severity"], "valid_from": None, "valid_until": c["valid_until"],
                      "params": c["params"], "source": c["source"]})
    rules.append({"id": "R_fact", "type": "fact", "title": "Approved fact", "severity": "low", "valid_from": None,
                  "valid_until": None, "params": {}, "source": None,
                  "content": "TechNova was ranked No. 1 productivity platform in India by Example Research, 2026."})
    return rules
