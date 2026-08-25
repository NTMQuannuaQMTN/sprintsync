# SprintSync GitHub Action (V2 Phase 8)

An alternative to connecting a repository via SprintSync's GitHub webhook
install flow. Instead of SprintSync installing a webhook on your behalf
(which requires the connecting user to have **admin** access on the repo),
you add a small workflow to the repository itself, which forwards its own
`push`/`pull_request` events to SprintSync using a token you control.

This is the same reasoning pipeline either way — `POST /webhook/github`
(signed webhook) and `POST /webhook/action` (this Action) both call the
identical `_handle_push` / `_handle_pull_request` processing in
`apps/api/src/api/v1/webhook.py`. The only difference is how the request
is authenticated and where it originates.

## Why this exists, not just "use GitHub Actions to call an API"

The differentiator isn't the Action itself — a GitHub Action that POSTs a
webhook payload somewhere is trivial. It's what SprintSync does with the
event once it arrives: real diff-aware AI reasoning, task matching against
your actual task list, confidence-gated suggestions, and (for supported
providers) task-board sync — the same pipeline the signed webhook path
uses. The Action is just a second, admin-permission-free door into that
pipeline.

## Setup

1. **Generate a token** for the repository you want to connect:

   ```
   POST /api/v1/repositories/{repo_id}/action-token
   Authorization: <your SprintSync session>
   ```

   Returns `{"action_token": "..."}`. This is shown once — save it now.
   Calling this endpoint again **rotates** the token, immediately
   invalidating the previous one (see `test_action_endpoint_rotated_token_no_longer_works`
   in `apps/api/tests/test_github_action_ingestion.py`).

2. **Add it as a GitHub Actions secret** on the repository you want to
   sync — Settings → Secrets and variables → Actions → New repository
   secret, name it `SPRINTSYNC_TOKEN`.

3. **Add a workflow** — copy [`docs/examples/sprintsync-sync.yml`](examples/sprintsync-sync.yml)
   to `.github/workflows/sprintsync-sync.yml` in that repository, and set
   `api_url` to your SprintSync deployment's base URL.

4. Push a commit or open a PR. Check the workflow run's logs — the action
   prints SprintSync's HTTP response and fails the job (with a GitHub
   Actions error annotation) if the token is missing, invalid, or revoked.

## What it sends

The action forwards the exact payload GitHub already put at
`GITHUB_EVENT_PATH` for the triggering event (the same shape `github.event`
exposes in any workflow) — it doesn't reconstruct or guess at the payload
shape. The request body is:

```json
{
  "event_name": "push",
  "delivery_id": "<run_id>-<run_attempt>",
  "payload": { "...": "the real GitHub event payload" }
}
```

`delivery_id` reuses the same generic `WebhookDelivery` idempotency table
the signed-webhook path uses — a retried/re-run workflow attempt with the
same `run_id`/`run_attempt` will not be double-processed.

## Security

- The bearer token is a per-repository credential, generated server-side
  (`secrets.token_urlsafe(32)`), stored on `Repository.action_token`
  (unique, indexed) — the same storage pattern already used for
  `Profile.github_access_token` elsewhere in this codebase.
- `/webhook/action` looks the repository up **by token**, not by the
  payload's `repository.full_name` — the payload's own claims about which
  repo it's from are never trusted for authorization, only the token is.
- Rotating or revoking (`DELETE /repositories/{id}/action-token`)
  immediately invalidates the old token — there is no grace period.
- The token is never logged. Structured log events for this path record
  `repo`, `event_type`, and `delivery_id` only (see `src/api/v1/webhook.py`).
- As with the signed-webhook path, all inbound activity text (commit
  messages, PR titles/bodies, diffs) is still treated as untrusted data by
  the AI reasoning layer — see `apps/api/src/services/ai_reasoning/prompt.py`'s
  security-boundary documentation. Nothing about using the Action changes
  that boundary.

## Known limitations (honestly documented, not fixed this session)

- No frontend UI exists yet to generate/rotate/revoke the token or copy
  the example workflow — this is API-only for now (curl or an HTTP
  client). Wiring this into the repository settings page is tracked in
  `docs/V2_IMPLEMENTATION_PLAN.md`.
- Not fired against a real, hosted GitHub Actions runner in this session —
  no live repository with this workflow installed was available. It *was*
  verified by running `action.yml`'s exact shell script locally (bash +
  `jq` + `curl`, with `GITHUB_EVENT_PATH`/`GITHUB_EVENT_NAME`/`GITHUB_RUN_ID`
  set the same way GitHub's runner sets them) against a real local
  instance of the API and a real database row: the happy path (200,
  commit processed), duplicate-delivery short-circuiting (`{"status":
  "duplicate", ...}`), and the invalid-token failure branch (401 → the
  script's `::error::` annotation + `exit 1`) all behaved as documented.
  What wasn't verified is GitHub's own hosted-runner environment
  specifically (its exact `jq`/`bash`/`curl` versions, its secret-masking
  in a real Actions log) — the endpoint itself is also covered by real
  integration tests against the live database
  (`apps/api/tests/test_github_action_ingestion.py`).
- Requires `jq`, present by default on GitHub-hosted runners
  (`ubuntu-latest`/`macos-latest`/`windows-latest`) but not guaranteed on
  self-hosted runners.
