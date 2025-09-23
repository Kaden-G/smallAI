## SmallAI — Quick instructions for coding agents

This repository converts natural-language log queries into Splunk SPL using a small, self-contained hybrid system (ML + rule fallbacks). Below are the concise, actionable conventions and hotspots an AI agent should know before editing code.

- Architecture (big picture)
  - Two parsing approaches: `ml_parser.py` (TF-IDF + LogisticRegression per slot) and `rule_based_parser.py` (regex + keyword dictionaries). `hybrid_parser.py` trains ML models and falls back to rules when confidence < `CONF_THRESHOLD`.
  - Data flow: input NL -> per-slot prediction (action, time, user, source) -> normalize -> optional CLI clarification -> `to_spl()` builds SPL string.

- Key files
  - `hybrid_parser.py` — main demo: trains models (in-memory), predicts, clarifies (interactive), and generates SPL. Defaults: `DATASET_FILE="datasets/log_query_dataset.csv"`, `CONF_THRESHOLD=0.7`.
  - `rule_based_parser.py` — deterministic fallback; contains `parse_query()` and the canonical slot keywords (see `action_keywords`, `time_keywords`, `source_keywords`, `users`).
  - `ml_parser.py` — standalone ML training/eval helper; note it uses a different dataset path (`log_query_dataset.csv`) so be careful when changing dataset names.
  - `datasets/generate_dataset.py` — synthetic dataset generator; output CSV columns: `nl_query,action,time,user,source,structured_query`.

- Important conventions & patterns (do not break these)
  - Slot names are fixed: `action`, `time`, `user`, `source`. Code assumes these exact keys across files.
  - Unknown/unspecified slot value uses a literal wildcard string `"*"` (not None). Keep this behavior when changing slot logic.
  - Structured-string format used in many places: e.g. `action=failure time=last24h source=auth` (see `structured_string()` in `rule_based_parser.py`).
  - ML fallback logic: models.predict_proba(...) used in `hybrid_parser.py`; if max confidence < `CONF_THRESHOLD`, the code uses the rule-based slot for that field.

- Where to make common changes
  - Add new sourcetypes / mapping: update `source_to_sourcetype` and `known_sourcetypes` in `hybrid_parser.py`, and corresponding `source_keywords` in `rule_based_parser.py`.
  - Extend action templates: update `action_templates` in `hybrid_parser.py` (this text is appended directly into SPL).
  - Time mapping: change `time_map` in `hybrid_parser.py` (controls `earliest` / `latest` tokens in SPL).

- Developer workflows (commands you can run)
  - Install deps: `pip install -r requirements.txt` (repo expects Python 3.9+ per README).
  - Run parser on a query (interactive): `./hybrid_parser.py "show me failed logins from yesterday"`
  - Force (non-interactive) mode: `./hybrid_parser.py -f "query..."` — skips clarification prompts and keeps `*` wildcards.
  - Run rule-only evaluation: `python3 rule_based_parser.py` (no-arg path runs `evaluate()` and prints per-field accuracy).
  - Regenerate dataset: `python3 datasets/generate_dataset.py` (creates `log_query_dataset.csv` in workspace root unless changed).

- Notable gotchas / repo quirks
  - Dataset path inconsistency: `hybrid_parser.py` expects `datasets/log_query_dataset.csv` while `ml_parser.py`/`datasets/generate_dataset.py` write/read `log_query_dataset.csv` at the repo root; fix both or adjust code when changing dataset layout.
  - No model persistence: training happens on each run (in-memory). If you add persistence, update `hybrid_parser.py` to load/save models consistently.
  - `index` default in SPL is hard-coded to `main` in `to_spl()` — change deliberately.

- Examples (copyable snippets)
  - Slot example: `{'action': 'failure', 'time': 'last24h', 'user': '*', 'source': 'auth'}`
  - Generated SPL pattern: `index=main sourcetype=syslog ("Failed password" OR "auth failure") earliest=-24h@h latest=now`

- Guidance for automated edits
  - Preserve slot keys and wildcard semantics when refactoring functions that touch slot dicts.
  - When adding a new time or source label, update both ML training labels (dataset CSV) and rule-based keyword lists to keep parity.
  - Small, safe changes: updating `action_templates` or `source_to_sourcetype` is low-risk; changing training pipeline hyperparameters affects model outputs an# agent\_instructions.md — Quick instructions for coding agents

> Purpose: a concise, machine-friendly set of instructions that coding assistants or automation tools can follow to make safe, correct code changes in the SmallAI repo. This file is intentionally short and prescriptive — it does **not** replace human-facing `docs/plan.md` or `docs/instructions.md`. It exists so bots/agents can quickly find project entrypoints, run and test code, and open PRs with minimal human hand-holding.

---

## Quick facts (single-shot)

* **Repo root:** `smallAI/`
* **Primary language:** Python 3.10+
* **Main CLI:** `src/hybrid_parser.py`
* **API serve file (if present):** `deploy/serve.py` (FastAPI)
* **Dataset:** `dataset/log_query_dataset.csv`
* **Tests:** `pytest` (run `pytest -q`)
* **Lint:** `flake8` or `ruff` (project config may vary)
* **Build:** `docker build -t smallai:latest deploy/` (Dockerfile in `deploy/`)

---

## How to run locally (for dev agents)

1. Create virtualenv + install:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Run unit tests:

   ```bash
   pytest -q
   ```
3. Run CLI (interactive):

   ```bash
   python src/hybrid_parser.py "show me failed logins from yesterday"
   ```
4. Run CLI (force mode - no prompts):

   ```bash
   python src/hybrid_parser.py -f "show me failed logins from yesterday"
   ```
5. Run API (if `deploy/serve.py` exists):

   ```bash
   python deploy/serve.py
   # then POST to /rewrite-query with JSON {"query": "..."}
   ```

---

## Coding & PR rules for automated changes

* **Small PRs only:** target < 200 lines changed. Break larger tasks into multiple PRs.
* **Tests:** any functional change MUST include or update tests. PRs without tests will be rejected.
* **No secrets**: do not add API keys, credentials or real log samples to the repo. Use sanitized, synthetic samples only.
* **PII:** do not commit real logs. Use `scripts/sanitize_logs.py` to anonymize if needed.
* **Commit message format:** `type(scope): short description` (e.g., `fix(parser): handle yesterday -> last24h normalization`).
* **PR description template:** include problem statement, test steps, files changed, and acceptance checklist.

---

## Agent responsibilities (what an agent can safely do)

* Create or edit small utility scripts (`scripts/*.py`) and tests under `tests/`.
* Run unit tests locally and include results in the PR.
* Update `docs/plan.md` or `docs/instructions.md` only when guided by an owner (add an `owner:` tag). Prefer opening an issue for larger plan edits.
* Add or update `src/` parser logic if accompanied by tests demonstrating the behavior change.

## Agent restrictions (what to avoid)

* Do NOT push directly to `main`. Always create a `feature/...` branch and open a PR.
* Do NOT access private systems or credentials. Avoid web requests unless required and explicitly approved.
* Do NOT create large datasets or commit large binary files (>5MB) to the repo.

---

## Owner escalation & approvals

* For any change touching production packaging (`deploy/`), CI or PII handling, create a PR and request review from `@kaden` (repo owner). Add `@kaden` as reviewer in the PR.

---

*Last updated: concise agent guide autogenerated and committed to `docs/agent_instructions.md`. If you want me to also add a CI job that runs these checks automatically, I can generate a `ci.yml` stub next.*
d should keep tests/data in sync.

If anything here is ambiguous or you want the agent to include extra examples (more failing cases, mapping tables, or a sample dataset row), tell me which section to expand and I'll iterate.
