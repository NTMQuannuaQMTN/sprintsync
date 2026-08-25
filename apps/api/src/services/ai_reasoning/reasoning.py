"""Structured AI reasoning — the real V2 replacement for ai.py's blind
keyword-only analyze_commit. Two paths, same output shape:

  - LLM path: real Claude API call (Anthropic SDK), given the actual diff/
    activity text (not just the commit message), structured output
    validated via ActivityAnalysis before use. Requires ANTHROPIC_API_KEY.
  - Heuristic path: the same keyword/filename-overlap scoring V1 shipped
    with (src/services/task_matching.py), used automatically when no API
    key is configured, or if the LLM call fails for any reason.

Callers never need to know which path ran — every result is
{task_id, proposed_status, confidence, confidence_tier, explanation,
evidence} with an evidence.source of "llm" or "heuristic". This is what
makes the fallback genuinely transparent rather than a silent downgrade:
inspect evidence.source (surfaced in the Suggestion UI) to see which one
actually produced any given suggestion.
"""
import json
import os
from typing import List, Optional

import structlog

from src.models.task import TaskStatus
from src.services import task_matching
from src.services.ai_reasoning.prompt import build_diff_excerpt, build_prompt
from src.services.ai_reasoning.schema import ActivityAnalysis, ConfidenceTier, confidence_tier
from src.services.status_mapping import resolve_status

logger = structlog.get_logger(__name__)

ANTHROPIC_MODEL = "claude-opus-5"
# Below this, a match is too weak to even surface as a suggestion — this is
# distinct from the HIGH/MEDIUM/LOW tier boundaries in schema.py, which
# govern presentation/trust, not whether a Suggestion row gets created at all.
LOW_CONFIDENCE_FLOOR = 0.3
_VALID_STATUSES = {s.value for s in TaskStatus}


async def analyze_activity(
    activity_type: str,
    text_signals: List[str],
    tasks: List[dict],
    event_key: str,
    changed_files: Optional[List[str]] = None,
    files_with_patches: Optional[List[dict]] = None,
    repo_status_mapping: Optional[dict] = None,
) -> List[dict]:
    """activity_type: "commit" | "pull_request". text_signals: e.g. a
    commit's [message], or a PR's [title, body, branch_name]. event_key:
    e.g. "push" | "pr_opened" | "pr_merged" — resolved to a proposed status
    via status_mapping.resolve_status when the model doesn't (or can't)
    confidently propose its own. files_with_patches: the same
    {filename, status, additions, deletions, patch} shape stored on
    Commit/PullRequest.files_changed — this is what actually lets the LLM
    path judge a completion claim against the real diff instead of trusting
    the message/title alone; the heuristic path doesn't use patch content
    (it never did), only changed_files (filenames)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            analysis = await _analyze_with_llm(
                api_key, activity_type, text_signals, tasks, changed_files, files_with_patches
            )
            return _finalize_llm(analysis, event_key, repo_status_mapping)
        except Exception as e:
            logger.warning(
                "ai_reasoning.llm_call_failed_falling_back_to_heuristic",
                error=str(e),
                activity_type=activity_type,
            )
    return _analyze_with_heuristic(text_signals, tasks, event_key, changed_files, repo_status_mapping)


async def _analyze_with_llm(
    api_key: str,
    activity_type: str,
    text_signals: List[str],
    tasks: List[dict],
    changed_files: Optional[List[str]],
    files_with_patches: Optional[List[dict]],
) -> ActivityAnalysis:
    from anthropic import AsyncAnthropic  # lazy import — optional dependency, only needed on this path

    if not tasks:
        raise ValueError("No open tasks to analyze against")

    activity_text = "\n\n---\n\n".join(s for s in text_signals if s) or "(no text content)"
    diff_excerpt = build_diff_excerpt(files_with_patches) if files_with_patches else None
    system, user = build_prompt(activity_type, activity_text, tasks, changed_files, diff_excerpt)

    client = AsyncAnthropic(api_key=api_key)
    async with client.messages.stream(
        model=ANTHROPIC_MODEL,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}],
        thinking={"type": "adaptive"},
    ) as stream:
        message = await stream.get_final_message()

    if message.stop_reason == "refusal":
        raise ValueError("Model declined to analyze this activity (safety refusal)")

    raw = "".join(b.text for b in message.content if b.type == "text").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return ActivityAnalysis.model_validate(json.loads(raw))


def _finalize_llm(analysis: ActivityAnalysis, event_key: str, repo_status_mapping: Optional[dict]) -> List[dict]:
    default_status = resolve_status(event_key, repo_status_mapping)
    out = []
    for assessment in analysis.task_assessments:
        tier = confidence_tier(assessment.confidence)
        if tier == ConfidenceTier.LOW and assessment.confidence < LOW_CONFIDENCE_FLOOR:
            continue
        proposed_status = (
            assessment.proposed_status if assessment.proposed_status in _VALID_STATUSES else default_status
        )
        out.append({
            "task_id": assessment.task_id,
            "proposed_status": proposed_status,
            "confidence": assessment.confidence,
            "confidence_tier": tier.value,
            "explanation": assessment.reasoning,
            "evidence": {
                "work_type": analysis.work_type.value,
                "summary": analysis.summary,
                "source": "llm",
            },
        })
    out.sort(key=lambda x: x["confidence"], reverse=True)
    return out[:5]


def _analyze_with_heuristic(
    text_signals: List[str],
    tasks: List[dict],
    event_key: str,
    changed_files: Optional[List[str]],
    repo_status_mapping: Optional[dict],
) -> List[dict]:
    matches = task_matching.score_tasks(text_signals, tasks, changed_files)
    default_status = resolve_status(event_key, repo_status_mapping)
    out = []
    for m in matches:
        tier = confidence_tier(m.confidence)
        if tier == ConfidenceTier.LOW and m.confidence < LOW_CONFIDENCE_FLOOR:
            continue
        out.append({
            "task_id": m.task_id,
            "proposed_status": default_status,
            "confidence": m.confidence,
            "confidence_tier": tier.value,
            "explanation": "; ".join(m.reasons) or "Keyword/file overlap with task",
            "evidence": {
                "matched_keywords": m.matched_keywords,
                "matched_files": m.matched_files,
                "explicit_reference": m.explicit_reference,
                "source": "heuristic",
            },
        })
        if len(out) >= 5:
            break
    return out
