# backend/approval_worker.py
import time, threading, logging
from typing import Dict, Any, Optional

log = logging.getLogger(__name__)

# Import managers to avoid circular imports
def get_managers():
    from backend.integrations.github_manager import GitHubManager
    from backend.integrations.jira_manager import JiraManager
    from backend.approvals import approvals
    return GitHubManager(dry_run=True), JiraManager(dry_run=True), approvals

# Initialize managers (dry_run=True by default for safety)
github, jira, approvals = get_managers()

def run_worker(poll_interval: float = 1.0):
    """
    Background worker that polls for pending approvals.
    This is mainly for monitoring - actual execution happens on resolve.
    """
    log.info("Approval worker started")
    while True:
        try:
            # Poll pending items for monitoring/logging
            pending_items = approvals.list()
            if pending_items:
                log.debug(f"Pending approvals: {len(pending_items)}")
                
                # Log old items that might need attention
                current_time = time.time()
                for item in pending_items:
                    age_minutes = (current_time - item.get('created_at', current_time)) / 60
                    if age_minutes > 30:  # 30 minutes old
                        log.warning(f"Approval {item['id']} has been pending for {age_minutes:.1f} minutes")
            
            time.sleep(poll_interval)
        except Exception as e:
            log.error(f"Error in approval worker: {e}")
            time.sleep(5.0)

def on_approval_resolved(item_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute approved actions. Called after an approval is resolved.
    This is where the actual integration work happens.
    """
    action = item_dict["action"]
    payload = item_dict["payload"]
    status = item_dict["status"]
    
    log.info(f"Processing approval: {action} - {status}")
    
    if status != "approved":
        return {"skipped": "rejected", "action": action}

    try:
        # Route to appropriate handler based on action
        if action == "github.pr":
            return execute_github_pr(payload)
        elif action == "github.comment":
            return execute_github_comment(payload)
        elif action == "github.merge":
            return execute_github_merge(payload)
        elif action == "github.branch":
            return execute_github_branch(payload)
        elif action == "github.issue":
            return execute_github_issue(payload)
        elif action == "jira.create":
            return execute_jira_create(payload)
        elif action == "jira.update":
            return execute_jira_update(payload)
        elif action == "jira.comment":
            return execute_jira_comment(payload)
        elif action == "jira.transition":
            return execute_jira_transition(payload)
        elif action == "ci.fix_suggestions":
            return execute_ci_fix_suggestions(payload)
        elif action == "ci.workflow_failure":
            return execute_workflow_failure(payload)
        elif action == "pr.review_suggestions":
            return execute_pr_review_suggestions(payload)
        elif action == "pr.review_requested":
            return execute_pr_review_requested(payload)
        elif action == "deployment.suggest":
            return execute_deployment_suggest(payload)
        elif action == "issue.triage_suggestions":
            return execute_issue_triage(payload)
        elif action == "github.pr_auto_reply":
            return execute_github_pr_auto_reply(payload)
        elif action == "github.apply_patch":
            return execute_github_apply_patch(payload)
        else:
            return {"error": "unknown_action", "action": action}
            
    except Exception as e:
        log.error(f"Error executing approval {action}: {e}")
        return {"error": str(e), "action": action}

# GitHub action handlers
def execute_github_pr(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a GitHub pull request"""
    required_fields = ["owner", "repo", "head", "base", "title"]
    if not all(field in payload for field in required_fields):
        return {"error": "missing_required_fields", "required": required_fields}
    
    result = github.create_pr(
        owner=payload["owner"],
        repo=payload["repo"],
        head=payload["head"],
        base=payload["base"],
        title=payload["title"],
        body=payload.get("body", "")
    )
    
    log.info(f"Created PR: {payload['title']} on {payload['owner']}/{payload['repo']}")
    return {"success": True, "result": result}

def execute_github_comment(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Add comment to GitHub PR or issue"""
    if "pr_number" in payload:
        result = github.comment_pr(
            owner=payload["owner"],
            repo=payload["repo"],
            pr_number=payload["pr_number"],
            body=payload["body"]
        )
    elif "issue_number" in payload:
        result = github.comment_issue(
            owner=payload["owner"],
            repo=payload["repo"],
            issue_number=payload["issue_number"],
            body=payload["body"]
        )
    else:
        return {"error": "missing pr_number or issue_number"}
    
    log.info(f"Added comment to {payload['owner']}/{payload['repo']}")
    return {"success": True, "result": result}

def execute_github_merge(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Merge a GitHub pull request"""
    result = github.merge_pr(
        owner=payload["owner"],
        repo=payload["repo"],
        pr_number=payload["pr_number"],
        commit_title=payload.get("commit_title", ""),
        commit_message=payload.get("commit_message", ""),
        merge_method=payload.get("merge_method", "merge")
    )
    
    log.info(f"Merged PR #{payload['pr_number']} on {payload['owner']}/{payload['repo']}")
    return {"success": True, "result": result}

def execute_github_branch(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a GitHub branch"""
    result = github.create_branch(
        owner=payload["owner"],
        repo=payload["repo"],
        base_branch=payload["base_branch"],
        new_branch=payload["new_branch"]
    )
    
    log.info(f"Created branch {payload['new_branch']} on {payload['owner']}/{payload['repo']}")
    return {"success": True, "result": result}

def execute_github_issue(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a GitHub issue"""
    result = github.create_issue(
        owner=payload["owner"],
        repo=payload["repo"],
        title=payload["title"],
        body=payload.get("body", ""),
        labels=payload.get("labels", [])
    )
    
    log.info(f"Created issue: {payload['title']} on {payload['owner']}/{payload['repo']}")
    return {"success": True, "result": result}

def execute_github_pr_auto_reply(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute auto-reply suggestions on GitHub PR"""
    import json
    
    try:
        data = json.loads(payload["suggestions_json"])
        replies = data.get("replies", [])
        posted_comments = []
        
        # Post each reply as a comment (limit to 10 for safety)
        for r in replies[:10]:
            body = r if isinstance(r, str) else r.get("body", "")
            if not body:
                continue
                
            result = github.comment_pr(
                owner=payload["owner"],
                repo=payload["repo"],
                pr_number=payload["pr_number"],
                body=body
            )
            posted_comments.append(result)
        
        log.info(f"Posted {len(posted_comments)} auto-reply comments on PR #{payload['pr_number']}")
        
        return {
            "success": True,
            "posted_comments": posted_comments,
            "proposed_patch": data.get("proposed_patch", ""),
            "total_replies": len(replies)
        }
    except Exception as e:
        log.error(f"Error executing PR auto-reply: {e}")
        return {"success": False, "error": str(e)}

# Jira action handlers
def execute_jira_create(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a Jira issue"""
    result = jira.create_issue(
        project_key=payload["project_key"],
        summary=payload["summary"],
        description=payload["description"],
        issue_type=payload.get("issue_type", "Task")
    )
    
    log.info(f"Created Jira issue: {payload['summary']} in {payload['project_key']}")
    return {"success": True, "result": result}

def execute_jira_update(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update a Jira issue"""
    result = jira.update_issue(
        key=payload["key"],
        fields=payload["fields"]
    )
    
    log.info(f"Updated Jira issue: {payload['key']}")
    return {"success": True, "result": result}

def execute_jira_comment(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Add comment to Jira issue"""
    result = jira.add_comment(
        key=payload["key"],
        comment=payload["comment"]
    )
    
    log.info(f"Added comment to Jira issue: {payload['key']}")
    return {"success": True, "result": result}

def execute_jira_transition(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Transition Jira issue status"""
    result = jira.transition_issue(
        key=payload["key"],
        transition_id=payload["transition_id"],
        comment=payload.get("comment")
    )
    
    log.info(f"Transitioned Jira issue: {payload['key']}")
    return {"success": True, "result": result}

# CI and automation handlers
def execute_ci_fix_suggestions(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle CI failure with fix suggestions"""
    repo = payload.get("repo")
    branch = payload.get("branch")
    hints = payload.get("hints", [])
    
    # For now, create a GitHub issue with suggestions
    # In a real implementation, this could analyze logs and create fix PRs
    issue_body = f"""
## CI Failure Detected

**Repository:** {repo}
**Branch:** {branch}
**Check Suite ID:** {payload.get('check_suite_id', 'N/A')}

### Suggested Fixes:
{chr(10).join(f'- {hint}' for hint in hints)}

### Next Steps:
1. Review the CI logs for specific error messages
2. Apply suggested fixes above
3. Re-run the failed checks

*This issue was automatically created by the AI Interview Assistant.*
"""
    
    if repo and "/" in repo:
        owner, repo_name = repo.split("/", 1)
        issue_payload = {
            "owner": owner,
            "repo": repo_name,
            "title": f"CI Failure: {branch}",
            "body": issue_body,
            "labels": ["ci-failure", "automated"]
        }
        
        # Create approval for creating the issue
        issue_result = execute_github_issue(issue_payload)
        return {"success": True, "action": "created_issue", "result": issue_result}
    
    return {"success": True, "action": "logged_suggestions", "hints": hints}

def execute_workflow_failure(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle workflow failure"""
    # Similar to CI fix suggestions but more specific to workflows
    return execute_ci_fix_suggestions(payload)

def execute_pr_review_suggestions(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle PR review suggestions"""
    suggestions = payload.get("suggestions", [])
    pr_number = payload.get("pr_number")
    repo = payload.get("repo")
    
    if suggestions and pr_number and repo:
        comment_body = f"""
## Automated Review Suggestions

{chr(10).join(f'- {suggestion}' for suggestion in suggestions)}

*These suggestions were automatically generated by the AI Interview Assistant.*
"""
        
        owner, repo_name = repo.split("/", 1) if "/" in repo else ("", repo)
        comment_payload = {
            "owner": owner,
            "repo": repo_name,
            "pr_number": pr_number,
            "body": comment_body
        }
        
        return execute_github_comment(comment_payload)
    
    return {"success": True, "action": "no_suggestions"}

def execute_pr_review_requested(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle PR review request notification"""
    # For now, just log it. Could integrate with Slack, email, etc.
    log.info(f"Review requested for PR #{payload.get('pr_number')} by {payload.get('requested_reviewer')}")
    return {"success": True, "action": "notified"}

def execute_deployment_suggest(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle deployment suggestions"""
    repo = payload.get("repo")
    commit_count = payload.get("commit_count", 0)
    
    # Create a deployment checklist issue
    issue_body = f"""
## Deployment Suggestion

**Repository:** {repo}
**Commits:** {commit_count} new commits on main branch

### Pre-deployment Checklist:
- [ ] Review all changes in the commits
- [ ] Ensure all tests are passing
- [ ] Check if database migrations are needed
- [ ] Verify environment configuration
- [ ] Schedule deployment window if needed

### Post-deployment:
- [ ] Monitor application health
- [ ] Verify feature functionality
- [ ] Check error rates and performance

*This checklist was automatically generated by the AI Interview Assistant.*
"""
    
    if repo and "/" in repo:
        owner, repo_name = repo.split("/", 1)
        issue_payload = {
            "owner": owner,
            "repo": repo_name,
            "title": f"Deployment Checklist - {commit_count} commits",
            "body": issue_body,
            "labels": ["deployment", "checklist", "automated"]
        }
        
        return execute_github_issue(issue_payload)
    
    return {"success": True, "action": "logged_suggestion"}

def execute_issue_triage(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle issue triage suggestions"""
    suggestions = payload.get("suggestions", [])
    issue_number = payload.get("issue_number")
    repo = payload.get("repo")
    
    if suggestions and issue_number and repo:
        comment_body = f"""
## Triage Suggestions

{chr(10).join(f'- {suggestion}' for suggestion in suggestions)}

*These suggestions were automatically generated by the AI Interview Assistant.*
"""
        
        owner, repo_name = repo.split("/", 1) if "/" in repo else ("", repo)
        comment_payload = {
            "owner": owner,
            "repo": repo_name,
            "issue_number": issue_number,
            "body": comment_body
        }
        
        return execute_github_comment(comment_payload)
    
    return {"success": True, "action": "no_suggestions"}

def execute_github_apply_patch(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Apply unified diff patch with GitHub branch/commit/PR automation"""
    from backend.patch_apply import apply_patch
    
    try:
        patch_content = payload.get("patch_content", "")
        branch_name = payload.get("branch_name", f"auto-patch-{int(time.time())}")
        commit_message = payload.get("commit_message", "Apply automated patch changes")
        pr_title = payload.get("pr_title", f"Automated patch: {branch_name}")
        
        if not patch_content:
            return {"error": "missing_patch_content"}
        
        # Apply patch with GitHub automation
        result = apply_patch(
            patch_content=patch_content,
            branch_name=branch_name,
            commit_message=commit_message,
            pr_title=pr_title
        )
        
        if result.get("success"):
            log.info(f"Applied patch successfully: {result.get('pr_url', 'No PR created')}")
            return {"success": True, "result": result}
        else:
            log.error(f"Patch application failed: {result.get('error')}")
            return {"success": False, "error": result.get("error")}
            
    except Exception as e:
        log.error(f"Error in apply_patch execution: {e}")
        return {"success": False, "error": str(e)}

def start_worker_thread():
    """Start the approval worker in a background thread"""
    worker_thread = threading.Thread(target=run_worker, daemon=True)
    worker_thread.start()
    return worker_thread

# Configuration functions
def set_dry_run_mode(enabled: bool):
    """Enable/disable dry run mode for all integrations"""
    global github, jira
    github.dry_run = enabled
    jira.dry_run = enabled
    log.info(f"Dry run mode {'enabled' if enabled else 'disabled'}")

def get_integration_status() -> Dict[str, Any]:
    """Get status of all integrations"""
    return {
        "github_dry_run": github.dry_run,
        "jira_dry_run": jira.dry_run,
        "pending_approvals": len(approvals.list())
    }
