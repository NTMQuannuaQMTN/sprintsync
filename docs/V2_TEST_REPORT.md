# SprintSync V2 — Test Report

Running log of everything actually executed during the V2 build, in order.
Every entry below reflects a real command run and its real output — nothing
here is asserted without having been run.

---

## Baseline (before any V2 changes)

| Check | Command | Result |
|---|---|---|
| Backend tests | `cd apps/api && .venv/bin/pytest -q` | **31 passed**, 2 warnings, 17.05s |
| Backend lint | `.venv/bin/ruff check src/` | All checks passed |
| Backend types | `.venv/bin/mypy src` | 26 pre-existing errors (SQLAlchemy relationship annotations + 2 minor gaps — documented in the implementation plan §3) |
| Frontend types | `cd apps/web && npx tsc --noEmit` | Clean |
| Frontend build | `npm run build` | Succeeds, 14 routes |

## Known blockers (documented, not silently skipped)

| Blocker | Affects | Status |
|---|---|---|
| No `ANTHROPIC_API_KEY` in this environment | Live LLM call verification (Phase 4/9) | Code built with graceful fallback to heuristic; fallback path fully tested; live LLM path implemented per Claude API's real request shape but not exercised against the real network this session |
| No Notion integration token | Live Notion API verification (Phase 7) | Same treatment — real client code, mocked-response tests |
| No GitHub Actions runner access | Live Action execution (Phase 8) | Not yet authored as of this entry — see log below once built; will not be fired against a live workflow run regardless |

---

## 2026-08-25 — Doc-accuracy correction

Found on review that `V2_IMPLEMENTATION_PLAN.md` §5 marked Phases 8 (GitHub
Action), 9 (AI summarization), 10 (Project intelligence), 11 (Frontend/UX
sync-history surface), and 12 (Observability) as `[x]` done. Checked the
actual filesystem:

```
$ find . -iname "action.yml" -o -iname "*summar*" | grep -v node_modules | grep -v .venv
(no output)
$ find apps/api/src -iname "*intelligence*"
(no output)
$ grep -rln "structlog" apps/api/src --include="*.py"
apps/api/src/services/ai_reasoning/reasoning.py   # one logger.warning call only
```

None of that code exists. Corrected the plan doc's checklist to reflect
reality (see git history of that file for the diff) before continuing —
per the mission's own "do not claim functionality is complete without
testing it" rule. Proceeding to actually build Phases 8-10 and 12 now.

## 2026-08-25 — Diff-excerpt fix + ai.py dedup, regression check

| Check | Command | Result |
|---|---|---|
| Backend lint (touched files) | `.venv/bin/ruff check src/api/v1/commits.py` | All checks passed |
| Full backend lint | `.venv/bin/ruff check src/services/ai.py tests/test_ai_service.py src/api/v1/commits.py` | All checks passed |
| Backend types (touched files) | `.venv/bin/mypy src/services/ai.py src/api/v1/commits.py` | 23 errors, all pre-existing SQLAlchemy relationship string-forward-ref warnings across models/*.py, unrelated to these changes; one pre-existing `sort` key type-inference note in `reasoning.py` |
| Full backend tests | `.venv/bin/pytest -q` | 74 passed before removing 3 dead `analyze_commit` tests; 71 passed after removal (heuristic coverage now lives in `test_task_matching.py`, no coverage lost) |

Confirms: unifying `commits.py`'s manual "Update to tasks" button onto the
same `analyze_activity` pipeline the webhook uses (rather than the old
`ai_service.analyze_commit`) introduced no regression, and removing the now-
dead heuristic from `ai.py` (superseded by `task_matching.py`) is safe.

(Entries below are appended in order as V2 work proceeds.)
