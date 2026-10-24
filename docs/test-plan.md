# Test plan

`cd backend && pytest`. Layers: unit (rule engine, normalisation, contrast, tokens, passwords), document (docx/pdf/image validation), schema/evidence (invalid AI output), integration (`tests/test_api.py`: auth, organisation isolation, upload -> confirm -> review -> images -> approve, permissions, revisions, insights) and a labelled evaluation set (`tests/test_evaluation.py`, 9 cases).

## Evaluation (offline checks, evaluation date 20 Oct 2026)
All 9 labelled cases match expectations. The set is small and written alongside the checks, so it says little about real-world accuracy. Expect false positives (for example "guaranteed" used legitimately) and misses (subtle tone problems, paraphrased claims). Extend it with real drafts and record results here, including failures.

## Manual checklist
Keyboard-only walk-through of upload -> confirm -> review -> approve; a creator calling `/decision` directly gets 403; an expired or tampered token is rejected; an oversized or invalid upload shows a clear message; the draft survives a failed API call; light and dark themes; reduced-motion setting.
