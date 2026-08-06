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


async def test_extract_tasks_from_vietnamese_feedback_doc():
    """Real-world regression: a Vietnamese feedback PDF for an unrelated
    product used arrow lines, asterisk-headers with no space, and
    Vietnamese imperative verbs instead of English bullets — the original
    heuristic (English-only, bullet-space-required) produced zero matches
    on this document and silently fell back to a single generic task."""
    text = (
        "Nền màu đỏ đậm\n"
        "=>\n"
        "Đổi màu hợp với nền màu đỏ đậm; SAT: đỏ; Champions: đen\n"
        "=> Tính năng import từ class này qua class kia cho cả test, vocab\n"
        "*BONUS: tính năng copy class qua bên lớp mới\n"
        "Cần có tính năng tạo mục để quản lý cho dễ\n"
        "Up lại ảnh 2 bọn t với chỉnh writing style\n"
        "- thêm tính năng pin class (để ghim lớp chính lên cho dễ)\n"
    )
    tasks = await ai_service.extract_tasks_from_text(text, "sat-champions")
    titles = [t.title for t in tasks]

    # Line after a lone "=>" is promoted verbatim.
    assert any("Đổi màu hợp với nền màu đỏ đậm" in t for t in titles)
    # "=> " directly prefixing content on the same line.
    assert any("Tính năng import từ class này" in t for t in titles)
    # Asterisk header with no space after the marker.
    assert any("BONUS: tính năng copy class" in t for t in titles)
    # Vietnamese imperative verb at line start (no bullet at all).
    assert any(t.startswith("có tính năng tạo mục") for t in titles)
    assert any(t.startswith("lại ảnh 2 bọn t") for t in titles)
    # Pre-existing dash-bullet support still works alongside the new patterns.
    assert any("thêm tính năng pin class" in t for t in titles)


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
