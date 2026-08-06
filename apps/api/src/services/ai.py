"""AI service — task extraction from documents and commit analysis.

Uses a simple heuristic/pattern-based approach as a placeholder.
Replace with actual LLM (Tencent WorkBuddy / OpenAI) calls.
"""
import re
from typing import List

from src.schemas.task import TaskCreate
from src.models.task import TaskPriority, TaskStatus


class AIService:
    """Pluggable AI service — swap implementation without changing callers."""

    async def extract_tasks_from_text(self, text: str, repo_name: str) -> List[TaskCreate]:
        """
        Extract implementation tasks from project specification text.
        Returns a flat list of TaskCreate objects (parent_id links subtasks).
        """
        tasks: List[TaskCreate] = []

        # Heuristic patterns for common spec document structures
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        task_patterns = [
            r"^(\d+\.|\-|\*|\•)\s*(.+)$",  # numbered or bulleted (space after marker optional, e.g. "*BONUS:")
            r"^(=>)\s*(.+)$",  # arrow-prefixed action lines ("=> Tính năng import ...")
            r"^(Implement|Build|Create|Add|Integrate|Setup|Configure|Design|Develop|Fix|Refactor)\s+(.+)$",
            # Common Vietnamese task/action verbs (feedback docs are often written in Vietnamese,
            # imperative, with no consistent bullet/heading structure).
            r"^(Thêm|Đổi|Cần|Tạo|Sửa|Nâng cấp|Cải thiện|Chỉnh|Xóa|Bỏ|Up|Des)\s+(.+)$",
            r"^(Feature|Task|Story|Epic|Requirement):\s*(.+)$",
            r"^##?\s+(.+)$",  # Markdown headings as tasks
        ]

        seen = set()
        # A line that is just "=>" on its own (no trailing content) means the
        # actual instruction is the *next* line — promote it even if it
        # doesn't match any pattern above.
        promote_next = False
        for line in lines:
            if line == "=>":
                promote_next = True
                continue

            if len(line) < 10 or len(line) > 300:
                promote_next = False
                continue

            if promote_next:
                title = line.strip()
                if title and title not in seen and len(title) > 5:
                    seen.add(title)
                    tasks.append(TaskCreate(
                        title=title,
                        description=None,
                        status=TaskStatus.TODO,
                        priority=self._infer_priority(title),
                        ai_tags=self._extract_tags(title),
                    ))
                promote_next = False
                continue

            for pattern in task_patterns:
                m = re.match(pattern, line, re.IGNORECASE)
                if m:
                    title = m.group(len(m.groups())).strip()
                    title = re.sub(r"^[#\-\*\•\d\.]+\s*", "", title).strip()
                    if title and title not in seen and len(title) > 5:
                        seen.add(title)
                        priority = self._infer_priority(title)
                        tasks.append(TaskCreate(
                            title=title,
                            description=None,
                            status=TaskStatus.TODO,
                            priority=priority,
                            ai_tags=self._extract_tags(title),
                        ))
                    break

        if not tasks:
            # Fallback: create a default task
            tasks = [
                TaskCreate(
                    title=f"Review and implement {repo_name} specification",
                    description="AI could not extract specific tasks. Please review the document and add tasks manually.",
                    status=TaskStatus.TODO,
                    priority=TaskPriority.HIGH,
                )
            ]

        return tasks[:50]  # cap at 50 tasks per spec

    async def analyze_commit(
        self,
        commit_message: str,
        files_changed: List[dict],
        tasks: List[dict],
    ) -> List[dict]:
        """
        Analyze a commit and return suggested task updates.

        Returns list of dicts: {task_id, proposed_status, confidence, explanation, evidence}
        """
        suggestions = []

        if not tasks:
            return suggestions

        commit_lower = commit_message.lower()
        files = [f.get("filename", "") for f in (files_changed or [])]

        # Heuristic: look for completion indicators
        completion_keywords = [
            "implement", "add", "complete", "finish", "done", "fix",
            "resolve", "close", "merge", "integrate", "setup", "create",
        ]
        is_completion = any(k in commit_lower for k in completion_keywords)

        for task in tasks:
            if task.get("status") in ("done", "cancelled"):
                continue

            task_lower = task["title"].lower()
            confidence = 0.0
            matched_reasons = []

            # Title word overlap
            task_words = set(re.findall(r"\b\w{4,}\b", task_lower))
            commit_words = set(re.findall(r"\b\w{4,}\b", commit_lower))
            overlap = task_words & commit_words
            if overlap:
                confidence += min(0.4, len(overlap) * 0.1)
                matched_reasons.append(f"Keywords match: {', '.join(list(overlap)[:3])}")

            # File name hints
            file_hints = [f for f in files if any(w in f for w in list(task_words)[:5])]
            if file_hints:
                confidence += 0.3
                matched_reasons.append(f"Files changed: {', '.join(file_hints[:3])}")

            # Completion signal
            if is_completion and confidence > 0:
                confidence += 0.2

            if confidence >= 0.5:
                proposed = "done" if is_completion else "in_progress"
                suggestions.append({
                    "task_id": task["id"],
                    "proposed_status": proposed,
                    "confidence": round(min(confidence, 0.95), 2),
                    "explanation": self._build_explanation(commit_message, matched_reasons, proposed),
                    "evidence": {
                        "commit_message": commit_message,
                        "matching_files": file_hints[:5],
                        "matching_keywords": list(overlap)[:5],
                        "reasoning": matched_reasons,
                    },
                })

        # Sort by confidence
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        return suggestions[:5]  # top 5 per commit

    def _infer_priority(self, title: str) -> TaskPriority:
        t = title.lower()
        if any(k in t for k in ["critical", "urgent", "security", "auth", "login", "payment", "crash"]):
            return TaskPriority.CRITICAL
        if any(k in t for k in ["important", "core", "main", "api", "database", "deploy"]):
            return TaskPriority.HIGH
        if any(k in t for k in ["optional", "nice", "later", "future", "cleanup", "refactor"]):
            return TaskPriority.LOW
        return TaskPriority.MEDIUM

    def _extract_tags(self, title: str) -> List[str]:
        t = title.lower()
        tags = []
        tag_map = {
            "api": ["api", "endpoint", "route"],
            "ui": ["ui", "component", "page", "frontend", "design"],
            "database": ["database", "db", "schema", "model", "migration"],
            "auth": ["auth", "login", "oauth", "jwt", "session"],
            "testing": ["test", "spec", "e2e", "unit"],
            "infra": ["deploy", "ci", "cd", "docker", "k8s", "infra"],
        }
        for tag, keywords in tag_map.items():
            if any(k in t for k in keywords):
                tags.append(tag)
        return tags

    def _build_explanation(self, commit_msg: str, reasons: List[str], proposed: str) -> str:
        action = "completed" if proposed == "done" else "started working on"
        reasons_str = "; ".join(reasons) if reasons else "keyword and file analysis"
        return (
            f"Based on commit '{commit_msg[:60]}...', the developer appears to have {action} this task. "
            f"Evidence: {reasons_str}."
        )


ai_service = AIService()
