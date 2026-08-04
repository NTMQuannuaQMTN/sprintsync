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
        # The spec row is cleaned up automatically (test_repo's DB delete
        # cascades to project_specifications), but the uploaded object in
        # Supabase Storage is not tied to Postgres FKs — remove it
        # explicitly so test runs don't accumulate junk in the real bucket.
        # storage_path is "{repo_id}/{uuid}/{filename}" (specs.py), so list
        # one level under the repo_id "directory" to find it.
        from supabase import create_client

        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        bucket = supabase.storage.from_(settings.SUPABASE_BUCKET)
        for subdir in bucket.list(str(test_repo)):
            for f in bucket.list(f"{test_repo}/{subdir['name']}"):
                bucket.remove([f"{test_repo}/{subdir['name']}/{f['name']}"])
