"""Structured AI output schema — validated before ever being used to build a
Suggestion. Nothing downstream trusts raw model text; everything goes
through ActivityAnalysis.model_validate_json() first, and a validation
failure falls back to the heuristic path rather than propagating a
malformed result (see reasoning.py).
"""
import enum
from typing import List, Optional

from pydantic import BaseModel, Field


class WorkType(str, enum.Enum):
    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    DOCS = "docs"
    TEST = "test"
    CHORE = "chore"
    OTHER = "other"


class ConfidenceTier(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def confidence_tier(score: float) -> ConfidenceTier:
    """HIGH: safe to auto-generate a suggestion the user will likely just
    approve. MEDIUM: still only ever a suggestion (never auto-applied —
    V1's human-approval gate is unchanged), but flagged as less certain.
    LOW: recorded and surfaced, explicitly not acted on further — this
    codebase already never auto-applies anything without human approval, so
    the tier's real effect (see reasoning.py) is on *whether a Suggestion is
    created at all* for a LOW match, not on bypassing approval."""
    if score >= 0.85:
        return ConfidenceTier.HIGH
    if score >= 0.5:
        return ConfidenceTier.MEDIUM
    return ConfidenceTier.LOW


class TaskAssessment(BaseModel):
    task_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    proposed_status: Optional[str] = None
    reasoning: str = Field(max_length=1000)


class ActivityAnalysis(BaseModel):
    """One LLM (or heuristic) analysis of a single commit or PR against a
    repo's current task list."""
    work_type: WorkType
    summary: str = Field(max_length=500)
    task_assessments: List[TaskAssessment] = Field(default_factory=list)
    unmatched: bool = False  # True: this activity doesn't clearly relate to any existing task
