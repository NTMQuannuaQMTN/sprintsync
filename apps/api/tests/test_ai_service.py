"""Unit tests for the heuristic AIService (src/services/ai.py).

No DB/network required. These exercise real extraction/analysis logic, not
mocks — per the checklist's SPEC-003/SUGG-001/SUGG-002 evidence requirement.
"""
from src.services.ai import ai_service


async def test_extract_tasks_from_bulleted_spec():
    text = (
        "# Project Requirements\n"
        "- Implement GitHub OAuth login\n"
        "- Build the dashboard overview page\n"
        "- Add webhook signature verification\n"
    )
    tasks = await ai_service.extract_tasks_from_text(text, "sprintsync")
    titles = [t.title for t in tasks]
    assert any("GitHub OAuth login" in t for t in titles)
    assert any("dashboard overview page" in t for t in titles)
    assert any("webhook signature verification" in t for t in titles)


async def test_extract_tasks_falls_back_when_nothing_matches():
    tasks = await ai_service.extract_tasks_from_text("no structured content here at all", "myrepo")
    assert len(tasks) == 1
    assert "myrepo" in tasks[0].title


async def test_extract_tasks_caps_at_fifty():
    text = "\n".join(f"- Implement feature number {i} for the system" for i in range(80))
    tasks = await ai_service.extract_tasks_from_text(text, "myrepo")
    assert len(tasks) <= 50


async def test_analyze_commit_flags_completion_keyword_as_done():
    tasks = [{"id": "t1", "title": "Implement webhook signature verification", "status": "todo"}]
    files = [{"filename": "src/services/github.py", "status": "modified"}]
    suggestions = await ai_service.analyze_commit(
        commit_message="Implement webhook signature verification",
        files_changed=files,
        tasks=tasks,
    )
    assert len(suggestions) == 1
    assert suggestions[0]["task_id"] == "t1"
    assert suggestions[0]["proposed_status"] == "done"
    assert suggestions[0]["confidence"] > 0
    assert "reasoning" in suggestions[0]["evidence"]


async def test_analyze_commit_skips_already_done_tasks():
    tasks = [{"id": "t1", "title": "Implement webhook signature verification", "status": "done"}]
    files = []
    suggestions = await ai_service.analyze_commit(
        commit_message="Implement webhook signature verification",
        files_changed=files,
        tasks=tasks,
    )
    assert suggestions == []


async def test_analyze_commit_returns_nothing_for_unrelated_commit():
    tasks = [{"id": "t1", "title": "Implement webhook signature verification", "status": "todo"}]
    suggestions = await ai_service.analyze_commit(
        commit_message="Update README typo",
        files_changed=[{"filename": "README.md", "status": "modified"}],
        tasks=tasks,
    )
    assert suggestions == []
