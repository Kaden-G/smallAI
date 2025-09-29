# Phase 7 — Recommendation Microservice (SOAR-lite)

**Duration**: 2–4 weeks  
**Goal**: Extend from queries → actionable guidance.  
**Tools**: FastAPI microservice, YAML KB

---

## Deliverables
- /recommend endpoint
- YAML knowledge base (seeded from NIST, SANS, ATT&CK)
- Feedback logging

---

## Why It Matters
Analysts get next-step recommendations (lightweight SOAR-lite). Raises value beyond syntax generation.

---

## Risks & Premortem
| Risk | Why It Matters | Mitigation |
|------|----------------|------------|
| Over-scoping into SOAR (real tiger) | Scope bloat | YAML-only KB, suggestions not automation |
| Low trust (real tiger) | Suggestions ignored | Seed KB from credible playbooks |
| Maintenance burden (paper → real later) | KB grows stale | Modular KB files + automation |
| Latency creep (paper tiger) | Hurts UX | YAML lookup = O(1), microservice stateless |

---

## Lessons Learned
*(fill in after completion)*
