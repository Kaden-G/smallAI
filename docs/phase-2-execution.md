# Phase 2 — Execution (MVP)

**Duration**: 2–3 weeks  
**Goal**: Deliver hybrid NL → SPL translator + CLI demo.  
**Tools**: Python, regex, scikit-learn, Docker

---

## Deliverables
- Rule-based parser (`src/rule_based_parser.py`)
- ML prototype (`src/ml_parser.py`, TF-IDF + LR)
- Hybrid parser (`src/hybrid_parser.py`)
- Evaluation scripts (`notebooks/eval.ipynb`)
- CLI demo + drift logging (`logs/unparsed.log`)

---

## Why It Matters
Delivers the first measurable NL → SPL translation. Combines precision of rules with generalization of ML. Improves recall on ambiguous phrasing.

---

## Risks & Premortem
| Risk | Why It Matters | Mitigation |
|------|----------------|------------|
| Rule brittleness (real tiger) | Every new phrasing requires updates | Hybrid fallback (ML-first, rules for guardrails) |
| ML overfitting (real tiger) | Poor generalization on real inputs | Use simple ML, cross-validation |
| Inconsistent slot handling (real tiger) | Misaligned slots → broken SPL | schema.yaml contract + eval scripts |
| Latency bloat (paper tiger → real) | Fallback chain grows slow | Measure early; Phase 3 adds normalization |
| Evaluation noise (real tiger) | Phrasing variants distort accuracy | Normalization layer in Phase 3 |

---

## Lessons Learned
*(fill in after completion)*
