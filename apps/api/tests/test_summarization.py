"""Unit tests for V2 Phase 9 (AI summarization) — same LLM-mocked-at-the-
transport-boundary pattern as test_ai_reasoning.py.
"""
from types import SimpleNamespace

from src.services.ai_reasoning import summarization


def _fake_message(text: str, stop_reason: str = "end_turn"):
    return SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)])


class _FakeStreamManager:
    def __init__(self, final_message):
        self._final_message = final_message

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get_final_message(self):
        return self._final_message


class _FakeMessages:
    def __init__(self, final_message):
        self._final_message = final_message

    def stream(self, **kwargs):
        return _FakeStreamManager(self._final_message)


class _FakeAsyncAnthropic:
    def __init__(self, final_message):
        self.messages = _FakeMessages(final_message)


def _patch_anthropic(monkeypatch, final_message):
    monkeypatch.setattr("anthropic.AsyncAnthropic", lambda *a, **k: _FakeAsyncAnthropic(final_message))


async def test_summarize_commit_falls_back_to_heuristic_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = await summarization.summarize_commit(
        message="Fix webhook signature bypass\n\nMore detail here",
        files_changed=[{"filename": "src/services/github.py"}],
    )
    assert result["source"] == "heuristic"
    assert "Fix webhook signature bypass" in result["summary"]
    assert "1 file" in result["summary"]


async def test_summarize_commit_uses_llm_when_available(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    _patch_anthropic(monkeypatch, _fake_message("Hardens webhook signature verification to fail closed."))
    result = await summarization.summarize_commit(message="fix bug", files_changed=[])
    assert result["source"] == "llm"
    assert result["summary"] == "Hardens webhook signature verification to fail closed."


async def test_summarize_commit_falls_back_on_llm_refusal(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    _patch_anthropic(monkeypatch, _fake_message("", stop_reason="refusal"))
    result = await summarization.summarize_commit(message="some real commit message", files_changed=[])
    assert result["source"] == "heuristic"
    assert "some real commit message" in result["summary"]


async def test_summarize_commit_falls_back_on_empty_llm_output(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    _patch_anthropic(monkeypatch, _fake_message("   "))
    result = await summarization.summarize_commit(message="another commit", files_changed=[])
    assert result["source"] == "heuristic"


async def test_summarize_pull_request_heuristic_no_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = await summarization.summarize_pull_request(
        title="Add Notion integration", body="Implements the provider", files_changed=[{"filename": "a.py"}, {"filename": "b.py"}]
    )
    assert result["source"] == "heuristic"
    assert "Add Notion integration" in result["summary"]
    assert "2 files" in result["summary"]


async def test_summarize_digest_no_activity():
    result = summarization.summarize_digest(
        repo_name="sprintsync",
        period_label="today",
        commit_count=0,
        pr_opened_count=0,
        pr_merged_count=0,
        tasks_done_count=0,
        tasks_in_progress_count=0,
    )
    assert result["source"] == "heuristic"
    assert "no development activity" in result["summary"]


async def test_summarize_digest_with_activity():
    result = summarization.summarize_digest(
        repo_name="sprintsync",
        period_label="this week",
        commit_count=5,
        pr_opened_count=2,
        pr_merged_count=1,
        tasks_done_count=3,
        tasks_in_progress_count=2,
    )
    assert result["source"] == "heuristic"
    assert "5 commits" in result["summary"]
    assert "2 PRs opened" in result["summary"]
    assert "1 merged" in result["summary"]
    assert "3 tasks completed" in result["summary"]
    assert "2 in progress" in result["summary"]
