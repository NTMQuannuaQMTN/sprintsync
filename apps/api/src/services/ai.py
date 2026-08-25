"""AI service — task extraction from spec documents (spec upload feature).

Uses a simple heuristic/pattern-based approach. Commit/PR activity analysis
now lives in src/services/ai_reasoning/ (structured LLM output with a
heuristic fallback via task_matching.py) — this module no longer handles it.
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

ai_service = AIService()
