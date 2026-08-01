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

- GitHub OAuth: confirm `GET /api/v1/auth/login` builds the correct
  authorize URL from `settings.GITHUB_CLIENT_ID`/`GITHUB_REDIRECT_URI`;
  confirm `/auth/callback` upserts `User` by `github_id` and issues a JWT
  via `create_access_token`.
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
  ClickUp/Confluence are future sync targets, not V1 work.
- **GitHub is the only repository provider.** `src/services/github.py`
  (`GitHubService`) is the integration point. When GitLab/Bitbucket support
  is eventually added, it must sit behind the same shape of service class
  and the `IntegrationType` enum already anticipates this
  (`GITLAB` is already a member) — do not hardcode GitHub-specific logic
  into route handlers; keep it inside the service layer so a second
  provider is an additive change, not a rewrite.

---

## 7. Known Repo State (last updated 2026-08-02, verify before trusting)

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

**Still open / genuinely blocked:**
- **This sandbox's Python is 3.9.6; the project targets `>=3.11`** and uses
  PEP 604 union syntax (`str | None`) in `src/core/security.py` that 3.9
  cannot execute. No 3.11+ interpreter, `pyenv`, or `brew` is available here.
  `ruff`/`mypy`/`pytest` all run fine (they're static/isolated enough not to
  hit this), but a full `uvicorn` startup has not been achieved in this
  sandbox. Do not "fix" this by downgrading the project's syntax — that
  regresses correct code to work around a local tooling gap.
- **No reachable Postgres, no GitHub OAuth App credentials** — `alembic
  upgrade head` and any live GitHub OAuth/webhook exchange remain untested by
  execution, only by manual code trace.
- **`src/services/ai.py`'s `AIService` is an explicit heuristic placeholder**
  (regex/keyword-overlap, not an LLM call) — real and tested, but a product
  decision is still open on whether V1 needs an actual LLM call here.
- **AUTH-004 frontend gating is client-side only** (`useEffect` redirect, no
  Next.js middleware) — works, but a protected page briefly renders before
  redirecting; not fixed this pass, flagged as a possible follow-up.
- **No commits UI** — the new `GET /repositories/{id}/commits` endpoint and
  `commitsApi` client exist, but no page renders them yet.

---

## 8. Safety Rules (non-negotiable)

Allowed autonomously: inspecting files, editing application code, adding
tests, updating docs, running local tests/typecheck/lint/build, running
`npm install` for already-declared dependencies, reading logs.

Never do autonomously:

- Expose, print, or commit secrets/API keys/tokens (`.env`, GitHub
  client secret, webhook secret, DB credentials).
- Run destructive DB operations (`DROP`, `TRUNCATE`, `alembic downgrade`
  against a real DB) without explicit user approval.
- Modify production infrastructure or CI/CD config without approval.
- Delete or bypass a failing test/security check to make a build pass.
- Force-push, rewrite git history, or delete branches.
- Silently delete the legacy Express server or the orphaned frontend
  pages listed in §7 without flagging the decision to the user first —
  removing code is a judgment call about someone else's in-progress work,
  even when it looks clearly superseded.

If a required action is destructive or irreversible, stop and report it as
`BLOCKED` with the reason, instead of proceeding.

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
