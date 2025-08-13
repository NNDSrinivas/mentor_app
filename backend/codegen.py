from __future__ import annotations
"""Simple code generation utilities for review comment automation."""
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Any, Optional, List

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from app.task_manager import Task


def extract_patch_from_comment(body: str) -> Optional[str]:
    """Extract a unified diff patch from a comment body if present."""
    in_patch = False
    patch_lines: List[str] = []
    for line in body.splitlines():
        if line.strip().startswith("```patch") or line.strip().startswith("```diff"):
            in_patch = True
            continue
        if line.strip().startswith("```") and in_patch:
            break
        if in_patch:
            patch_lines.append(line)
    return "\n".join(patch_lines) if patch_lines else None


def generate_patch(comment: Dict[str, Any]) -> Optional[str]:
    """Generate a patch for an actionable review comment.

    This stub tries to read a patch directly embedded in the comment. In a real
    deployment this would call an external code generation service.
    """
    body = comment.get("body", "")
    patch = extract_patch_from_comment(body)
    if patch:
        return patch
    # Placeholder for AI-based generation
    return None


def generate_code_and_tests(task: "Task", source_dir: str, tests_dir: str) -> Dict[str, str]:
    """Generate a source file and companion unit test from a task description.

    The generated module is named ``task_<task_id>.py`` and contains a single
    ``main`` function stub.  A matching test file ``test_task_<task_id>.py`` is
    placed in ``tests_dir`` with a placeholder assertion.  Both files include the
    task title and description in their docstrings so developers can flesh them
    out later.

    Args:
        task: ``Task`` instance describing the work to be implemented.
        source_dir: Directory where the source module will be written.
        tests_dir: Directory where the test module will be written.

    Returns:
        Dict with ``source`` and ``test`` keys mapping to the created file paths.
    """

    src_path = Path(source_dir) / f"task_{task.task_id}.py"
    test_path = Path(tests_dir) / f"test_task_{task.task_id}.py"

    src_content = (
        f'"""Auto-generated stub for task: {task.title}\n\n{task.description}\n"""\n\n'
        "def main() -> None:\n"
        f"    \"\"\"Entry point for task {task.task_id}.\"\"\"\n"
        "    pass\n"
    )

    test_content = (
        f'"""Tests for task {task.task_id}: {task.title}"""\n\n'
        "def test_placeholder() -> None:\n"
        "    assert True\n"
    )

    src_path.write_text(src_content)
    test_path.write_text(test_content)

    return {"source": str(src_path), "test": str(test_path)}


def generate_from_tasks(tasks: List["Task"], source_dir: str, tests_dir: str) -> List[Dict[str, str]]:
    """Generate code and tests for a list of tasks.

    Args:
        tasks: List of ``Task`` objects.
        source_dir: Directory for source modules.
        tests_dir: Directory for test modules.

    Returns:
        List of dictionaries describing the created files for each task.
    """

    results = []
    for task in tasks:
        results.append(generate_code_and_tests(task, source_dir, tests_dir))
    return results
