from typing import Literal

RuleType = Literal["preferred_term", "banned_term", "expiry", "required_disclaimer", "claim_rule", "tone_guideline", "fact", "palette", "accessibility"]
Severity = Literal["low", "medium", "high"]
FindingType = Literal["terminology", "banned_term", "expired_offer", "date_conflict", "missing_disclaimer",
                      "unsupported_claim", "tone_mismatch", "visual_palette", "missing_alt", "low_contrast", "reviewer_suggestion", "other"]
Verdict = Literal["supported", "contradicted", "unverified"]
FindingStatus = Literal["open", "flagged", "accepted", "edited", "dismissed", "resolved"]
