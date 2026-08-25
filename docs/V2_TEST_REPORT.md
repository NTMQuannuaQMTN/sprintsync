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

## 2026-08-25 — Phase 12 (observability), Phase 10 (project intelligence), Phase 9 (summarization), Phase 8 (GitHub Action)

| Check | Command | Result |
|---|---|---|
| Full backend lint | `.venv/bin/ruff check src/ tests/` | All checks passed, after every phase below |
| Full backend tests, after Phase 12 | `.venv/bin/pytest -q` | 71 passed |
| Full backend tests, after Phase 10 | `.venv/bin/pytest -q` | 76 passed (+5 `test_project_intelligence.py`) |
| Full backend tests, after Phase 9 | `.venv/bin/pytest -q` | 90 passed (+14: `test_summarization.py`, `test_summary_endpoints.py`) |
| Full backend tests, after Phase 8 | `.venv/bin/pytest -q` | 98 passed (+8 `test_github_action_ingestion.py`) |
| Backend types | `.venv/bin/mypy src` | 28 errors immediately after Phase 12 — one was newly introduced (`core/logging.py`'s renderer variable needed an explicit `Union[ConsoleRenderer, JSONRenderer]` annotation; mypy couldn't unify the if/else branches otherwise). Fixed same-session; re-ran: 27 errors, all pre-existing and unrelated to this session's changes (see `docs/V2_IMPLEMENTATION_PLAN.md` §11 for the itemized breakdown) |
| GitHub Action end-to-end (real, not just reviewed) | Ran `action.yml`'s exact shell script locally (`bash`+`jq`+`curl`, with `GITHUB_EVENT_PATH`/`GITHUB_EVENT_NAME`/`GITHUB_RUN_ID` set the way GitHub's runner sets them) against a real local `uvicorn` instance and a real DB row (repo + `action_token` inserted directly, then cleaned up) | Happy path: HTTP 200, `{"status":"ok","commits_processed":1,...}`. Duplicate delivery: second identical request returned `{"status":"duplicate",...}` instead of reprocessing. Invalid token: HTTP 401, which the script's `[ "${HTTP_STATUS}" -ge 400 ]` branch correctly turns into a `::error::` annotation + `exit 1`. |
| Alembic migration 005 (`repositories.action_token`) | `.venv/bin/alembic upgrade head` | Failed first attempt — `alembic/env.py` had no protection against Supabase's Transaction Pooler breaking named prepared statements (same class of bug `core/database.py` already documents and works around, but never ported to the migration runner). Fixed `env.py` to build its engine the same way (`NullPool` + `statement_cache_size=0` + unnamed prepared statements); migration then applied cleanly. Verified column exists via a direct `information_schema.columns` query against the real DB. |

Confirms: Phases 8/9/10/12 are real, working code exercised by real tests
and (for the GitHub Action) a real manual end-to-end run — not just
"the checklist says done." The one new mypy error this pass introduced
was caught and fixed before moving on, not left for later.

## 2026-08-25 — Phase 7 completion (Notion connect flow + approval mirror)

| Check | Command | Result |
|---|---|---|
| Full backend lint | `.venv/bin/ruff check src/ tests/` | All checks passed |
| Full backend tests | `.venv/bin/pytest -q` | 106 passed (+8: `test_integrations.py` ×5, `test_suggestion_notion_mirror.py` ×3) |
| Backend types | `.venv/bin/mypy src` | 27 errors, all pre-existing, none newly introduced |

Notion's live-verification call (`NotionBoardProvider.verify_connection`)
and `find_task`/`update_status` were mocked at the class level for these
tests (no real `NOTION_TOKEN` in this environment — same blocker as
before); the request-shape itself remains covered separately by
`test_taskboard.py`'s `httpx.MockTransport` tests. Explicitly verified:
approving a suggestion with no Notion connected is unchanged (existing
behavior, no regression); approving with Notion connected calls
`find_task`/`update_status` with the expected task title/proposed status;
a Notion API failure during the mirror does not revert or block the
already-committed internal Task status change.

## 2026-08-25 — Phase 11 (frontend) + Phase 6 completion (status-mapping endpoint)

| Check | Command | Result |
|---|---|---|
| Backend lint | `.venv/bin/ruff check src/ tests/` | All checks passed |
| Backend tests | `.venv/bin/pytest -q` | 109 passed (+4 for the new status-mapping PATCH endpoint, +1 net from removing the old no-op state and adding real coverage) |
| Backend types | `.venv/bin/mypy src` | 27 errors, all pre-existing, none newly introduced |
| Frontend types | `cd apps/web && npx tsc --noEmit` | Clean, after every frontend commit this pass (Suggestions evidence fix, Settings rewrite, repo Connections card, Intelligence page, Commits/PRs tab) |
| Frontend build | `npm run build` | Succeeds after every frontend commit this pass; 15 routes (added `/repositories/[id]/intelligence`) |
| Frontend dev-server smoke test | `npm run dev` + `curl` each new/changed route | `/settings`, `/repositories/[id]`, `/repositories/[id]/intelligence`, `/repositories/[id]/commits` all returned 200 with no server-side errors in the dev log |

Known gap, honestly documented rather than silently skipped: no interactive
browser testing was performed on any of this session's frontend work. This
environment has no browser/screenshot tool available, and the app's
client-side (not middleware) auth guard means a plain `curl` request never
reaches the real authenticated UI — only "does the route compile and
respond" was verifiable here, not "does clicking the button actually work
end-to-end in a browser." The component logic was reviewed against the
same `useQuery`/`useMutation` patterns already proven out elsewhere in this
exact codebase (e.g. the Suggestions page's existing approve/reject flow).

(Entries below are appended in order as V2 work proceeds.)
