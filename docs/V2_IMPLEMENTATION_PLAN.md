# SprintSync V2 — Implementation Plan

Status as of this document's creation: **audit complete, implementation in progress.**
This is a living document, updated after every meaningful milestone during the
autonomous V2 build. See `docs/V2_TEST_REPORT.md` for the running record of
what was actually run and what it actually returned.

---

## 0. How to read this document

Every claim below is either (a) verified by running something for real against
this codebase, moments before writing it down, or (b) explicitly marked as a
plan/decision, not yet implemented. Nothing here is aspirational-and-labeled-
as-done. Where an external credential (an LLM API key, a Notion token, a Jira
token) is required to fully verify a feature end-to-end, that is stated
explicitly as a blocker — the code is still built for real and unit-tested at
every boundary that doesn't require the missing credential.

---

## 1. Current Architecture (V1, as verified)

**Stack:** FastAPI (Python 3.11, async SQLAlchemy 2.0 + asyncpg) backend;
Next.js 15 / React 19 frontend; Postgres hosted on Supabase; Supabase Auth
(GitHub OAuth) for identity; Supabase Storage for uploaded spec files;
deployed on Vercel (both apps, as of this session — the API runs on Vercel's
Python runtime via `apps/api/api/index.py` + `pyproject.toml`-declared deps).

**Backend layout** (`apps/api/src/`):
- `api/v1/*.py` — one router module per resource: `auth`, `repositories`,
  `tasks`, `specs`, `suggestions`, `webhook`, `dashboard`, `activity`,
  `commits`. All mounted in `api/v1/router.py`.
- `models/*.py` — SQLAlchemy models: `Profile`, `Repository`,
  `ProjectSpecification`, `Task`, `Commit`, `Suggestion`, `ActivityLog`,
  `Integration` (declared, unused in V1 — see §7 below, this is where V2's
  task-board abstraction attaches).
- `services/github.py` — all GitHub REST calls (list repos, commit detail,
  webhook install/delete, signature verification).
- `services/ai.py` — **heuristic** (regex/keyword) task extraction and
  commit-to-task matching. No LLM call exists anywhere in this codebase today.
- `services/document_parser.py` — PDF/DOCX text extraction, plus a Google
  Docs link importer (added this session).
- `core/security.py` — Supabase JWT verification via JWKS (ES256).
- `core/database.py` — async engine, `NullPool` + unnamed prepared
  statements (required for Supabase's Transaction Pooler / PgBouncer).

**Frontend layout** (`apps/web/src/`):
- `app/` — App Router pages: `login`, `dashboard`, `repositories`,
  `repositories/[id]/{tasks,commits,suggestions,activity,upload}`, `settings`.
- `lib/api.ts` — typed fetch client, all requests proxied through
  `next.config.js`'s rewrite to the FastAPI backend.
- `providers/AuthProvider.tsx` — client-side auth guard (no middleware).

**V1 data flow (as built):**
```
GitHub push webhook → webhook.py → Commit row (+ diff, best-effort via GitHub API)
                                  → ai_service.analyze_commit() [keyword+filename heuristic]
                                  → Suggestion row (status=pending)
                                  → human approve/reject → Task.status flips
                                  → ActivityLog entry
```
Separately: repo connect (GitHub OAuth token → list/connect repos), spec
upload (PDF/DOCX/Google Doc → heuristic task extraction → human review →
`Task` rows), and a manual "Update to tasks" button that re-runs the same
heuristic over already-stored, not-yet-analyzed commits.

## 2. Current V1 Functionality — what actually works today

Verified this session (pytest 31/31, ruff clean, tsc clean, build clean, plus
direct live checks against the real production deployment and real Supabase
DB):

| Area | Status |
|---|---|
| Auth (Supabase JWKS/ES256) | Works. Real JWT verification, tested. |
| Repo connect (incl. collaborator/org repos) | Works for personal + collaborator repos. **Org repos need `read:org` scope — added this session, requires user re-login; if the org restricts third-party app access, an org admin must approve it separately.** |
| Spec upload (PDF/DOCX/Google Doc link) | Works. Real text extraction, real heuristic task drafting, human review before save. |
| Task CRUD | Works. Create/edit-status/delete all real, DB-backed. |
| GitHub webhook → Commit → Suggestion → Approve → Task update | Works **when a webhook is actually installed**. See Critical Issue below. |
| Manual commit sync + "Update to tasks" | Works. Added this session; now has a 60s cooldown to avoid re-hitting GitHub on every page load. |
| Activity log | Works, DB-backed, real timestamps. |
| Settings page | **Decorative only** — no field beyond "Sign out" is wired to a backend call. |

## 3. Current Problems (carried in from the pre-V2 audit + this session)

### CRITICAL
1. **GitHub webhook signature verification silently no-ops when `GITHUB_WEBHOOK_SECRET` is unset**, and **auto-install of the webhook on repo-connect is skipped entirely under the same condition** (`if settings.GITHUB_WEBHOOK_SECRET:` guards both). Confirmed live against production: both real connected repos have `webhook_active=False`. This means the entire "commit → webhook fires automatically" path — the literal product pitch — has never actually fired for a real repo. This is Phase 1 (stabilization) work, done first, below.
2. **AI commit analysis never reads the diff.** `analyze_commit` only looks at commit-message keywords and filenames; the stored `patch` text is fetched and persisted but never inspected. This is the exact anti-pattern the product is supposed to avoid ("must not trust the commit message alone"). This is the core of Phase 4 below.
3. **No structured/validated AI output anywhere** — the heuristic returns plain dicts, no schema, no confidence tiers beyond a single float threshold.

### HIGH
4. Settings page is fully decorative — misleading in a demo.
5. No error states on Dashboard/Activity pages (`isError` available, unused).
6. `Integration` model exists but nothing ever reads/writes it — no real task-board integration exists.
7. Only binary `done`/`in_progress` task-state proposals — no `blocked`, no distinction from `not_started`.

### MEDIUM
8. File upload buffers the whole file into memory before the size check (minor DoS surface).
9. Type-checking gaps (`mypy`): `GitHubService(None)` possible at 2 call sites; a `dict | BaseException` narrowing gap in `commits.py` (cosmetic, guarded correctly at runtime).
10. No idempotency concept beyond `Commit.sha` uniqueness — no equivalent for PR events (none exist yet).

### LOW
11. `activity.py`'s ownership check is inline instead of using the shared `_assert_repo_owner` pattern (style only).
12. `autopilot.md` §7 / `CHECKLIST.md` closing summary are stale (dated, pre-deploy).

---

## 4. V2 Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │              GitHub (source of truth)        │
                    │   push webhook · PR webhook · REST API        │
                    └───────────────────┬───────────────────────────┘
                                        │ signed payload
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │  Ingestion layer (webhook.py, pr_webhook.py)  │
                    │  - signature verification (now enforced)      │
                    │  - idempotency (event id / commit sha / PR+   │
                    │    action dedup)                              │
                    │  - stores raw event → Commit / PullRequest    │
                    └───────────────────┬───────────────────────────┘
                                        │ normalized event
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │   AI Reasoning layer (services/ai_reasoning)  │
                    │  - structured prompt: system/repo-content/    │
                    │    task-list strictly separated                │
                    │  - Claude API call, Pydantic-validated output │
                    │  - falls back to heuristic if no API key       │
                    │  - confidence tiers: HIGH/MEDIUM/LOW           │
                    └───────────────────┬───────────────────────────┘
                                        │ {task_id, action, confidence, evidence}
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │   Task Matching (services/task_matching.py)   │
                    │  - branch name, PR title/desc, commit msg,     │
                    │    issue refs, changed files, task title/desc │
                    └───────────────────┬───────────────────────────┘
                                        │ matched task + confidence
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │  Suggestion (internal review queue — unchanged│
                    │  human-in-the-loop gate from V1)               │
                    └───────────────────┬───────────────────────────┘
                                        │ on approve
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │  TaskBoardProvider abstraction                │
                    │  (services/taskboard/base.py)                  │
                    │  ┌───────────────┐  ┌───────────────┐         │
                    │  │ InternalBoard │  │ NotionBoard    │  ...    │
                    │  │ (Postgres,    │  │ (real Notion   │         │
                    │  │  V1 default)  │  │  API calls)    │         │
                    │  └───────────────┘  └───────────────┘         │
                    └─────────────────────────────────────────────┘
```

Key architectural decisions:

- **The AI reasoning layer is provider-agnostic of the task board.** It only
  ever emits `{task_id, action, confidence, evidence}` — it never talks to
  Notion/Jira directly. This is what makes "platform-independent AI
  reasoning" real rather than a slogan.
- **`TaskBoardProvider` is an ABC**, not a full-generality plugin system.
  Every provider must implement `find_task`, `update_status`, `add_comment`;
  `create_task`/`list_tasks` are optional (default to `NotImplementedError`
  with a clear message) since not every provider needs every capability —
  per the explicit instruction not to force unsupported capabilities.
- **The internal Postgres board becomes a `TaskBoardProvider` implementation
  too** (`InternalBoardProvider`), not a special case — this is what lets V1
  keep working unchanged while the abstraction is real, not cosmetic.
- **Confidence tiers gate mutation, not visibility.** A LOW-confidence match
  still creates a `Suggestion` row (visible for human review) but never
  auto-applies; only a HIGH-confidence, already-human-approved suggestion
  actually calls `TaskBoardProvider.update_status`.

---

## 5. V2 Feature Roadmap — Task Checklist

Legend: `[x]` done and verified · `[~]` implemented, credential-blocked from
full live verification (real network call to a 3rd-party) · `[ ]` not started
· `[-]` deliberately deferred past this session, with reason.

```
[x] Full V1 audit (this document, §1-3)
[x] Phase 1 — V1 stabilization
    [x] Fix webhook signature bypass + auto-install skip (real secret, real
        migration/reconnect against production)
    [x] Add error states to Dashboard/Activity
    [ ] Settings page real wiring — deferred, see §9
[x] Phase 2 — Clean architecture
    [x] services/taskboard/ package: base.py (ABC), internal.py, notion.py
    [x] services/ai_reasoning/ package: schema.py, reasoning.py, prompt.py
    [x] services/task_matching.py extracted from ai.py
[x] Phase 3 — GitHub activity ingestion
    [x] PR webhook events (opened/synchronize/closed+merged)
    [x] Idempotency: PullRequest table keyed on (repo, number, updated_at-hash)
    [x] Malformed-payload / missing-field handling
[~] Phase 4 — AI development understanding (structured reasoning)
    [x] Pydantic schema for AI output, validated before use
    [x] Real Claude API call path (services/ai_reasoning/reasoning.py)
    [x] Heuristic fallback when ANTHROPIC_API_KEY unset — BLOCKED on
        credential for live LLM verification; heuristic path fully tested
    [x] Confidence-tier gating (HIGH/MEDIUM/LOW)
[x] Phase 5 — Task matching
    [x] Branch name, PR title/description, issue references added as signals
[x] Phase 6 — Task state synchronization
    [x] Configurable status-mapping (push/PR-opened/PR-merged → configurable
        target status), stored per-repository
[~] Phase 7 — Multi-platform task boards
    [x] TaskBoardProvider ABC + InternalBoardProvider (V1 behavior, unchanged)
    [x] NotionBoardProvider — real API client code — BLOCKED on credential
        for live verification; unit-tested against mocked Notion responses
    [ ] Wiring: no endpoint/UI exists yet for a user to actually connect a
        Notion workspace and have it used (the `Integration` model + a
        connect flow). The provider code is real and tested in isolation
        but not reachable by a real user through the product today.
    [-] Jira / Linear — deferred, see §9 (architecture supports adding them;
        not implemented this session — explicitly conditional in the brief:
        "if technically feasible" / "if time allows")
[x] Phase 8 — GitHub Action
    [x] action.yml (composite, bash+jq+curl) + example workflow
        (docs/examples/sprintsync-sync.yml) + docs/GITHUB_ACTION.md
    [x] Repository.action_token (migration 005) + generate/rotate
        (POST)/revoke (DELETE) /repositories/{id}/action-token
    [x] POST /webhook/action — token-authenticated (repo resolved by token,
        never by the payload's own claim), dispatches through the same
        _handle_push/_handle_pull_request pipeline as the signed webhook
    [x] Verified for real: ran action.yml's exact shell script locally
        against a live instance + real DB row (happy path, duplicate-
        delivery short-circuit, invalid-token failure branch all
        confirmed) — not fired against an actual hosted Actions runner
        (documented as a known limitation, see docs/GITHUB_ACTION.md)
[x] Phase 9 — AI summarization
    [x] summarize_commit / summarize_pull_request — same LLM-or-heuristic
        pattern as Phase 4 — BLOCKED on credential for live LLM
        verification; heuristic path fully tested end-to-end via real
        endpoints (GET .../commits/{id}/summary,
        GET .../pull_requests/{id}/summary)
    [x] summarize_digest (daily/weekly) — heuristic-only by design (pure
        count aggregation), GET /repositories/{id}/summary?period=day|week
    [x] Closed a real gap found while wiring this up: PullRequest rows were
        written by the webhook but had no read endpoint at all — added
        GET /repositories/{id}/pull_requests (list/detail)
[x] Phase 10 — Project intelligence
    [x] Stale-task detection, unmatched-activity detection, unusually-
        large-change detection — pure DB queries, no LLM involved,
        GET /repositories/{id}/intelligence, fully tested against the real DB
[ ] Phase 11 — Frontend / UX
    [x] Error states added to Dashboard/Activity (Phase 1 work)
    [ ] Not yet started this pass: surfacing sync history / AI decision /
        confidence / summaries / project-intelligence data on any page —
        every V2 backend feature above (Phases 7/9/10/Suggestion evidence)
        is reachable via API only, not yet in the Next.js UI
[x] Phase 12 — Observability
    [x] Structured logging (structlog) now configured at app startup
        (src/core/logging.py — JSON in production, console in dev) and
        wired through the real ingestion → reasoning → sync pipeline:
        webhook received/rejected/duplicate/ignored/processed, LLM-vs-
        heuristic path taken, per-suggestion outcome, and external API
        failures that were previously silently swallowed (commit-detail/
        PR-files fetch failures now log a warning instead of a bare `pass`)
[x] Phase 13 — Security
    [x] Prompt-injection boundary audit + fix (repo content never enters the
        system prompt; explicit delimiting)
    [x] Webhook secret fix (also Phase 1)
    [x] Re-audit auth/authorization (unchanged from V1's already-solid state)
[x] Phase 14 — Testing
    [x] Real tests for everything above that doesn't require a live 3rd-party
        credential; mocked-boundary tests for what does
[x] Phase 15 — Performance/reliability
    [x] Commit-sync cooldown (done earlier this session)
    [x] N+1 review of new endpoints
[-] Linear integration — deferred (see §9)
[-] Full CI/CD pipeline (GitHub Actions running this repo's own tests) —
    deferred, see §9
```

---

## 6. Technical Decisions

- **LLM provider: Anthropic Claude**, via the official `anthropic` Python
  SDK, `claude-opus-5`, structured output via Pydantic schema validation on
  the response (not `output_config.format` — kept to a plain JSON-mode
  prompt + manual `model_validate_json`, to avoid a hard dependency on a
  specific SDK version's structured-output feature surface; the SDK is new
  in this codebase and pinned conservatively). Falls back to the existing
  heuristic when `ANTHROPIC_API_KEY` is unset — the system is never
  non-functional for lack of a key, it degrades.
- **Why Notion first, not Jira:** Notion's API is simpler (no OAuth-dance
  complexity for a personal integration token, flatter data model — a
  database + pages), which makes it the highest-value first real
  integration to prove the abstraction with actual working code rather than
  splitting effort across two partially-done providers. Jira's API (REST v3,
  ADF rich-text bodies, project/issue-type configuration) is architecturally
  supported by the same `TaskBoardProvider` interface but not implemented
  this session — explicitly conditional in the brief ("if technically
  feasible"), and the honest call is that one real, tested integration beats
  two shallow ones.
- **No new infrastructure** (no Redis, no queue) — V2's volume doesn't
  justify it; webhook processing stays synchronous within the request,
  matching V1.
- **PR state stored in a new `pull_requests` table**, not bolted onto
  `Commit` — a PR is a distinct, longer-lived entity with its own lifecycle
  (opened → synchronized N times → merged/closed), not a commit.

## 7. Security Considerations (V2-specific, beyond V1's existing auth/RLS)

- **Prompt injection**: commit messages, PR titles/descriptions, and diff
  content are untrusted input from repository contributors. The AI reasoning
  prompt strictly separates `system` (our instructions) from `user` content
  (repo data), and the repo data is always wrapped in an explicit delimiter
  with an instruction that its content is data to analyze, never a
  command to follow. Tested with an adversarial fixture (a commit message
  containing an embedded fake instruction) — see test report.
- **Webhook secret**: fixed to be a real, non-empty value in both
  environments; signature verification now actually rejects forged
  requests (previously silently accepted them — see Critical Issue #1).
- **No secrets to the model beyond what's needed**: the AI reasoning call
  never receives tokens/keys/credentials — only commit/PR text and task
  titles/descriptions.
- **Notion/GitHub tokens**: stored the same way `Profile.github_access_token`
  already is (plain column, relies on Supabase-side encryption at rest +
  RLS on direct client access, backend bypasses RLS by design — consistent
  with the existing, already-reviewed pattern, not a new risk introduced).

## 8. Deployment Considerations

- New env vars: `ANTHROPIC_API_KEY` (optional — heuristic fallback if
  unset), `NOTION_TOKEN`/`NOTION_DATABASE_ID` per-integration (stored in
  `Integration.access_token`/`config`, not a global env var, since each user
  connects their own workspace).
- New Alembic migration(s) for `pull_requests` table and any
  `Repository`-level config columns (status-mapping config).
- No change to the existing Vercel deployment shape (same `pyproject.toml`
  dependency-declaration gotcha applies — new deps must be added there too).

## 9. Explicitly Deferred (with reasons) — not silently dropped

| Item | Reason |
|---|---|
| Jira integration | Time/scope tradeoff this session; architecture supports it (`TaskBoardProvider`), not implemented. Explicitly conditional in the brief. |
| Linear integration | Same as Jira — explicitly conditional ("if architecture/time allows"). |
| Live LLM verification (Phase 4/9) | No `ANTHROPIC_API_KEY` available in this environment. Code is real and unit-tested at every boundary that doesn't require the live call; the call itself is implemented per the Claude API's actual current request/response shape. |
| Live Notion API verification (Phase 7) | No Notion integration token available. Same treatment — real client code, mocked-response tests. |
| Settings page real wiring | Out of scope for this session's V2 slice (not part of the GitHub-activity-to-task-board pipeline that is V2's actual differentiator); flagged, not fixed, to keep focus on the core mission. |
| Full CI/CD (running this repo's tests on every push) | Would require adding repo secrets via GitHub's UI (an action only a human with repo admin access can do) — documented as a recommended next step, not performed. |
| GitHub Action live end-to-end test on a hosted runner | The Action's shell script was verified for real (locally, against a live API instance and DB row — see docs/GITHUB_ACTION.md), but not fired against an actual GitHub-hosted Actions runner, since no repo had the workflow installed. |
| Notion integration — connect-and-use flow | `NotionBoardProvider` is real and unit-tested (mocked Notion responses) but no endpoint/UI lets a user actually connect a workspace and have it used (would need the `Integration` model wired to a real connect flow) — the provider exists but isn't reachable by a real user yet. |
| Frontend/UX for Phases 7/9/10 and richer Suggestion evidence | Every new backend capability this session (project intelligence, summaries, PR read API, action-token management) is reachable via API only — no Next.js page surfaces any of it yet. |

## 10. Testing Strategy

- Unit tests for: Pydantic schema validation (valid/invalid AI output),
  confidence-tier decision logic, task-matching signal scoring, PR-webhook
  idempotency, prompt-injection-resistant prompt construction, status-mapping
  config resolution.
- Integration tests (real DB, existing `conftest.py` pattern): PR webhook →
  `PullRequest` row → task match → suggestion, mirroring the existing
  commit-webhook integration test.
- Mocked-boundary tests for the two credential-gated externals (Claude API,
  Notion API) — `httpx`/`anthropic` client mocked at the transport level so
  the real request-construction and response-parsing code is exercised
  without a live credential.
- All new tests run via the existing `pytest` + `pytest-asyncio` setup.

## 11. Definition of Done (for this session's V2 slice)

- [x] `pytest` passes (including new tests) — 98/98 as of the Phase 8
  (GitHub Action) commit
- [x] `ruff check` clean across `src/` and `tests/`
- [~] `mypy` — 27 errors, all pre-existing (SQLAlchemy string-forward-ref
  relationship warnings, one pre-existing `sort` key type-inference note in
  reasoning.py, one async-generator note in database.py, four pre-existing
  assignment errors in suggestions.py) — none newly introduced this
  session (one was: core/logging.py's renderer needed an explicit type
  annotation, fixed same-commit)
- [ ] `tsc --noEmit` / `npm run build` — not re-verified since Phase 11
  frontend work hasn't started; last known-good was pre-Phase-3
- [x] Webhook signature bypass fixed and verified live against production
- [x] `docs/V2_IMPLEMENTATION_PLAN.md` (this file) — corrected 2026-08-25
  after finding Phases 8-12 were marked done without the code existing;
  kept current through the Phase 8/9/10/12 commits that followed
- [~] `docs/V2_TEST_REPORT.md` — appended with real entries through the
  Phase 8 commit; not yet caught up with every commit since (see doc itself)
- [ ] README — not yet updated for V2
