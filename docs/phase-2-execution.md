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

Definition of Done
Phase 2 — Definition of Done

Goal: Deliver a working hybrid parser (ML-first, rule fallback) that can produce correct Splunk SPL queries from plain-English inputs — not just on demo data, but across a representative set of log types.

Functional Criteria
Hybrid parser (hybrid_parser.py) generates valid SPL syntax for queries containing the four required slots: action, time, user, and source.
Parser runs end-to-end in a CLI demo (cli.py or hybrid_parser.py -i).
Drift hook logs any unparsed/low-confidence queries to logs/logs/ logs/unparsed.log.

Accuracy Criteria
Rule parser baseline: ≥ 85% exact-match accuracy on the synthetic dataset.
ML parser: ≥ 95% accuracy on time slot, ≥ 90% overall.
Hybrid parser: ≥ 90% exact-match accuracy on synthetic dataset, plus ability to correctly parse at least one real-world query for each major log type (auth, web/nginx, ssh, filesystem, database).
The accuracy report (docs/accuracy_report.md) compares rule-based, ML-based, and hybrid approaches, including confusion matrices and a slot-level breakdown.

Robustness Criteria
The parser does not crash on malformed input; instead, it logs the error to unparsed.log.
At least 20 queries spanning 5 log types were tested and documented (10 synthetic, 10 real-world examples).
Deliverables for Closure
rule_based_parser.py, ml_parser.py, hybrid_parser.py
CLI demo script
Drift hook (logs/unparsed.log + helper)
Accuracy report (synthetic dataset + sample real-world queries)

## Lessons Learned
*(fill in after completion)*
