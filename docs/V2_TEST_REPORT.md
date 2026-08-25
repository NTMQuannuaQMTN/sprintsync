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
| No GitHub Actions runner access | Live Action execution (Phase 8) | `action.yml` authored and reviewed; not fired against a live workflow run |

---

(Entries below are appended in order as V2 work proceeds.)
