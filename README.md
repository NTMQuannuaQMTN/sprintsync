# SprintSync

An AI engineering-operations agent: it watches what actually happens in a
GitHub repository — commits, diffs, pull requests — understands the work
in context of your project's real task list, and proposes task-board
updates for a human to approve. Not "GitHub commits can update a board"
(a GitHub Action + a webhook can already do that); the point is the AI
reasoning in between: matching real diffs to real tasks, judging whether
a status change is actually justified, and staying honest about its own
confidence.

## Why this exists

Plenty of tools connect GitHub to a task board. What they don't do is
*understand* the work: a commit message claiming "fixes login bug" isn't
the same as a diff that actually fixes it, and "this pushed to `main`" is
not the same as "this task is done." SprintSync's differentiator is the
reasoning layer sitting between the two — not another integration.

Concretely, that means:

1. **AI understanding of engineering activity** — the model reads the
   actual diff, not just the commit message/PR title (see
   `apps/api/src/services/ai_reasoning/`).
2. **Automatic task matching** — branch name, commit message, PR
   title/body, changed files, and an explicit `#<task-id>` reference when
   present (`apps/api/src/services/task_matching.py`).
3. **Intelligent, confidence-gated state transitions** — a suggestion is
   only ever *proposed*; a human always approves before a task's status
   actually changes (`apps/api/src/api/v1/suggestions.py`).
4. **Context-aware summaries** — real Claude-generated (or heuristic
   fallback) summaries of a commit, PR, or a repo's daily/weekly activity
   (`apps/api/src/services/ai_reasoning/summarization.py`).
5. **Project intelligence** — stale tasks, unmatched activity, and
   unusually large changes, computed from real data, clearly distinguished
   from AI inference (`apps/api/src/services/project_intelligence.py`).
6. **Developer-native workflow** — a GitHub Action alternative to a
   webhook install, so it works even without repo-admin access (see
   [`docs/GITHUB_ACTION.md`](docs/GITHUB_ACTION.md)).
7. **Platform-independent architecture** — a `TaskBoardProvider`
   abstraction (`apps/api/src/services/taskboard/`) so the reasoning layer
   never talks to Notion/Jira directly; today's providers are the internal
   Postgres board and Notion.

## Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │              GitHub (source of truth)        │
                    │   push webhook · PR webhook · GitHub Action   │
                    └───────────────────┬───────────────────────────┘
                                        │ signed webhook, or a
                                        │ token-authenticated Action call
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │  Ingestion (api/v1/webhook.py)                │
                    │  - signature verification (fail-closed)        │
                    │  - generic delivery idempotency                │
                    │  - stores raw event → Commit / PullRequest    │
                    └───────────────────┬───────────────────────────┘
                                        │ normalized event
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │   AI Reasoning (services/ai_reasoning/)       │
                    │  - system/repo-content strictly separated      │
                    │  - real diff content, not just the message     │
                    │  - Claude API, Pydantic-validated output       │
                    │  - heuristic fallback if no API key            │
                    └───────────────────┬───────────────────────────┘
                                        │ {task_id, confidence, evidence}
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │   Task Matching (services/task_matching.py)   │
                    └───────────────────┬───────────────────────────┘
                                        │ matched task + confidence
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │  Suggestion (human-review queue)               │
                    └───────────────────┬───────────────────────────┘
                                        │ on approve
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │  TaskBoardProvider (services/taskboard/)      │
                    │  ┌───────────────┐  ┌───────────────┐         │
                    │  │ InternalBoard │  │ NotionBoard    │  ...    │
                    │  │ (Postgres,    │  │ (real Notion   │         │
                    │  │  default)     │  │  API calls)    │         │
                    │  └───────────────┘  └───────────────┘         │
                    └─────────────────────────────────────────────┘
```

**Stack**: FastAPI (Python 3.11, async SQLAlchemy 2.0 + asyncpg) backend;
Next.js 15 / React 19 frontend; Postgres on Supabase; Supabase Auth
(GitHub OAuth); deployed on Vercel.

For the full architecture writeup, current problems/limitations, and the
phase-by-phase build log, see [`docs/V2_IMPLEMENTATION_PLAN.md`](docs/V2_IMPLEMENTATION_PLAN.md)
and [`docs/V2_TEST_REPORT.md`](docs/V2_TEST_REPORT.md).

## Supported integrations

| Provider | Status |
|---|---|
| Internal (Postgres) task board | Default, always available |
| Notion | Real, working — connect via Settings → Integrations (or `POST /integrations/notion/connect`); mirrors an approved status change onto a matching Notion page by title lookup |
| Jira / Linear | Not implemented — the `TaskBoardProvider` abstraction supports adding them |

## Setup

### Backend (`apps/api`)

```bash
cd apps/api
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn src.main:app --reload --port 8000
```

Environment variables (`.env`, see `src/core/config.py`):

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://...` — Supabase's connection string. If pointed at Supabase's Transaction Pooler (port 6543), the app already handles PgBouncer's unnamed-prepared-statement requirement (see `core/database.py`) |
| `SUPABASE_URL` | Yes | Used to fetch the JWKS for verifying Supabase-issued JWTs |
| `SUPABASE_SERVICE_KEY` | Yes | Supabase Storage access (spec-upload feature) |
| `GITHUB_WEBHOOK_SECRET` | Recommended | Without it, webhook signature verification fails closed — no webhook will be accepted at all until this is set |
| `FRONTEND_URL` | Yes | CORS + the webhook URL registered with GitHub |
| `ANTHROPIC_API_KEY` | Optional | Enables real Claude-based reasoning/summarization; without it, the app runs entirely on the heuristic fallback (`evidence.source: "heuristic"` on every suggestion) |
| `ENV` | Optional | `development` (default) or `production` — also controls log rendering (console vs JSON), see `core/logging.py` |

### Frontend (`apps/web`)

```bash
cd apps/web
npm install
npm run dev
```

Environment variables (`.env.local`):

| Variable | Notes |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key |
| `API_URL` | Server-side only (Vercel rewrite target) — where the FastAPI backend is reachable from |

### GitHub setup

1. Configure GitHub as an OAuth provider in the Supabase dashboard
   (Authentication → Providers → GitHub), requesting at least `repo` and
   `read:org` scopes.
2. Connect a repository from the Repositories page. If the connecting
   user has admin access, SprintSync installs a webhook automatically
   (or via the repo detail page's "Install" button if it wasn't set up
   at connect time).
3. If the user is **not** a repo admin, webhook install isn't possible —
   use the GitHub Action path instead (see below).

### Task-board setup (Notion)

Settings → Integrations → Connect Notion, with a Notion internal
integration token and the target database's id. The connection is
verified live against the Notion API before anything is saved.

### GitHub Action setup (no repo-admin required)

See [`docs/GITHUB_ACTION.md`](docs/GITHUB_ACTION.md) for the full guide,
and [`docs/examples/sprintsync-sync.yml`](docs/examples/sprintsync-sync.yml)
for a copy-pasteable workflow. Short version:

1. Generate a token from the repository detail page's Connections card
   (or `POST /repositories/{id}/action-token`).
2. Store it as that repo's `SPRINTSYNC_TOKEN` Actions secret.
3. Add the example workflow, pointing `api_url` at your deployment.

### AI configuration

Set `ANTHROPIC_API_KEY` to enable the real reasoning/summarization path
(model: `claude-opus-5`). Every AI call degrades gracefully to a
heuristic (keyword/filename overlap for matching, a template sentence for
summaries) on a missing key, a network failure, a safety refusal, or
invalid/schema-violating model output — never a hard failure, and always
visibly labeled via `evidence.source` / a summary's `source` field so the
origin is never hidden.

## Security

- Webhook signatures are verified HMAC-SHA256 and **fail closed** — an
  unset `GITHUB_WEBHOOK_SECRET` rejects every webhook rather than
  accepting unsigned requests.
- The GitHub Action path uses a separate per-repo bearer token; the
  repository is resolved by that token, never by the payload's own claims.
- Commit messages, PR titles/bodies, and diffs are treated as **untrusted
  input** throughout the AI reasoning layer — always wrapped in an
  explicit `<activity>`/`<diff>` block, with the system prompt explicitly
  instructing the model never to treat that content as an instruction.
  Tested adversarially (see `apps/api/tests/test_ai_reasoning.py`).
- Structured logs never include tokens/secrets — only ids, names, counts,
  and error messages (`apps/api/src/core/logging.py`).
- Nothing mutates a task's real status without human approval — the
  Suggestion review queue is the sole gate, unchanged from V1.

## Testing

```bash
cd apps/api && .venv/bin/pytest -q      # 109 tests, real DB + mocked LLM/Notion boundaries
cd apps/api && .venv/bin/ruff check src/ tests/
cd apps/api && .venv/bin/mypy src
cd apps/web && npx tsc --noEmit && npm run build
```

See `docs/V2_TEST_REPORT.md` for the full, dated log of what was actually
run and what it returned.

## Deployment

Both apps deploy to Vercel. The API runs on Vercel's Python runtime via
`apps/api/api/index.py`; note that Vercel's Python builder prefers
`pyproject.toml` over `requirements.txt` when both exist, so any new
runtime dependency must be added to **both** files (dev/test-only tools
like `pytest` are deliberately requirements.txt-only). Deploy from the
monorepo root, not from inside `apps/api` or `apps/web`.

## Known limitations

- Jira and Linear providers aren't implemented (the abstraction supports
  adding them).
- The Notion mirror matches an existing page by title only — it doesn't
  create a page for a task with no match, and there's no persisted
  Task-to-Notion-page-id mapping yet.
- No UI exists yet to configure a repository's status-mapping overrides
  (the API endpoint is real: `PATCH /repositories/{id}/status-mapping`).
- Full CI/CD (running this repo's own tests on every push) isn't set up.
- The GitHub Action was verified by running its exact shell script
  locally against a live instance, not against an actual hosted GitHub
  Actions runner.
- Live LLM and live Notion API calls are implemented and request-shape
  verified, but not exercised end-to-end in this environment (no
  `ANTHROPIC_API_KEY` / Notion token available here).

## Where to go next (V3)

The most natural next step is closing the Notion mirror's biggest gap: a
persisted `Task` ↔ Notion-page mapping (created on first successful sync,
not just looked up by title), which would also unlock two-way sync
(a status changed directly in Notion reflected back into SprintSync).
After that: a real Jira provider (the abstraction is ready for it), and
surfacing per-repository status-mapping configuration in the UI.
