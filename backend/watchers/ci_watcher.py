# backend/watchers/ci_watcher.py
from __future__ import annotations
import logging
from typing import Dict, Any, List

log = logging.getLogger(__name__)

# Import approvals globally to avoid circular imports
def get_approvals():
    from backend.approvals import approvals
    return approvals

def handle_github_webhook(event: str, payload: Dict[str, Any]):
    """
    Handle GitHub webhook events and surface actionable items for approval.
    Focus on CI failures, PR events, and workflow runs.
    """
    log.info(f"Received GitHub webhook: {event}")
    
    if event == "check_suite":
        handle_check_suite(payload)
    elif event == "workflow_run":
        handle_workflow_run(payload)
    elif event == "pull_request":
        handle_pull_request(payload)
    elif event == "push":
        handle_push(payload)
    elif event == "issues":
        handle_issues(payload)
    else:
        log.debug(f"Unhandled webhook event: {event}")

def handle_check_suite(payload: Dict[str, Any]):
    """Handle check suite events (CI runs)"""
    action = payload.get("action")
    check_suite = payload.get("check_suite", {})
    conclusion = check_suite.get("conclusion")
    status = check_suite.get("status")
    repo = payload.get("repository", {}).get("full_name")
    branch = check_suite.get("head_branch")
    
    if action == "completed" and conclusion == "failure":
        # CI failure detected - suggest fixes
        pull_requests = check_suite.get("pull_requests", [])
        pr_info = pull_requests[0] if pull_requests else None
        
        failure_context = {
            "repo": repo,
            "branch": branch,
            "check_suite_id": check_suite.get("id"),
            "pr_number": pr_info.get("number") if pr_info else None,
            "pr_title": pr_info.get("title") if pr_info else None,
            "head_sha": check_suite.get("head_sha"),
            "message": f"Check suite failed on {repo}@{branch}",
            "hints": extract_check_suite_hints(check_suite),
            "severity": "high" if pr_info else "medium"
        }
        
        get_approvals().submit("ci.fix_suggestions", failure_context)
        log.warning(f"CI failure queued for approval: {repo}@{branch}")

def handle_workflow_run(payload: Dict[str, Any]):
    """Handle workflow run events"""
    action = payload.get("action")
    workflow_run = payload.get("workflow_run", {})
    conclusion = workflow_run.get("conclusion")
    repo = payload.get("repository", {}).get("full_name")
    branch = workflow_run.get("head_branch")
    
    if action == "completed" and conclusion == "failure":
        failure_context = {
            "repo": repo,
            "branch": branch,
            "workflow_id": workflow_run.get("id"),
            "workflow_name": workflow_run.get("name"),
            "run_number": workflow_run.get("run_number"),
            "head_sha": workflow_run.get("head_sha"),
            "message": f"Workflow '{workflow_run.get('name')}' failed on {repo}@{branch}",
            "hints": extract_workflow_hints(workflow_run),
            "logs_url": workflow_run.get("logs_url"),
            "severity": "high"
        }
        
        get_approvals().submit("ci.workflow_failure", failure_context)
        log.warning(f"Workflow failure queued for approval: {workflow_run.get('name')} on {repo}")

def handle_pull_request(payload: Dict[str, Any]):
    """Handle pull request events"""
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {}).get("full_name")
    
    if action == "opened":
        # New PR opened - suggest review checklist or automated checks
        pr_context = {
            "repo": repo,
            "pr_number": pr.get("number"),
            "title": pr.get("title"),
            "author": pr.get("user", {}).get("login"),
            "base_branch": pr.get("base", {}).get("ref"),
            "head_branch": pr.get("head", {}).get("ref"),
            "draft": pr.get("draft"),
            "message": f"New PR #{pr.get('number')}: {pr.get('title')}",
            "suggestions": generate_pr_suggestions(pr),
            "severity": "low"
        }
        
        # Only queue if it's not a draft and meets certain criteria
        if not pr.get("draft") and should_suggest_pr_actions(pr):
            get_approvals().submit("pr.review_suggestions", pr_context)
            log.info(f"PR review suggestions queued: #{pr.get('number')} on {repo}")
    
    elif action == "review_requested":
        # Review requested - surface to reviewer
        review_context = {
            "repo": repo,
            "pr_number": pr.get("number"),
            "title": pr.get("title"),
            "requested_reviewer": payload.get("requested_reviewer", {}).get("login"),
            "message": f"Review requested for PR #{pr.get('number')}: {pr.get('title')}",
            "severity": "medium"
        }
        
        get_approvals().submit("pr.review_requested", review_context)

def handle_push(payload: Dict[str, Any]):
    """Handle push events to main/master branches"""
    ref = payload.get("ref", "")
    repo = payload.get("repository", {}).get("full_name")
    
    # Only care about pushes to main branches
    if ref in ("refs/heads/main", "refs/heads/master"):
        commits = payload.get("commits", [])
        if commits:
            push_context = {
                "repo": repo,
                "branch": ref.replace("refs/heads/", ""),
                "commit_count": len(commits),
                "head_commit": payload.get("head_commit", {}),
                "message": f"{len(commits)} commits pushed to {repo} main branch",
                "severity": "low"
            }
            
            # Check if this might need deployment or post-merge actions
            if should_suggest_deployment(commits):
                get_approvals().submit("deployment.suggest", push_context)

def handle_issues(payload: Dict[str, Any]):
    """Handle issue events"""
    action = payload.get("action")
    issue = payload.get("issue", {})
    repo = payload.get("repository", {}).get("full_name")
    
    if action == "opened":
        # New issue opened - suggest triage actions
        issue_context = {
            "repo": repo,
            "issue_number": issue.get("number"),
            "title": issue.get("title"),
            "author": issue.get("user", {}).get("login"),
            "labels": [label.get("name") for label in issue.get("labels", [])],
            "message": f"New issue #{issue.get('number')}: {issue.get('title')}",
            "suggestions": generate_issue_suggestions(issue),
            "severity": "low"
        }
        
        get_approvals().submit("issue.triage_suggestions", issue_context)

def extract_check_suite_hints(check_suite: Dict[str, Any]) -> List[str]:
    """Extract hints for fixing check suite failures"""
    hints = []
    
    # Basic hints based on common failure patterns
    conclusion = check_suite.get("conclusion")
    if conclusion == "failure":
        hints.extend([
            "Check test failures in the CI logs",
            "Verify all required checks are passing",
            "Look for linting or formatting issues",
            "Check for dependency conflicts"
        ])
    
    # Add more sophisticated analysis based on check suite details
    app = check_suite.get("app", {})
    if app.get("name") == "GitHub Actions":
        hints.append("Review GitHub Actions workflow configuration")
    
    return hints

def extract_workflow_hints(workflow_run: Dict[str, Any]) -> List[str]:
    """Extract hints for fixing workflow failures"""
    hints = []
    workflow_name = workflow_run.get("name", "").lower()
    
    if "test" in workflow_name:
        hints.extend([
            "Check unit test failures",
            "Review test coverage requirements",
            "Verify test environment setup"
        ])
    elif "build" in workflow_name:
        hints.extend([
            "Check build configuration",
            "Verify dependency installation",
            "Review compilation errors"
        ])
    elif "deploy" in workflow_name:
        hints.extend([
            "Check deployment credentials",
            "Verify environment configuration",
            "Review infrastructure requirements"
        ])
    else:
        hints.append("Check workflow logs for specific error messages")
    
    return hints

def generate_pr_suggestions(pr: Dict[str, Any]) -> List[str]:
    """Generate suggestions for PR review"""
    suggestions = []
    
    # Basic suggestions based on PR metadata
    if not pr.get("body"):
        suggestions.append("Add PR description explaining the changes")
    
    # Check title patterns
    title = pr.get("title", "").lower()
    if any(keyword in title for keyword in ["fix", "bug", "hotfix"]):
        suggestions.append("Consider adding regression tests for bug fixes")
    elif any(keyword in title for keyword in ["feat", "feature"]):
        suggestions.append("Ensure feature documentation is updated")
    
    # Check for large PRs
    additions = pr.get("additions", 0)
    deletions = pr.get("deletions", 0)
    if additions + deletions > 500:
        suggestions.append("Large PR detected - consider breaking into smaller changes")
    
    return suggestions

def generate_issue_suggestions(issue: Dict[str, Any]) -> List[str]:
    """Generate suggestions for issue triage"""
    suggestions = []
    
    title = issue.get("title", "").lower()
    body = issue.get("body", "").lower()
    
    if "bug" in title or "error" in title:
        suggestions.extend([
            "Add 'bug' label",
            "Request reproduction steps if missing",
            "Assign to appropriate team member"
        ])
    elif "feature" in title or "enhancement" in title:
        suggestions.extend([
            "Add 'enhancement' label",
            "Consider product review if needed",
            "Estimate effort and priority"
        ])
    
    if not issue.get("labels"):
        suggestions.append("Add appropriate labels for categorization")
    
    return suggestions

def should_suggest_pr_actions(pr: Dict[str, Any]) -> bool:
    """Determine if we should suggest actions for this PR"""
    # Skip bot PRs
    author = pr.get("user", {}).get("login", "")
    if "bot" in author.lower() or author.endswith("[bot]"):
        return False
    
    # Skip very small PRs (likely typo fixes)
    additions = pr.get("additions", 0)
    deletions = pr.get("deletions", 0)
    if additions + deletions < 10:
        return False
    
    return True

def should_suggest_deployment(commits: List[Dict[str, Any]]) -> bool:
    """Determine if commits suggest a deployment might be needed"""
    deployment_keywords = ["deploy", "release", "version", "migration", "config"]
    
    for commit in commits:
        message = commit.get("message", "").lower()
        if any(keyword in message for keyword in deployment_keywords):
            return True
    
    return False
