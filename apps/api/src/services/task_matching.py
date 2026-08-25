"""Task matching — scores which existing task(s) a piece of GitHub activity
(a commit, or a PR's title/body/branch) most likely relates to.

Generalizes what used to be inlined in ai.py's analyze_commit: that version
only ever looked at one signal (the commit message) plus filenames. This
version takes a list of independent text signals (a PR contributes several:
title, body, branch name; a commit contributes one: its message) and an
explicit-reference check, so the same scoring logic serves both events
instead of being duplicated per event type.

Explicit references: a developer can type the first 8 hex characters of a
task's id (e.g. "fixes #a1b2c3d4") in a commit message, PR title, or PR body
for a near-certain match — this is V2's real, working implementation of
"support explicit references when available." A full GitHub-issue-style
sequential per-repo task number (so this reads more like "#42") is a natural
follow-up but requires its own migration + UI surface; deferred, documented
in docs/V2_IMPLEMENTATION_PLAN.md rather than silently left out.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional

_REF_PATTERN = re.compile(r"#([0-9a-f]{8})\b", re.IGNORECASE)
_WORD_PATTERN = re.compile(r"\b\w{4,}\b")


@dataclass
class TaskMatch:
    task_id: str
    confidence: float  # 0.0 - 1.0
    reasons: List[str] = field(default_factory=list)
    matched_keywords: List[str] = field(default_factory=list)
    matched_files: List[str] = field(default_factory=list)
    explicit_reference: bool = False


def _short_id(task_id: str) -> str:
    return task_id.replace("-", "")[:8].lower()


def find_explicit_reference(text_signals: List[str], tasks: List[dict]) -> Optional[TaskMatch]:
    """Checks every text signal for a `#<8-hex-chars-of-task-id>` reference.
    Returns immediately on the first match — an explicit reference is
    authoritative, not just one more scored signal."""
    combined = " ".join(s for s in text_signals if s)
    refs = {m.group(1).lower() for m in _REF_PATTERN.finditer(combined)}
    if not refs:
        return None
    for task in tasks:
        if _short_id(str(task["id"])) in refs:
            return TaskMatch(
                task_id=task["id"],
                confidence=0.98,
                reasons=[f"Explicit reference #{_short_id(str(task['id']))} found in activity text"],
                explicit_reference=True,
            )
    return None


def score_tasks(
    text_signals: List[str],
    tasks: List[dict],
    changed_files: Optional[List[str]] = None,
) -> List[TaskMatch]:
    """Scores every open task against the combined text signals + changed
    files. An explicit reference short-circuits to a single high-confidence
    match; otherwise every task gets keyword/filename-overlap scoring, same
    heuristic V1 shipped with, just generalized to multiple text signals."""
    explicit = find_explicit_reference(text_signals, tasks)
    if explicit:
        return [explicit]

    combined_text = " ".join(s.lower() for s in text_signals if s)
    combined_words = set(_WORD_PATTERN.findall(combined_text))
    files = changed_files or []

    matches: List[TaskMatch] = []
    for task in tasks:
        if task.get("status") in ("done", "cancelled"):
            continue

        task_words = set(_WORD_PATTERN.findall(task["title"].lower()))
        overlap = task_words & combined_words
        if not overlap and not files:
            continue

        confidence = 0.0
        reasons: List[str] = []
        if overlap:
            confidence += min(0.4, len(overlap) * 0.1)
            reasons.append(f"Keyword overlap: {', '.join(sorted(overlap)[:3])}")

        file_hints = [f for f in files if any(w in f.lower() for w in list(task_words)[:5])]
        if file_hints:
            confidence += 0.3
            reasons.append(f"Changed files match task: {', '.join(file_hints[:3])}")

        if confidence <= 0:
            continue

        matches.append(TaskMatch(
            task_id=task["id"],
            confidence=round(min(confidence, 0.95), 2),
            reasons=reasons,
            matched_keywords=sorted(overlap)[:5],
            matched_files=file_hints[:5],
        ))

    matches.sort(key=lambda m: m.confidence, reverse=True)
    return matches
