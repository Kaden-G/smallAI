# Phase 1 — Foundation

**Duration**: 1 week  
**Goal**: Define scope, create repo skeleton, prepare baseline dataset & schema.  
**Tools**: GitHub, Python, CSV, YAML

---

## Deliverables
- Repo skeleton (`src/`, `datasets/`, `docs/`, `tests/`, `deploy/`)
- Starter dataset (`datasets/log_query_dataset.csv`)
- Schema baseline (`datasets/schema.yaml`)
- YAML templates for configs (model, CLI, deploy)
- Draft `README.md`

---

## Why It Matters
Creates a structured starting point, ensures consistency across code and data. Reduces technical debt later, makes experimentation repeatable, enforces slot consistency.

---

## Risks & Premortem
| Risk | Why It Matters | Mitigation |
|------|----------------|------------|
| Inconsistent folder/file names (real tiger) | Integration errors, wasted debugging time | CONTRIBUTING.md + CI smoke tests for path/schema consistency |
| Synthetic dataset bias (paper → real later) | Accuracy won’t generalize to real NOC language | Plan to collect 50–100 real queries in Phase 6 |
| Schema drift (real tiger) | Parsers break if schema changes silently | schema.yaml enforced; CI smoke tests block drift |
| Over-documentation slowdown (paper tiger) | Too much upfront slows progress | Phase 1 kept short, focus on baseline artifacts |

---

## Lessons Learned
*(fill in after completion)*
