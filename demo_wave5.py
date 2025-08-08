#!/usr/bin/env python3
"""
Wave 5 Demo - Human-in-the-Loop Approval Gates
==============================================

This demo shows the approval workflow for task/PR/CI-aware operations.
Run this to see how the agent requests approval before any mutations.
"""

import sys
import time
import os
sys.path.append('backend')

from approvals import ApprovalsQueue
from integrations.github_manager import GitHubManager
from integrations.jira_manager import JiraManager

def demo_approval_workflow():
    """Demo the complete approval workflow"""
    print("🚀 Wave 5 Demo: Human-in-the-Loop Approval Gates\n")
    
    # Initialize systems (dry_run=True for safety)
    queue = ApprovalsQueue()
    github = GitHubManager(dry_run=True)
    jira = JiraManager(dry_run=True)
    
    print("✅ Initialized approval-gated systems:")
    print(f"   - GitHub Manager (dry_run={github.dry_run})")
    print(f"   - Jira Manager (dry_run={jira.dry_run})")
    print(f"   - Approval Queue (capacity={queue.q.maxsize})\n")
    
    # Simulate GitHub PR creation request
    print("📋 Scenario 1: GitHub PR Creation Request")
    pr_data = {
        "title": "Fix critical bug in authentication",
        "body": "This PR addresses the security vulnerability found in the auth module",
        "head": "feature/auth-fix",
        "base": "main"
    }
    
    approval_id = queue.submit(
        action="github_create_pr",
        payload={
            "details": pr_data,
            "context": "Security fix identified by AI analysis"
        }
    )
    
    print(f"🔔 Approval request submitted: {approval_id}")
    print("   Action: Create GitHub Pull Request")
    print("   Context: Critical security vulnerability fix")
    print("   Status: Waiting for human approval...\n")
    
    # Show pending approvals
    pending = queue.list()
    print(f"📊 Pending Approvals: {len(pending)}")
    for item in pending:
        print(f"   ID: {item['id']}")
        print(f"   Action: {item['action']}")
        print(f"   Created: {item['created_at']}")
        print(f"   Status: {item['status']}\n")
    
    # Simulate Jira issue creation
    print("📋 Scenario 2: Jira Issue Creation Request")
    issue_data = {
        "project": "DEV",
        "summary": "Implement user authentication audit logs",
        "description": "Add comprehensive logging for all authentication events",
        "issuetype": "Task"
    }
    
    jira_approval_id = queue.submit(
        action="jira_create_issue",
        payload={
            "details": issue_data,
            "context": "Follow-up task for security audit compliance"
        }
    )
    
    print(f"🔔 Approval request submitted: {jira_approval_id}")
    print("   Action: Create Jira Issue")
    print("   Context: Security compliance requirement")
    print("   Status: Waiting for human approval...\n")
    
    # Show all pending approvals
    all_pending = queue.list()
    print(f"📊 Total Pending Approvals: {len(all_pending)}")
    print("\n💡 In a real scenario:")
    print("   1. Human reviewers get WebSocket notifications")
    print("   2. They review the request context and details")
    print("   3. Approval/rejection triggers the approval_worker")
    print("   4. Approved actions execute with full logging")
    print("   5. Results are broadcast via WebSocket to all clients")
    
    print("\n🎯 Wave 5 Success: Agent is now task/PR/CI-aware with approval gates!")

if __name__ == "__main__":
    demo_approval_workflow()
