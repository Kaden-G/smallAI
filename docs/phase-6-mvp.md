# Phase 6 — Usable MVP

**Duration**: 2–3 weeks  
**Goal**: Deliver usable analyst-facing API.  
**Tools**: FastAPI, Docker, Render/Fly.io

---

## Deliverables
- FastAPI service (`src/serve.py`)
- CLI v2 integrated with API
- Evaluation dataset (50–100 real queries)
- Monitoring (latency, error rate)

---

## Why It Matters
Elevates SmallAI from prototype → NOC-ready tool. Real-world evaluation ensures relevance.

---

## Risks & Premortem
| Risk | Why It Matters | Mitigation |
|------|----------------|------------|
| Latency under load (real tiger) | Analysts won’t adopt | Track p50/p95 latency, optimize |
| Accuracy gap (real tiger) | Weak on real queries | Eval dataset + retraining loop |
| API reliability (real tiger) | Crashes erode trust | Error handling + CI smoke test |
| Security oversights (paper → real later) | Misuse risk | Add API keys in Phase 6.5 |

---

## Lessons Learned
*(fill in after completion)*
