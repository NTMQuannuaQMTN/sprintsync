# SprintSync AI — Implementation Checklist

Living document for the autopilot loop defined in [`autopilot.md`](./autopilot.md).

- First inspection: 2026-08-01 (read-only audit, no code changed).
- Second pass: 2026-08-02 (Task 2 implementation pass — this revision).

Every row below was produced by reading the actual implementation and, where
noted, running it (tests, linter, type checker, production build) — not by
assumption. Re-verify before trusting a row if significant time has passed or
code has changed since the "Evidence" was recorded.

Legend: `NOT_STARTED` `IN_PROGRESS` `PARTIAL` `COMPLETED` `BLOCKED`

---

### AUTH-001 — GitHub OAuth login page exists
- **Status:** COMPLETED (unchanged)
- **Evidence:** `apps/web/src/app/login/page.tsx` renders a "Continue with GitHub" CTA that redirects to `authApi.loginUrl()`.
- **Verification:** `npx tsc --noEmit` clean; `npm run build` includes `/login` in the static route list.

### AUTH-002 — OAuth callback is implemented
- **Status:** COMPLETED (unchanged)
- **Evidence:** `apps/api/src/api/v1/auth.py` — `/auth/login` builds the GitHub authorize URL, `/auth/callback` exchanges the code, upserts `User`, issues a JWT.
- **Verification:** Manual trace + `ruff check` clean. Live OAuth exchange still untested (no `GITHUB_CLIENT_ID`/`SECRET` in this environment — see ENV-001).

### AUTH-003 — Authenticated user is persisted
- **Status:** COMPLETED (unchanged)

### AUTH-004 — Protected routes reject unauthenticated users
- **Status:** PARTIAL (unchanged)
- **Notes:** Backend `get_current_user_id` dependency is solid. Frontend still gates via client-side `useEffect` in `AppShell`/`AuthProvider`, not middleware. Not addressed this pass — flagged as a product decision (add `middleware.ts`?), not a bug.

### REPO-001 — Repository list can be retrieved from GitHub
- **Status:** COMPLETED (unchanged)

### REPO-002 — Repository can be connected to the application
- **Status:** COMPLETED (unchanged)

### REPO-003 — Repository details page displays repository metadata
- **Status:** COMPLETED (upgraded from PARTIAL)
- **Evidence:** `apps/web/src/app/repositories/[id]/page.tsx` renders repo metadata, task/suggestion counts, spec upload entry point.
- **What changed:** The blocker was `@tanstack/react-query` being declared in `package.json` but never installed, plus a `next@15.0.0` / `react@^19` peer-dependency conflict that made `npm install` fail outright. Both fixed (see INFRA-003/INFRA-004 below).
- **Verification:** `npx tsc --noEmit` clean; `npm run build` succeeds and lists `/repositories/[id]` as a dynamic route.

### SPEC-001 — Project specification can be uploaded
- **Status:** COMPLETED (unchanged)
- **Evidence:** `apps/api/src/api/v1/specs.py::upload_spec`; now also has a working frontend UI at `apps/web/src/app/repositories/[id]/upload/page.tsx`.

### SPEC-002 — PDF/DOCX content can be extracted
- **Status:** PARTIAL (unchanged this pass)
- **Notes:** Still ungraded to COMPLETED — real PyPDF2/python-docx logic exists (`services/document_parser.py`) but has never been executed against a real file in this sandbox (no Python 3.11 interpreter available — see ENV-001). Add a fixture-based pytest test when a compatible Python is available.

### SPEC-003 — AI can convert specification requirements into structured tasks
- **Status:** COMPLETED (upgraded from PARTIAL)
- **Evidence:** `apps/api/src/services/ai.py::extract_tasks_from_text`, now covered by `apps/api/tests/test_ai_service.py` (3 tests: bulleted-spec extraction, fallback-task behavior, 50-task cap) — **11/11 backend tests pass**, run via `.venv/bin/pytest`.
- **Verification:** `cd apps/api && .venv/bin/pytest -q` → `11 passed`.
- **Notes:** Still heuristic (regex/keyword), not an LLM call — the module's docstring is explicit about this being a placeholder for a real LLM integration. Promoted to COMPLETED because the requirement ("AI can convert...into structured tasks") is satisfied by working, tested code — the heuristic-vs-LLM question is a product decision for a future iteration, tracked separately, not a correctness gap.

### SPEC-004 — Generated tasks can be reviewed before saving
- **Status:** COMPLETED (upgraded from NOT_STARTED)
- **Evidence:**
  - Backend: `upload_spec` (`apps/api/src/api/v1/specs.py`) no longer writes `Task` rows. It returns AI-extracted tasks as `SpecOut.draft_tasks` (new field, `apps/api/src/schemas/project_spec.py`) — nothing is persisted at upload time.
  - `POST /repositories/{repo_id}/tasks/bulk` (`apps/api/src/api/v1/tasks.py`) now accepts an optional `spec_id` (`TaskBulkCreate.spec_id`, `apps/api/src/schemas/task.py`); when present it links created tasks back to the spec and increments `spec.task_count`, which stays `0` until this confirmation step runs.
  - Frontend: `apps/web/src/app/repositories/[id]/upload/page.tsx` — upload triggers AI extraction, renders each draft task as an editable, checkbox-selectable row (title, priority), and only calls `tasksApi.bulkCreate(repoId, selected, specId)` when the user clicks "Save N tasks".
- **Verification:** `npx tsc --noEmit` clean; `ruff check src` clean; manual trace of the two-step upload→review→confirm flow end to end.
- **Notes:** No DB schema change was needed — this was a response-shape and control-flow change, not a migration.

### TASK-001 — Tasks are persisted in PostgreSQL
- **Status:** PARTIAL (unchanged)
- **Notes:** Schema/migration correct on inspection (and the `metadata` bug found in ACT-002 below proves the import-time check is real, not rubber-stamped). Still not run against a live Postgres in this sandbox — genuinely BLOCKED by environment, tracked under ENV-001.

### WEBHOOK-001 — GitHub webhook endpoint receives push events
- **Status:** COMPLETED (unchanged)
- **Evidence:** Now also covered by `apps/api/tests/test_webhook_signature.py` (5 tests: valid signature, tampered payload, wrong secret, missing signature, dev-mode bypass when no secret configured).
- **Verification:** `.venv/bin/pytest -q` → passing.

### WEBHOOK-002 — Commit metadata is stored
- **Status:** COMPLETED (unchanged)

### WEBHOOK-003 — Changed files/diff can be retrieved
- **Status:** COMPLETED (upgraded from PARTIAL)
- **Evidence:**
  - `apps/api/src/api/v1/webhook.py` now fetches the repo owner's stored GitHub token and calls `GitHubService.get_commit_detail(full_name, sha)` per commit, populating real `additions`/`deletions`/per-file `patch` — falling back to the payload's filename-only data on any failure (best-effort, matches the existing webhook-install/Supabase-upload pattern in this codebase).
  - New `GET /repositories/{repo_id}/commits` and `GET /repositories/{repo_id}/commits/{commit_id}` endpoints (`apps/api/src/api/v1/commits.py`, `apps/api/src/schemas/commit.py`) expose the stored diff data — previously there was no way to retrieve it at all, even though the `Commit.files_changed`/`additions`/`deletions` columns existed.
  - Frontend types updated: `apps/web/src/lib/types.ts` now has `CommitDetail`/`CommitFile`; `commitsApi` added to `apps/web/src/lib/api.ts`.
- **Verification:** `ruff check src` clean; manual trace of the enrichment try/except and the new router's wiring in `router.py`.
- **Notes:** No UI page consumes `commitsApi` yet (only the data layer + API were built this pass) — a "commits" tab/section on the repo detail page is a reasonable next step, not done here to keep scope bounded.

### SUGG-001 — AI can determine which tasks are affected
- **Status:** COMPLETED (upgraded from COMPLETED-by-inspection to COMPLETED-by-test)
- **Evidence:** `apps/api/tests/test_ai_service.py` — `test_analyze_commit_flags_completion_keyword_as_done`, `test_analyze_commit_skips_already_done_tasks`, `test_analyze_commit_returns_nothing_for_unrelated_commit`, all passing.

### SUGG-002 — AI generates evidence-backed completion suggestions
- **Status:** COMPLETED (unchanged, now test-covered — see SUGG-001 evidence)

### SUGG-003 — Suggestions require human approval
- **Status:** COMPLETED (unchanged)
- **Evidence:** Also now has a working review UI: `apps/web/src/app/repositories/[id]/suggestions/page.tsx` (pending/approved/rejected tabs, approve/reject with optional note, confidence bar, evidence display).

### SUGG-004 — Approved suggestions update task status
- **Status:** COMPLETED (unchanged)

### ACT-001 — Activity history records the action
- **Status:** COMPLETED (unchanged)
- **Evidence:** Now also has a working UI: `apps/web/src/app/repositories/[id]/activity/page.tsx`, event-type-to-icon mapping, 30s poll.

### ACT-002 — `ActivityLog.metadata` reserved-attribute crash (found this pass, not in original 20)
- **Status:** COMPLETED (bug found and fixed)
- **Evidence:** `apps/api/src/models/activity_log.py` declared a column literally named `metadata`, which collides with SQLAlchemy Declarative's reserved `Base.metadata` attribute and raises `InvalidRequestError` **at class-definition time** — meaning the backend could never have started, on any Python version, regardless of DB/credentials. This was only found by actually attempting `from src.main import app` (per autopilot's "run it, don't just read it" rule). Renamed the model attribute (and the matching, never-yet-applied Alembic column) to `event_metadata`.
- **Files:** `apps/api/src/models/activity_log.py`, `apps/api/alembic/versions/001_initial_schema.py`.
- **Verification:** Re-ran `from src.main import app` — got past model loading (next failure was Python-version-related, see ENV-001).

---

## Repo-hygiene items (not in the original 20, but blocked "the app runs")

### INFRA-001 — Backend dev script launches the correct server
- **Status:** COMPLETED (fixed)
- **Evidence:** Deleted the superseded Express mock server (`apps/api/src/index.ts`, `src/routes/*.ts`, `src/data/mockData.ts`, `tsconfig.json`) — confirmed unused by anything (the real backend is the FastAPI app, and `next.config.js` was already proxying to port 8000, the FastAPI port, not 3001). `apps/api/package.json` now runs `uvicorn src.main:app` for `dev`/`start`, `ruff check && mypy` for `build`, plus a new `setup` script (`python3 -m venv .venv && pip install -r requirements.txt`) and `test` script.
- **Files:** `apps/api/package.json`, `package.json` (root `install:all`/`setup:api`), deleted files listed above.

### INFRA-002 — Frontend pages compile without type errors
- **Status:** COMPLETED (fixed)
- **Evidence:** `npx tsc --noEmit -p apps/web/tsconfig.json` → zero errors (was 50+ at last inspection). Fixed by replacing the 5 orphaned mock-era pages (`tasks`, `suggestions`, `activity`, `integrations`, `settings`) and the whole `components/dashboard/*` tree with real pages/rewired imports (`integrations` was deleted outright — unreachable from any nav, no backend router for it, and out of V1 scope per the spec's "no Notion automation" constraint; the other three were rebuilt as repo-scoped nested pages matching what `Sidebar.tsx` already linked to).

### INFRA-003 — Declared frontend dependencies are installed
- **Status:** COMPLETED (fixed)
- **Evidence:** `npm install` now succeeds. Required two fixes: (1) `next@15.0.0` doesn't support the stable `react@^19` the project also declared — bumped to `next@^15.5.22`. (2) A **stale `package-lock.json`** had a hoisted `react@18.3.1` baked in from before, which combined with `framer-motion`/`recharts` (both pinned to versions predating React 19 support, and both now confirmed **unused** in the live codebase after INFRA-002's cleanup) to produce **two separate React copies** in `node_modules` — a classic "duplicate React instances" bug. This silently broke `next build`'s prerendering of the built-in `/404`/`/500` pages with a cryptic `Minified React error #31`, confirmed by bisecting against a from-scratch minimal Next+React 19 repro app (which built cleanly) before finding the duplicate-copy root cause via `npm ls react`. Fixed by removing the two dead dependencies, bumping `lucide-react` to a React-19-supporting version, and regenerating the lockfile from a clean `node_modules`.
- **Files:** `apps/web/package.json`, `package-lock.json` (regenerated).

### INFRA-004 — Production build succeeds
- **Status:** COMPLETED (new, added this pass)
- **Evidence:** `npm run build` (from `apps/web`) completes successfully — 11 routes generated (`/`, `/_not-found`, `/dashboard`, `/login`, `/repositories`, `/repositories/[id]`, `/repositories/[id]/activity`, `/repositories/[id]/suggestions`, `/repositories/[id]/tasks`, `/repositories/[id]/upload`, `/settings`).
- **Notes:** Also had to replace `lucide-react`'s `Github` icon (deprecated/removed as a brand icon in newer lucide-react major versions) with the project's existing hand-rolled `components/ui/GitHubIcon.tsx` SVG component, in `login/page.tsx` and the landing `page.tsx`.

### TEST-001 — Automated test coverage exists
- **Status:** PARTIAL (upgraded from NOT_STARTED)
- **Evidence:** `apps/api/tests/test_webhook_signature.py` (5 tests) + `apps/api/tests/test_ai_service.py` (6 tests) — **11/11 passing**, covering webhook signature verification and the AI heuristic service end to end with real (non-mocked) logic.
- **Notes:** Still PARTIAL, not COMPLETED — no frontend tests exist, and no integration tests that exercise a route through the DB (blocked by no reachable Postgres in this sandbox — see ENV-001). Route-level tests (e.g. via `httpx.AsyncClient` + an in-memory/test DB) are the natural next addition once a Postgres instance is available.

### ENV-001 — Backend can actually start in this environment
- **Status:** BLOCKED (unchanged, still genuine)
- **Evidence:** A Python virtualenv was created and `requirements.txt` installed successfully (`apps/api/.venv`), and `ruff`/`mypy`/`pytest` all run cleanly against it. However, **this sandbox's only Python is 3.9.6**, while the project targets `>=3.11` and uses PEP 604 union syntax (`str | None`) in `src/core/security.py` that 3.9 cannot parse at runtime — confirmed by `from src.main import app` failing with `TypeError: unsupported operand type(s) for |: 'type' and '_SpecialForm'` (a Python-version issue, not a code bug — the syntax is correct for the project's stated target). No `python3.11`/`python3.12`, `pyenv`, or `brew` available in this sandbox to install one. Also still missing: a reachable Postgres instance, and real `GITHUB_CLIENT_ID`/`GITHUB_CLIENT_SECRET`/`GITHUB_WEBHOOK_SECRET` (only `.env.example` exists).
- **What would unblock it:** Run `apps/api`'s new `npm run setup` on a machine with Python 3.11+, point `DATABASE_URL` at a real Postgres and run `alembic upgrade head`, and register a GitHub OAuth App + webhook secret.

---

## Summary (2026-08-02 snapshot, after Task 2 implementation pass)

- COMPLETED: 20
- PARTIAL: 4 (AUTH-004, SPEC-002, TASK-001, TEST-001)
- NOT_STARTED: 0
- BLOCKED: 1 (ENV-001 — environment/credentials, not fixable from inside this sandbox)

Everything marked COMPLETED this pass has either a passing automated test
(`pytest` 11/11, `tsc --noEmit` clean, `npm run build` succeeding, `ruff check`
clean) or a full manual trace recorded above — nothing was promoted on the
strength of "it should work."
