"""
JIRA and Task Management Integration
Handles task tracking, assignment, and automated updates
"""

import json
import logging
import requests
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict

from backend.integrations.jira_manager import JiraManager
from backend.integrations.github_manager import GitHubManager
from backend.approvals import request_pr_auto_reply, sync_jira_pr_status

# Config with graceful fallbacks
try:
    from app.config import Config
    if not hasattr(Config, 'JIRA_BASE_URL'):
        Config.JIRA_BASE_URL = os.getenv('JIRA_BASE_URL', 'https://mock-jira.com')
        Config.JIRA_EMAIL = os.getenv('JIRA_EMAIL', 'user@example.com')
        Config.JIRA_USERNAME = os.getenv('JIRA_USERNAME', 'user@example.com')
        Config.JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN', 'mock-token')
        Config.GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', 'mock-token')
        Config.GITHUB_REPO = os.getenv('GITHUB_REPO', 'user/repo')
        Config.BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')
except ImportError:
    class Config:
        JIRA_BASE_URL = os.getenv('JIRA_BASE_URL', 'https://mock-jira.com')
        JIRA_EMAIL = os.getenv('JIRA_EMAIL', 'user@example.com')
        JIRA_USERNAME = os.getenv('JIRA_USERNAME', 'user@example.com')
        JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN', 'mock-token')
        GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', 'mock-token')
        GITHUB_REPO = os.getenv('GITHUB_REPO', 'user/repo')
        BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')

logger = logging.getLogger(__name__)

@dataclass
class Task:
    task_id: str
    title: str
    description: str
    status: str  # "todo", "in_progress", "review", "done"
    assignee: Optional[str] = None
    priority: str = "medium"  # "low", "medium", "high", "critical"
    project: Optional[str] = None
    sprint: Optional[str] = None
    story_points: Optional[int] = None
    labels: List[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    due_date: Optional[datetime] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

class JiraIntegration:
    def __init__(self, base_url: str = None, username: str = None, api_token: str = None):
        self.base_url = base_url or Config.JIRA_BASE_URL
        self.username = username or Config.JIRA_USERNAME
        self.api_token = api_token or Config.JIRA_API_TOKEN
        self.session = requests.Session()
        
        if self.username and self.api_token:
            self.session.auth = (self.username, self.api_token)
            self.session.headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
    
    def get_user_tasks(self, user_email: str, limit: int = 50) -> List[Task]:
        """Get tasks assigned to a specific user"""
        if not self._is_configured():
            return self._get_mock_tasks(user_email)
        
        try:
            jql = f'assignee = "{user_email}" AND status != "Done" ORDER BY priority DESC'
            response = self.session.get(
                f"{self.base_url}/rest/api/3/search",
                params={'jql': jql, 'maxResults': limit}
            )
            response.raise_for_status()
            
            jira_issues = response.json()['issues']
            tasks = []
            
            for issue in jira_issues:
                task = self._convert_jira_to_task(issue)
                tasks.append(task)
                
            return tasks
            
        except Exception as e:
            logger.error(f"Error fetching JIRA tasks: {e}")
            return self._get_mock_tasks(user_email)
    
    def create_task(self, title: str, description: str, project_key: str, assignee: str = None) -> Task:
        """Create a new task in JIRA"""
        if not self._is_configured():
            return self._create_mock_task(title, description, assignee)
        
        try:
            issue_data = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": title,
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": description}]
                            }
                        ]
                    },
                    "issuetype": {"name": "Task"}
                }
            }
            
            if assignee:
                issue_data["fields"]["assignee"] = {"emailAddress": assignee}
                
            response = self.session.post(
                f"{self.base_url}/rest/api/3/issue",
                json=issue_data
            )
            response.raise_for_status()
            
            issue = response.json()
            return self._convert_jira_to_task(issue)
            
        except Exception as e:
            logger.error(f"Error creating JIRA task: {e}")
            return self._create_mock_task(title, description, assignee)
    
    def update_task_status(self, task_id: str, new_status: str) -> bool:
        """Update task status"""
        if not self._is_configured():
            logger.info(f"Mock: Updated task {task_id} to status {new_status}")
            return True
        
        try:
            # Get available transitions
            response = self.session.get(f"{self.base_url}/rest/api/3/issue/{task_id}/transitions")
            response.raise_for_status()
            
            transitions = response.json()['transitions']
            
            # Find matching transition
            target_transition = None
            status_mapping = {
                "todo": ["To Do", "Open", "New"],
                "in_progress": ["In Progress", "In Development"],
                "review": ["In Review", "Code Review"],
                "done": ["Done", "Closed", "Resolved"]
            }
            
            for transition in transitions:
                if transition['to']['name'] in status_mapping.get(new_status, []):
                    target_transition = transition['id']
                    break
            
            if not target_transition:
                logger.warning(f"No transition found for status {new_status}")
                return False
            
            # Execute transition
            response = self.session.post(
                f"{self.base_url}/rest/api/3/issue/{task_id}/transitions",
                json={"transition": {"id": target_transition}}
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            return False
    
    def add_comment(self, task_id: str, comment: str) -> bool:
        """Add comment to task"""
        if not self._is_configured():
            logger.info(f"Mock: Added comment to task {task_id}: {comment}")
            return True
        
        try:
            comment_data = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": comment}]
                        }
                    ]
                }
            }
            
            response = self.session.post(
                f"{self.base_url}/rest/api/3/issue/{task_id}/comment",
                json=comment_data
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error(f"Error adding comment: {e}")
            return False
    
    def _convert_jira_to_task(self, jira_issue: Dict) -> Task:
        """Convert JIRA issue to internal Task format"""
        fields = jira_issue['fields']
        
        return Task(
            task_id=jira_issue['key'],
            title=fields['summary'],
            description=self._extract_description(fields.get('description', {})),
            status=self._map_status(fields['status']['name']),
            assignee=fields.get('assignee', {}).get('emailAddress') if fields.get('assignee') else None,
            priority=self._map_priority(fields.get('priority', {}).get('name', 'Medium')),
            project=fields['project']['key'],
            labels=[label for label in fields.get('labels', [])],
            created_at=datetime.fromisoformat(fields['created'].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(fields['updated'].replace('Z', '+00:00'))
        )
    
    def _extract_description(self, description_obj: Dict) -> str:
        """Extract plain text from JIRA's complex description format"""
        if not description_obj or 'content' not in description_obj:
            return ""
        
        text_parts = []
        for content in description_obj['content']:
            if content.get('type') == 'paragraph' and 'content' in content:
                for text_node in content['content']:
                    if text_node.get('type') == 'text':
                        text_parts.append(text_node.get('text', ''))
        
        return ' '.join(text_parts)
    
    def _map_status(self, jira_status: str) -> str:
        """Map JIRA status to internal status"""
        status_mapping = {
            'To Do': 'todo',
            'Open': 'todo',
            'New': 'todo',
            'In Progress': 'in_progress',
            'In Development': 'in_progress',
            'In Review': 'review',
            'Code Review': 'review',
            'Done': 'done',
            'Closed': 'done',
            'Resolved': 'done'
        }
        return status_mapping.get(jira_status, 'todo')
    
    def _map_priority(self, jira_priority: str) -> str:
        """Map JIRA priority to internal priority"""
        priority_mapping = {
            'Highest': 'critical',
            'High': 'high',
            'Medium': 'medium',
            'Low': 'low',
            'Lowest': 'low'
        }
        return priority_mapping.get(jira_priority, 'medium')
    
    def _is_configured(self) -> bool:
        """Check if JIRA integration is properly configured"""
        return bool(self.base_url and self.username and self.api_token)
    
    def _get_mock_tasks(self, user_email: str) -> List[Task]:
        """Generate mock tasks for development/testing"""
        return [
            Task(
                task_id="PROJ-123",
                title="Implement user authentication API",
                description="Create REST API endpoints for user login, logout, and token validation",
                status="in_progress",
                assignee=user_email,
                priority="high",
                project="PROJ",
                labels=["backend", "api", "auth"]
            ),
            Task(
                task_id="PROJ-124",
                title="Fix database connection timeout",
                description="Users are experiencing timeout errors when the database is under load",
                status="todo",
                assignee=user_email,
                priority="critical",
                project="PROJ",
                labels=["bugfix", "database", "performance"]
            ),
            Task(
                task_id="PROJ-125",
                title="Add unit tests for payment service",
                description="Increase test coverage for the payment processing module",
                status="review",
                assignee=user_email,
                priority="medium",
                project="PROJ",
                labels=["testing", "payment", "coverage"]
            )
        ]
    
    def _create_mock_task(self, title: str, description: str, assignee: str) -> Task:
        """Create a mock task for development/testing"""
        return Task(
            task_id=f"PROJ-{datetime.now().microsecond}",
            title=title,
            description=description,
            status="todo",
            assignee=assignee,
            priority="medium",
            project="PROJ",
            labels=["auto-created"]
        )

class TaskManager:
    def __init__(self):
        self.jira = JiraIntegration()
        # Managers exposed for cross-service integrations
        self.jira_manager = JiraManager(dry_run=True)
        self.github_manager = GitHubManager(dry_run=True)
        self.active_tasks: Dict[str, Task] = {}
        
    def get_user_current_tasks(self, user_email: str) -> List[Task]:
        """Get current tasks for user from all integrated systems"""
        tasks = self.jira.get_user_tasks(user_email)
        
        # Cache active tasks
        for task in tasks:
            self.active_tasks[task.task_id] = task
            
        return tasks

    def auto_reply_to_pr(self, owner: str, repo: str, pr_number: int, jira_issue: Optional[str] = None):
        """Use LLM to suggest fixes for PR comments and queue for approval."""
        return request_pr_auto_reply(owner, repo, pr_number, jira_issue)

    def sync_pr_status_to_jira(self, owner: str, repo: str, pr_number: int, jira_issue: str):
        """Trigger a Jira update reflecting the latest PR status."""
        return sync_jira_pr_status(owner, repo, pr_number, jira_issue)
    
    def extract_tasks_from_meeting(self, meeting_summary: Dict) -> List[str]:
        """Extract potential tasks from meeting content"""
        tasks = []
        
        # Extract from action items
        for action_item in meeting_summary.get('action_items', []):
            if any(keyword in action_item.lower() for keyword in [
                'implement', 'create', 'build', 'fix', 'update', 'add', 'remove', 'test'
            ]):
                tasks.append(action_item)
        
        # Extract from decisions that imply work
        for decision in meeting_summary.get('decisions', []):
            if any(keyword in decision.lower() for keyword in [
                'need to', 'should', 'will', 'must', 'have to'
            ]):
                tasks.append(decision)
        
        return tasks
    
    def suggest_code_implementation(self, task: Task) -> Dict[str, Any]:
        """Analyze task and suggest implementation approach"""
        suggestion = {
            "task_id": task.task_id,
            "implementation_approach": [],
            "estimated_effort": "unknown",
            "required_files": [],
            "dependencies": [],
            "test_strategy": []
        }
        
        # Analyze task description for implementation hints
        description_lower = task.description.lower()
        
        # API-related tasks
        if any(keyword in description_lower for keyword in ['api', 'endpoint', 'rest', 'graphql']):
            suggestion["implementation_approach"].append("Create API endpoints")
            suggestion["required_files"].append("routes/api.py")
            suggestion["test_strategy"].append("API integration tests")
        
        # Database-related tasks
        if any(keyword in description_lower for keyword in ['database', 'db', 'sql', 'table', 'migration']):
            suggestion["implementation_approach"].append("Database schema changes")
            suggestion["required_files"].append("migrations/")
            suggestion["test_strategy"].append("Database unit tests")
        
        # Frontend-related tasks
        if any(keyword in description_lower for keyword in ['ui', 'frontend', 'component', 'react', 'vue']):
            suggestion["implementation_approach"].append("Frontend component development")
            suggestion["required_files"].append("components/")
            suggestion["test_strategy"].append("Component unit tests")
        
        # Authentication/security tasks
        if any(keyword in description_lower for keyword in ['auth', 'login', 'security', 'token']):
            suggestion["implementation_approach"].append("Authentication/security implementation")
            suggestion["dependencies"].append("authentication middleware")
            suggestion["test_strategy"].append("Security tests")
        
        # Estimate effort based on complexity indicators
        complexity_indicators = ['integration', 'complex', 'multiple', 'refactor', 'architecture']
        if any(indicator in description_lower for indicator in complexity_indicators):
            suggestion["estimated_effort"] = "high"
        elif any(indicator in description_lower for indicator in ['fix', 'update', 'small']):
            suggestion["estimated_effort"] = "low"
        else:
            suggestion["estimated_effort"] = "medium"
        
        return suggestion
    
    def create_implementation_plan(self, task: Task) -> Dict[str, Any]:
        """Create detailed implementation plan for a task"""
        suggestion = self.suggest_code_implementation(task)
        
        plan = {
            "task_id": task.task_id,
            "title": task.title,
            "phases": [
                {
                    "phase": "Analysis",
                    "description": "Analyze requirements and plan implementation",
                    "estimated_time": "30 minutes",
                    "deliverables": ["Technical design document", "Implementation checklist"]
                },
                {
                    "phase": "Implementation", 
                    "description": "Write code based on requirements",
                    "estimated_time": "2-4 hours" if suggestion["estimated_effort"] == "medium" else "1-2 hours",
                    "deliverables": ["Source code", "Configuration changes"]
                },
                {
                    "phase": "Testing",
                    "description": "Write and run tests",
                    "estimated_time": "1-2 hours",
                    "deliverables": ["Unit tests", "Integration tests", "Test results"]
                },
                {
                    "phase": "Review",
                    "description": "Code review and PR process",
                    "estimated_time": "30 minutes",
                    "deliverables": ["Pull request", "Code review feedback"]
                }
            ],
            "implementation_approach": suggestion["implementation_approach"],
            "required_files": suggestion["required_files"],
            "dependencies": suggestion["dependencies"],
            "test_strategy": suggestion["test_strategy"],
            "acceptance_criteria": self._extract_acceptance_criteria(task),
            "definition_of_done": [
                "Code implements all requirements",
                "Unit tests pass with >80% coverage",
                "Code review approved",
                "Integration tests pass",
                "Documentation updated"
            ]
        }
        
        return plan
    
    def _extract_acceptance_criteria(self, task: Task) -> List[str]:
        """Extract acceptance criteria from task description"""
        criteria = []
        
        # Look for common acceptance criteria patterns
        description = task.description
        
        # Split by common delimiters
        for delimiter in ['Given', 'When', 'Then', 'As a', 'I want', 'So that']:
            if delimiter in description:
                parts = description.split(delimiter)
                for part in parts[1:]:  # Skip first part
                    criteria.append(f"{delimiter} {part.strip()}")
        
        # If no structured criteria found, extract general requirements
        if not criteria:
            sentences = description.split('.')
            for sentence in sentences:
                sentence = sentence.strip()
                if any(keyword in sentence.lower() for keyword in [
                    'should', 'must', 'will', 'needs to', 'required to'
                ]):
                    criteria.append(sentence)

        return criteria

    def trigger_code_generation(self, task: Task, files: Dict[str, str], base_branch: str = "main") -> Dict[str, Any]:
        """Trigger backend code generation and PR creation for a task"""
        payload = {
            "task_id": task.task_id,
            "title": task.title,
            "description": task.description,
            "files": files,
            "base_branch": base_branch,
        }
        try:
            response = requests.post(f"{Config.BACKEND_URL}/api/codegen", json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error triggering code generation: {e}")
            return {"error": str(e)}

# Note: TaskManager should be instantiated in the application, not here as a module-level singleton
