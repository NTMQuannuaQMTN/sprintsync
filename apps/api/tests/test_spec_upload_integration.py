"""Integration test for the spec upload -> Supabase Storage -> AI draft-task
flow against the real database and the real Supabase Storage bucket
(sprintsync-specs, created this pass — see CHECKLIST.md TASK 7).
"""
import io

from docx import Document

from src.core.config import settings


def _docx_bytes(paragraphs: list[str]) -> bytes:
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _cleanup_storage(repo_id) -> None:
    """Removes anything this test session uploaded under {repo_id}/ in the
    real Supabase Storage bucket — those objects aren't tied to Postgres
    FKs, so a DB-row cleanup alone would leave them behind."""
    from supabase import create_client

    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    bucket = supabase.storage.from_(settings.SUPABASE_BUCKET)
    for subdir in bucket.list(str(repo_id)):
        for f in bucket.list(f"{repo_id}/{subdir['name']}"):
            bucket.remove([f"{repo_id}/{subdir['name']}/{f['name']}"])


async def test_upload_spec_stores_file_and_returns_draft_tasks(client, test_repo):
    file_bytes = _docx_bytes([
        "- Implement GitHub OAuth login",
        "- Add webhook signature verification",
    ])
    files = {
        "file": (
            "spec.docx",
            file_bytes,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    resp = await client.post(f"/api/v1/repositories/{test_repo}/specs", files=files)
    assert resp.status_code == 201, resp.text
    spec = resp.json()
    try:
        assert spec["status"] == "done"
        assert spec["error_message"] is None
        # Real Supabase Storage upload — was skipped entirely (no storage_url)
        # before the sprintsync-specs bucket existed; now it should populate.
        assert spec["storage_url"], "expected a real signed Supabase Storage URL"

        titles = [t["title"] for t in spec["draft_tasks"]]
        assert any("GitHub OAuth login" in t for t in titles)
        assert any("webhook signature verification" in t for t in titles)
        # Nothing persisted as a real Task yet — that's the whole point of
        # SPEC-004's review-before-save flow.
        assert spec["task_count"] == 0

        tasks_listed = await client.get(f"/api/v1/repositories/{test_repo}/tasks")
        assert tasks_listed.json() == []
    finally:
        _cleanup_storage(test_repo)


async def test_save_reviewed_draft_tasks_persists_them_with_spec_link(client, test_repo):
    """Exercises exactly what the frontend's upload page "Save N tasks"
    button does: upload -> get draft_tasks + spec.id -> POST /tasks/bulk
    with spec_id set. This is the one leg of the upload flow that wasn't
    covered yet — the upload-only test above stops before this step."""
    file_bytes = _docx_bytes(["- Implement GitHub OAuth login", "- Add webhook signature verification"])
    files = {
        "file": (
            "spec.docx",
            file_bytes,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    try:
        upload = await client.post(f"/api/v1/repositories/{test_repo}/specs", files=files)
        spec = upload.json()
        draft_tasks = spec["draft_tasks"]
        assert len(draft_tasks) >= 2

        # Mirrors AddTaskForm/upload page: drop the frontend-only `selected`
        # flag, keep everything else, and only save what was "checked".
        save = await client.post(
            f"/api/v1/repositories/{test_repo}/tasks/bulk",
            json={"tasks": draft_tasks, "spec_id": spec["id"]},
        )
        assert save.status_code == 201, save.text
        saved = save.json()
        assert len(saved) == len(draft_tasks)
        assert all(t["spec_id"] == spec["id"] for t in saved)

        # The spec's task_count should now reflect the confirmed save, not
        # still be 0 from the upload-only response.
        spec_after = await client.get(f"/api/v1/repositories/{test_repo}/specs/{spec['id']}/tasks")
        assert len(spec_after.json()) == len(draft_tasks)

        tasks_listed = await client.get(f"/api/v1/repositories/{test_repo}/tasks")
        listed_titles = {t["title"] for t in tasks_listed.json()}
        assert listed_titles == {t["title"] for t in draft_tasks}
    finally:
        _cleanup_storage(test_repo)
