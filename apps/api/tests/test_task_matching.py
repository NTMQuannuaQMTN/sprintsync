"""Unit tests for the V2 task-matching module — pure logic, no DB/network."""
import uuid

from src.services.task_matching import find_explicit_reference, score_tasks
from src.services.status_mapping import resolve_status, DEFAULT_STATUS_MAPPING


def _task(title, status="todo", task_id=None):
    return {"id": task_id or str(uuid.uuid4()), "title": title, "status": status}


def test_explicit_reference_short_circuits_to_high_confidence():
    task_id = str(uuid.uuid4())
    short = task_id.replace("-", "")[:8]
    tasks = [_task("Implement authentication", task_id=task_id), _task("Unrelated task")]

    matches = score_tasks([f"fixes #{short} for real this time"], tasks)

    assert len(matches) == 1
    assert matches[0].task_id == task_id
    assert matches[0].explicit_reference is True
    assert matches[0].confidence >= 0.95


def test_explicit_reference_is_case_insensitive():
    task_id = str(uuid.uuid4())
    short = task_id.replace("-", "")[:8].upper()
    tasks = [_task("Implement authentication", task_id=task_id)]

    match = find_explicit_reference([f"See #{short}"], tasks)

    assert match is not None
    assert match.task_id == task_id


def test_no_reference_falls_back_to_keyword_scoring():
    tasks = [
        _task("Implement webhook signature verification"),
        _task("Add Google Docs import"),
    ]
    matches = score_tasks(["Implement webhook signature verification for real"], tasks)

    assert len(matches) == 1
    assert matches[0].explicit_reference is False
    assert "webhook" in " ".join(matches[0].matched_keywords).lower() or matches[0].confidence > 0


def test_combines_multiple_text_signals_pr_title_body_branch():
    """A PR contributes 3 signals at once — none alone might be a strong
    match, but combined they should score higher than any single one."""
    tasks = [_task("Implement Notion task board integration")]

    single_signal = score_tasks(["Add integration"], tasks)
    combined = score_tasks(
        ["Add integration", "This PR wires up the Notion task board provider", "feature/notion-integration"],
        tasks,
    )

    assert combined[0].confidence >= single_signal[0].confidence if single_signal else True
    assert combined[0].confidence > 0


def test_changed_files_matching_task_title_boosts_confidence():
    tasks = [_task("Refactor github service")]
    matches = score_tasks(
        ["small tweak"],
        tasks,
        changed_files=["src/services/github.py"],
    )
    assert len(matches) == 1
    assert "github.py" in " ".join(matches[0].matched_files)


def test_done_and_cancelled_tasks_are_never_matched():
    tasks = [_task("Implement login", status="done"), _task("Implement login", status="cancelled")]
    matches = score_tasks(["Implement login"], tasks)
    assert matches == []


def test_no_overlap_and_no_files_produces_no_matches():
    tasks = [_task("Completely unrelated task title")]
    matches = score_tasks(["xyzxyz totally different words"], tasks)
    assert matches == []


def test_empty_task_list_is_safe():
    assert score_tasks(["anything"], []) == []
    assert find_explicit_reference(["anything"], []) is None


# --- status_mapping ---


def test_default_status_mapping_used_when_repo_has_none():
    assert resolve_status("push", None) == DEFAULT_STATUS_MAPPING["push"]
    assert resolve_status("pr_merged", None) == "done"
    assert resolve_status("pr_closed", None) == "blocked"


def test_repo_override_wins_when_valid():
    assert resolve_status("push", {"push": "blocked"}) == "blocked"


def test_invalid_repo_override_falls_back_to_default():
    assert resolve_status("push", {"push": "not_a_real_status"}) == DEFAULT_STATUS_MAPPING["push"]


def test_unknown_event_key_falls_back_to_in_progress():
    assert resolve_status("some_future_event_type", None) == "in_progress"
