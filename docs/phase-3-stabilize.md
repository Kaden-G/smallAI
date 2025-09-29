# Phase 3 — Stabilize & Package

**Duration**: 2–3 weeks  
**Goal**: Improve robustness, add normalization, Dockerize.  
**Tools**: Pandas, pytest, Docker

---

## Deliverables
- Normalization layer (`src/normalize.py`)
- Expanded vocab & schema
- Regression tests (auth, ssh, db, filesystem logs)
- Dockerfile + CI build

---

## Why It Matters
Strengthens robustness against noisy log inputs. Regression tests prevent accuracy drift. Docker ensures consistent runtime across environments.

---

## Risks & Premortem
| Risk | Why It Matters | Mitigation |
|------|----------------|------------|
| Data normalization complexity (real tiger) | Inconsistent fields reduce accuracy | Preprocess layer aligns schema |
| Regression from vocab expansion (real tiger) | Adding logs can silently break accuracy | Regression test suite |
| Docker misconfig (paper tiger) | Demo fails for others | Standardized Dockerfile + CI |
| Coverage gaps (real tiger) | Slot errors sneak back | Expand tests; CI requires passing |
| Overhead from cleaning (paper tiger) | Latency impact | Preprocess before parse; measure latency |

---

## Lessons Learned
*(fill in after completion)*
