from __future__ import annotations

import subprocess
from typing import Dict, Any

from .integrations.jira_client import JiraClient
from .integrations.github_client import GitHubClient
from .llm import generate_answer


def generate_code_for_jira_task(task_key: str, jira: JiraClient | None = None) -> str:
    """Generate code for a Jira task using the LLM.

    Fetches the Jira issue details and sends a prompt to the language model.
    Returns the generated code snippet as a string.
    """
    jira = jira or JiraClient()
    issue = jira.get_issue(task_key)
    fields = issue.get('fields', {})
    summary = fields.get('summary', '')
    description = fields.get('description', '')
    prompt = (
        f"Generate code for Jira task {task_key}: {summary}\n"
        f"Description: {description}\n"
        "Provide only the relevant code snippet."
    )
    return generate_answer(prompt)


def run_tests() -> str:
    """Run pytest and return combined stdout/stderr output."""
    proc = subprocess.run(['pytest', '-q'], capture_output=True, text=True)
    return proc.stdout + proc.stderr


def commit_changes(message: str) -> str:
    """Commit all current changes with the provided message.

    Returns the resulting commit hash.
    """
    subprocess.check_call(['git', 'add', '-A'])
    subprocess.check_call(['git', 'commit', '-m', message])
    commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
    return commit_hash


def open_pull_request(owner: str, repo: str, head: str, base: str, title: str, body: str,
                       token_env: str = 'GITHUB_TOKEN', dry_run: bool = True) -> Dict[str, Any]:
    """Create a pull request using ``GitHubClient``.

    Parameters mirror the GitHub API. ``dry_run`` skips network calls during
    development. Returns the API response or a dry-run placeholder.
    """
    gh = GitHubClient(token_env=token_env, dry_run=dry_run)
    return gh.create_pr(owner, repo, head, base, title, body)

