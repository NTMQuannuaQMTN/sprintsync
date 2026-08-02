# SprintSync AI — Autopilot Operating Instructions

This file is the operating manual for an autonomous CodeBuddy development
session on this repository. It defines the loop, the checklist contract, the
verification bar, and the safety rules. It does not contain the checklist
itself — that lives in [`CHECKLIST.md`](./CHECKLIST.md) and is a living
document updated every iteration.

**The one rule that overrides all others:**

> Inspect → Implement → Verify → Re-inspect → Repeat.
> Never assume code is correct because it was generated. Never mark a
> requirement complete without evidence.

---

## 1. The Loop

```text
Read Project Specification (this file + product intent below)
        ↓
Generate / Update CHECKLIST.md
        ↓
Inspect Existing Code (never assume — grep, read, run)
        ↓
Any NOT_STARTED / PARTIAL items?
    ├── YES → Implement the highest-priority one → Verify it → back to top
    └── NO  → Run full verification suite → Re-check every checklist item
                    ↓
              All achievable items COMPLETED or genuinely BLOCKED?
                    ├── NO  → repeat
                    └── YES → STOP, produce final report
```

One iteration = one checklist item (or one tightly related cluster). Do not
batch unrelated items into a single implement/verify pass — it breaks the
evidence chain.

---

## 2. The Checklist Contract

`CHECKLIST.md` is the source of truth for autopilot progress on *this repo*
(distinct from the in-product task board SprintSync itself generates for its
users — see §6). Every row uses this schema:

```text
ID:                  short stable slug, e.g. AUTH-002
Requirement:         one specific, testable sentence
Status:              NOT_STARTED | IN_PROGRESS | PARTIAL | COMPLETED | BLOCKED
Evidence:            file(s)/line(s) + what was run to confirm it
Files involved:      repo-relative paths
Verification method: exact command or manual-inspection procedure
Notes:               caveats, decisions needed, follow-ups
```

Rules for status transitions:

- `COMPLETED` requires evidence from *running* something (test, typecheck,
  build, manual endpoint call) OR, when execution is impossible in this
  environment, a full manual read of the implementation that traces the
  requirement end-to-end. Reading a function signature and assuming its body
  is correct is not evidence.
- `PARTIAL` means real, non-trivial code exists but does not fully satisfy
  the requirement (missing a step, untested, wrong wiring, stubbed
  sub-piece). Say exactly what's missing.
- `BLOCKED` means a genuine external blocker: missing credentials
  (`GITHUB_CLIENT_ID`/`SECRET`, `GITHUB_WEBHOOK_SECRET`), no reachable
  Postgres instance, no LLM API key, an unclear spec decision, or a
  toolchain limitation in this sandbox. State the exact blocker and what
  would unblock it.
- Never invent a `COMPLETED` to make the list look better. A shorter honest
  list is the deliverable, not a longer dishonest one.

---

## 3. Task 1 — Generate/Update the Checklist (inspect first)

For every requirement in §6 (SprintSync V1 scope):

```text
Requirement → grep the repo for related symbols/routes/components
            → read the matching files fully (not just the top)
            → trace the data path: route → service → model → schema → frontend caller
            → run it if the environment allows (pytest/tsc/curl/uvicorn)
            → assign status + evidence
```

Do not assume a feature is missing because you don't remember seeing it —
search first. Do not assume a feature is done because a file with a
plausible name exists — this repo has **already burned that assumption
once** (see §7, legacy prototype pages that import functions that don't
exist). Read the actual implementation.

---

## 4. Task 2 — Implement Remaining Work

Dependency order for this specific stack:

```text
DB schema (SQLAlchemy models + Alembic migration)
      ↓
Backend API (FastAPI route + schema + service)
      ↓
Frontend integration (apps/web/src/lib/api.ts client + page/component)
      ↓
AI workflow (src/services/ai.py extraction/analysis logic)
      ↓
Testing (pytest for API, tsc/build for web)
```

Don't build a frontend page against an endpoint that doesn't exist yet.
Don't wire an AI step to a schema field that isn't migrated. If a
lower layer is only PARTIAL, fix that before building on top of it.

Per item:

1. Restate the requirement in one sentence.
2. Identify the existing architecture to extend (this codebase already has
   consistent per-resource route modules under `apps/api/src/api/v1/`,
   Pydantic schemas under `src/schemas/`, SQLAlchemy models under
   `src/models/`, and a typed fetch client in `apps/web/src/lib/api.ts` —
   follow those patterns, don't invent a new one).
3. Implement the smallest correct change.
4. Set status to `IN_PROGRESS` in `CHECKLIST.md` while working.
5. Verify immediately (§5) before moving to the next item.
6. Update `CHECKLIST.md` with the real outcome.

### Task 2.1 — Do not fake completion

Forbidden, no exceptions:

- Empty function bodies or `pass`/`return None` stubs marked COMPLETED.
- `# TODO` left in place while the checklist says done.
- Mocked GitHub/AI responses presented as real integration.
- Hardcoded suggestion/task data instead of DB-backed data.
- Removing or skipping a failing test to make CI green.
- Bypassing `get_current_user_id` / repo-ownership checks to make an
  endpoint "work."
- Marking anything COMPLETED because "it should work" without running it.

If you hit a real blocker (missing `GITHUB_CLIENT_ID`, no Postgres reachable
in this sandbox, no LLM API key provisioned, ambiguous product decision),
set `BLOCKED` and say exactly what unblocks it. That is a correct, honest
outcome — not a failure of the loop.

---

## 5. Task 3 — Verification Methods (exact commands for this repo)

Backend (`apps/api`, Python/FastAPI):

```bash
# Install first if not already (no venv exists in this repo yet)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

ruff check src                       # lint
mypy src                             # type check (pyproject.toml config)
alembic upgrade head                 # apply migrations against DATABASE_URL
pytest                               # once tests exist under apps/api/tests/
uvicorn src.main:app --reload --port 8000   # startup smoke test
curl localhost:8000/health           # should return {"status":"ok",...}
```

Frontend (`apps/web`, Next.js/TypeScript):

```bash
npm install                          # from repo root; workspaces: apps/*
cd apps/web
npx tsc --noEmit -p tsconfig.json    # type check — currently fails, see CHECKLIST.md
npm run build                        # production build
```

Integration verification specifics for this product:

- GitHub OAuth: this app no longer performs the OAuth handshake itself —
  Supabase Auth does (frontend calls `supabase.auth.signInWithOAuth`, GitHub
  client id/secret live in the Supabase dashboard). Confirm
  `core/security.py::decode_supabase_token` correctly verifies a
  Supabase-issued JWT against `SUPABASE_JWT_SECRET`, and that
  `POST /auth/sync` stores the GitHub provider token onto `profiles`.
- Webhook: confirm `verify_webhook_signature` rejects bad HMAC signatures
  (`src/services/github.py`) and that `POST /api/v1/webhook/github` is
  idempotent on `Commit.sha` (dedup check in `webhook.py`).
- AI suggestions: confirm every `Suggestion` row has a non-null `evidence`
  JSONB payload and that `status` starts at `PENDING` — never
  auto-approved.
- Approval flow: confirm task status only changes inside
  `approve_suggestion` (`suggestions.py`), never as a side effect of
  webhook processing.
- DB persistence: confirm the Alembic migration
  (`apps/api/alembic/versions/001_initial_schema.py`) matches the current
  models before trusting any "tasks are persisted" claim.

Manual code verification is mandatory in addition to the above — reread the
full implementation of anything you're about to mark COMPLETED. Passing
`tsc` does not mean the feature is correct; it means the types line up.

---

## 6. SprintSync V1 Scope (the specification this checklist is derived from)

The first version implements exactly this loop and nothing more:

```text
Project Specification (PDF/DOCX upload)
        ↓
AI-generated implementation checklist (heuristic/LLM task extraction)
        ↓
Developer reviews checklist
        ↓
Checklist stored in Postgres (Task rows)
        ↓
Developer writes code → GitHub commit → webhook fires
        ↓
Analyze commit + changed files
        ↓
Determine affected tasks (AI, keyword/file-overlap or LLM)
        ↓
Generate evidence-backed status-update suggestions (Suggestion rows)
        ↓
Human approval (approve/reject, never automatic)
        ↓
Task status updated, ActivityLog entry recorded
```

Hard constraints for V1, do not violate them:

- **No Notion writes.** Notion sync is an explicit future feature. The
  `Integration` model (`src/models/integration.py`) already reserves an
  `IntegrationType.NOTION` value for later — do not implement the write
  path in V1, only the schema placeholder.
- **Internal Postgres task DB is the source of truth.** Jira/Linear/
  ClickUp/Confluence are future sync targets, not V1 work. This DB is now
  hosted on Supabase; that changes *where* it runs, not this constraint.
- **Identity is Supabase Auth's job, not this app's.** GitHub OAuth
  (authorize/callback/token exchange) is configured entirely in the
  Supabase dashboard and handled by `supabase-js` client-side — this app
  never mints its own session tokens, it only verifies the JWT Supabase
  issues (`core/security.py`) and stores the GitHub provider token
  (`profiles.github_access_token`, via `POST /auth/sync`) for calling the
  GitHub API server-side. Do not reintroduce a custom login/callback
  endpoint or a custom-signed JWT — that was the pre-Supabase architecture
  and is gone on purpose.
- **Every table has RLS enabled.** New tables need `ENABLE ROW LEVEL
  SECURITY` plus an ownership-scoped policy in the same migration that
  creates them — see `alembic/versions/001_initial_schema.py`'s
  `_enable_rls()` for the pattern (direct `owner_id = auth.uid()` for
  top-level tables, an owning-repository subquery for child tables). This
  app's own backend connects with a role that bypasses RLS by design; the
  policies protect the direct PostgREST/supabase-js access path.
- **GitHub is the only repository provider.** `src/services/github.py`
  (`GitHubService`) is the integration point. When GitLab/Bitbucket support
  is eventually added, it must sit behind the same shape of service class
  and the `IntegrationType` enum already anticipates this
  (`GITLAB` is already a member) — do not hardcode GitHub-specific logic
  into route handlers; keep it inside the service layer so a second
  provider is an additive change, not a rewrite.

---

## 7. Known Repo State (last updated 2026-08-02 evening, verify before trusting)

This section exists so a future autopilot iteration doesn't have to
rediscover the same things from zero. It is a snapshot, not a guarantee —
re-verify before acting on it, per the memory/evidence discipline above. Full
per-item evidence lives in `CHECKLIST.md`; this is the condensed version.

**Fixed as of the 2026-08-02 pass** (see `CHECKLIST.md` for evidence on each):
- The Express mock server is gone; `apps/api/package.json` now runs the real
  FastAPI app via `uvicorn`.
- The 5 orphaned mock-era frontend pages/components are gone or rebuilt as
  real, repo-scoped nested pages (`repositories/[id]/{tasks,suggestions,activity,upload}`).
  `npx tsc --noEmit` and `npm run build` are both clean.
- `npm install` succeeds. This required removing two unused, React-19-incompatible
  dependencies (`framer-motion`, `recharts`) that combined with a stale lockfile
  to cause a **duplicate React copies** bug (`node_modules` had both React 18
  and 19 installed), which broke `next build`'s prerendering with a cryptic
  `Minified React error #31` on the built-in `/404`/`/500` pages. Bisected
  against a from-scratch minimal repro before finding the root cause via
  `npm ls react` — don't assume a React/Next version bump alone fixes a build
  error like this; check for duplicate copies first (`npm ls react`).
- A genuine crash bug was found and fixed: `ActivityLog.metadata` collided
  with SQLAlchemy Declarative's reserved `Base.metadata` attribute, meaning
  the backend could never have started on any Python version. Only found by
  actually attempting `from src.main import app` — reading the model file
  would not have caught it.
- SPEC-004 (review before save) and WEBHOOK-003 (real diff retrieval) are now
  implemented — see `CHECKLIST.md` for the exact endpoints/files.
- 11 backend unit tests exist and pass (`apps/api/tests/`), covering webhook
  signature verification and the AI heuristic service.

**Verified this session against a real, running stack** (portable Python
3.11.15 fetched into the session scratchpad since this sandbox's system
`python3` is 3.9; a local Postgres 18 fetched the same way, running on
`127.0.0.1:5433`; `apps/api/.env` created pointing at it — see
`CHECKLIST.md` for the full trail). This found and fixed **five more real
bugs that only surface when the app actually runs**, none of which reading
the code would have caught:
- `ActivityLog.metadata` collided with SQLAlchemy's reserved attribute —
  the app couldn't import, on any Python version.
- `greenlet` was missing from `requirements.txt` — every request touching
  `Depends(get_db)` 500'd during session teardown.
- The Alembic migration created every Postgres ENUM type **twice** (once in
  an upfront block, once implicitly via each `sa.Enum(...)` column) —
  `alembic upgrade head` failed immediately on a real database.
- Every enum-typed column bound by the Python enum's **name** ("TODO")
  instead of its **value** ("todo") — every task/suggestion/spec/activity
  write failed against the real Postgres enum types.
- `TaskOut.subtasks` triggered a lazy SQLAlchemy relationship load from
  inside Pydantic's synchronous `model_validate`, which isn't awaited —
  `MissingGreenlet` on every task create/read/update.

With all five fixed, the entire V1 loop was exercised end-to-end for real:
seed a user + repo → create tasks → POST a real webhook push (real HMAC
signature) → AI creates suggestions → list them → approve one → task status
flips to `done` → activity log shows every step. This is strong evidence
none of the previous "COMPLETED (by inspection)" gradings were wrong, but
also proof that inspection alone would never have caught any of the five
bugs above — run the thing.

The user's own long-running dev server (`npm run dev`, started before any
of this) had crashed at import on the stale Python 3.9 venv and sat dead on
port 8000 for over an hour — that's what "auth/login gives Internal Server
Error" turned out to be. If you see a proxy-level 500 from the frontend on
`/api/*`, check whether something is actually listening on port 8000
(`lsof -iTCP -sTCP:LISTEN`) before assuming it's a code bug.

**Local dev environment note:** `apps/api/.venv` is now built against a
portable Python 3.11.15 (not this sandbox's system `python3`, which is
3.9.6 and can't run `src/core/security.py`'s `str | None` syntax) and a
local Postgres 18 is running on `127.0.0.1:5433`, both fetched into the
session scratchpad. `apps/api/.env` points at that Postgres. **Both are
session-local, not committed, and won't survive past this sandbox** — a
persistent dev setup still needs its own Python 3.11+ (`pyenv`/`brew`) and
its own Postgres. Do not "fix" the Python-version syntax by downgrading it
to work around a missing interpreter — install the interpreter instead.

**Architecture pivot this pass (2026-08-02 evening): identity and the
database moved to Supabase**, at the user's request (their real GitHub
OAuth callback is `https://sodpgvxgrclvjawylrli.supabase.co/auth/v1/callback`
— i.e. GitHub OAuth is configured in their Supabase project, not as a
standalone GitHub OAuth App this backend talks to directly). What changed:
- GitHub OAuth is now entirely Supabase-managed. This app's own
  `/api/v1/auth/login` and `/auth/callback` endpoints are **deleted** — they
  no longer exist. The frontend calls `supabase.auth.signInWithOAuth`
  directly (`apps/web/src/lib/supabase.ts`, new). This app only verifies the
  resulting JWT (`core/security.py::decode_supabase_token`, HS256 against
  `SUPABASE_JWT_SECRET`) and captures the GitHub provider token once via the
  new `POST /auth/sync` (Supabase doesn't persist/refresh that token for
  us).
- The custom `users` table is gone. Identity lives in Supabase's own
  `auth.users` (never created/migrated by this app — it already exists in
  any Supabase project). `apps/api/src/models/profile.py` (`public.profiles`)
  is a 1:1 extension keyed by the same id, auto-populated by a Postgres
  trigger (`handle_new_user()`, in the migration) on every `auth.users`
  insert, reading GitHub-shaped `raw_user_meta_data`.
- Every `owner_id`/`user_id`/`reviewed_by` column now references
  `auth.users(id)`. **Important gotcha, already hit and fixed once:**
  declaring these as SQLAlchemy `ForeignKey("auth.users.id")` at the ORM
  level crashes on the first write (`NoReferencedTableError` — SQLAlchemy's
  flush machinery needs FK targets in its own `MetaData`, and `auth.users`
  deliberately isn't mapped here). The DB-level constraint is defined via
  raw DDL in the Alembic migration instead (works fine there — no ORM
  mapper resolution involved); the model columns are plain `UUID`, no
  `ForeignKey()` wrapper. Don't re-add one.
- **Every table has Row Level Security enabled**, with ownership-scoped
  policies (`_enable_rls()` in the migration). Genuinely tested — not just
  declared — against a locally-stubbed `auth` schema: a non-superuser role
  set to one user's `auth.uid()` could see its own repository but not
  another seeded user's. This app's own backend still connects via a
  role/connection string that bypasses RLS (by design); the policies exist
  for the direct PostgREST/supabase-js access path.
- Frontend: `lib/api.ts`, `lib/auth.ts`, `AuthProvider.tsx` rewritten to pull
  the Bearer token from the current Supabase session instead of a custom
  `localStorage` token.

**Still open / genuinely blocked:**
- **No real Supabase project credentials in this sandbox.** All of the
  above was verified against a *stub* of Supabase's `auth` schema (a
  minimal `auth.users` table + `auth.uid()` function), not the user's real
  project — that requires `SUPABASE_JWT_SECRET`/`SUPABASE_SERVICE_KEY`/
  `DATABASE_URL` (backend, `apps/api/.env`) and
  `NEXT_PUBLIC_SUPABASE_ANON_KEY` (frontend, `apps/web/.env.local` — already
  has the real project URL, needs the real anon key swapped in for the
  placeholder). The stub is close enough to validate the SQL/trigger/RLS
  logic; it is not a substitute for one real run against production
  Supabase.
- **`src/services/ai.py`'s `AIService` is an explicit heuristic placeholder**
  (regex/keyword-overlap, not an LLM call) — real, tested, and now proven to
  work end-to-end against a live webhook → suggestion → approval flow, but
  a product decision is still open on whether V1 needs an actual LLM call.
- **AUTH-004 frontend gating is client-side only** (`useEffect` redirect, no
  Next.js middleware) — works, but a protected page briefly renders before
  redirecting; not fixed this pass, flagged as a possible follow-up.
- **No commits UI** — the `GET /repositories/{id}/commits` endpoint and
  `commitsApi` client exist and were verified via the live DB, but no page
  renders them yet.

---

## 8. Safety Rules (operate autonomously — don't stop to ask)

**Standing authorization:** the user has explicitly told autopilot to run
without pausing for permission. Do not ask before implementing, refactoring,
deleting superseded/dead code, making architecture calls within the stated
V1 scope, installing/upgrading a dependency to fix a real incompatibility,
or any other ordinary engineering judgment call — just do it, verify it,
record it in `CHECKLIST.md`, and move to the next item. Git history is the
undo button for anything reversible; use it instead of asking first. This
is the default operating mode for this file — treat "should I check with
the user first?" as already answered "no" for everything in this
paragraph.

Allowed autonomously (non-exhaustive): inspecting files, editing
application code, deleting code confirmed superseded/unreachable, adding
tests, updating docs, running local tests/typecheck/lint/build, installing
or upgrading dependencies to fix a real conflict, running local dev servers
and hitting them to verify behavior, creating/migrating a local dev
database, reading logs.

The only things that still require stopping and reporting `BLOCKED`
instead of proceeding — because they're externally visible, hard to
reverse, or security-sensitive, not because they need a design opinion:

- Expose, print, or commit secrets/API keys/tokens (`.env`, GitHub
  client secret, webhook secret, DB credentials).
- Run destructive operations against data that isn't yours to lose — e.g.
  `DROP`/`TRUNCATE`/`alembic downgrade` against a shared or production
  database (a local, autopilot-managed dev/test database is fair game).
- Modify production infrastructure, CI/CD config, or anything outside this
  repo, without approval.
- Delete or bypass a failing test/security check to make a build pass.
- Force-push, rewrite git history, or delete branches.
- Push to a remote, open/merge a PR, or otherwise publish changes outside
  this local checkout.

Everything else: run it, don't ask.

---

## 9. Definition of Done

Autopilot may stop only when every item in `CHECKLIST.md` is `COMPLETED`,
or every remaining item is genuinely `BLOCKED` with a stated, real reason.
Before stopping, produce this report:

```text
## Autopilot Result

### Completed
- [x] ID — requirement (evidence)

### Partial
- [ ] ID — requirement (what's missing)

### Blocked
- [ ] ID — requirement (exact blocker, what would unblock it)

### Verification
- Tests:
- Type checking:
- Lint:
- Build:
- Integration checks:

### Remaining Issues
...

### Files Changed
...

### Recommended Next Steps
...
```

Do not claim 100% completion unless `CHECKLIST.md` and the verification
evidence actually support it.
