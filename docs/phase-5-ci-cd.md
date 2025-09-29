# Phase 5 — Automation & CI/CD

**Duration**: 1–2 weeks  
**Goal**: Add automation, enforce quality.  
**Tools**: GitHub Actions, Docker, pytest

---

## Deliverables
- GitHub Actions workflow (lint, test, build)
- Coverage + badges in README
- Docker image build + push (GHCR/DockerHub)

---

## Why It Matters
Professionalizes repo, enforces consistency, automates regression detection.

---

## Risks & Premortem
| Risk | Why It Matters | Mitigation |
|------|----------------|------------|
| CI flakiness (real tiger) | Wastes time, erodes trust | Pin dependencies, keep workflow minimal |
| Unclear gates (real tiger) | Regressions sneak in | PR template + accuracy smoke test |
| Docker bloat (paper → real later) | Slows pipeline | Slim base image, CI checks size |
| Credential leakage (real tiger) | Security risk | Use GitHub Secrets only |

---

## Lessons Learned
*(fill in after completion)*
