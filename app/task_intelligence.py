"""
Task Intelligence System
Inspired by Cluely's approach to JIRA integration and task management.

This system:
- Integrates with JIRA, Linear, Asana, and other task management tools
- Analyzes requirements and automatically creates stories/tasks
- Provides sprint planning assistance and workload optimization
- Tracks task progress and predicts completion times
- Generates intelligent task recommendations
"""
import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# JIRA integration
try:
    from jira import JIRA
    JIRA_AVAILABLE = True
except ImportError:
    JIRA_AVAILABLE = False

# Linear integration
try:
    import requests
    LINEAR_AVAILABLE = True
except ImportError:
    LINEAR_AVAILABLE = False

from .config import Config

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """Standard task status enum"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    """Task priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TaskType(Enum):
    """Task types for categorization"""
    FEATURE = "feature"
    BUG = "bug"
    STORY = "story"
    EPIC = "epic"
    TASK = "task"
    SPIKE = "spike"
    IMPROVEMENT = "improvement"

@dataclass
class TaskRequirement:
    """Represents a requirement extracted from text"""
    requirement_id: str
    description: str
    source: str  # "meeting", "email", "document", etc.
    priority: TaskPriority
    estimated_effort: Optional[int]  # Story points or hours
    acceptance_criteria: List[str]
    dependencies: List[str]
    stakeholders: List[str]
    extracted_confidence: float
    created_at: str

@dataclass
class TaskStory:
    """Represents a user story or task"""
    story_id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    story_points: Optional[int]
    priority: TaskPriority
    task_type: TaskType
    status: TaskStatus
    assignee: Optional[str]
    reporter: str
    sprint: Optional[str]
    epic: Optional[str]
    labels: List[str]
    components: List[str]
    created_at: str
    updated_at: str
    due_date: Optional[str]
    external_id: Optional[str]  # JIRA ticket ID, Linear issue ID, etc.
    metadata: Dict[str, Any]

@dataclass
class Sprint:
    """Represents a sprint or iteration"""
    sprint_id: str
    name: str
    start_date: str
    end_date: str
    goal: str
    status: str  # "future", "active", "closed"
    capacity: int  # Total story points capacity
    committed_points: int
    completed_points: int
    tasks: List[str]  # Task IDs in this sprint
    team: str
    metadata: Dict[str, Any]

@dataclass
class TaskAnalytics:
    """Task analytics and metrics"""
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    blocked_tasks: int
    average_completion_time: float  # in days
    velocity: float  # story points per sprint
    burndown_data: List[Dict[str, Any]]
    team_workload: Dict[str, int]
    predicted_completion: str
    risk_factors: List[str]

class JIRAIntegration:
    """
    JIRA API integration for task management
    """
    
    def __init__(self, server_url: str, username: str, api_token: str):
        self.server_url = server_url
        self.username = username
        self.api_token = api_token
        self.jira_client = None
        
        if JIRA_AVAILABLE:
            try:
                self.jira_client = JIRA(
                    server=server_url,
                    basic_auth=(username, api_token)
                )
                logger.info("🎯 JIRA integration initialized")
            except Exception as e:
                logger.error(f"❌ JIRA initialization failed: {e}")
        else:
            logger.warning("⚠️ JIRA library not available")
    
    async def create_issue(self, story: TaskStory, project_key: str) -> Optional[str]:
        """Create a JIRA issue from a story"""
        
        if not self.jira_client:
            logger.error("❌ JIRA client not available")
            return None
        
        try:
            # Map task type to JIRA issue type
            issue_type_map = {
                TaskType.FEATURE: "Story",
                TaskType.BUG: "Bug",
                TaskType.STORY: "Story",
                TaskType.EPIC: "Epic",
                TaskType.TASK: "Task",
                TaskType.SPIKE: "Spike",
                TaskType.IMPROVEMENT: "Improvement"
            }
            
            # Map priority
            priority_map = {
                TaskPriority.LOW: "Low",
                TaskPriority.MEDIUM: "Medium",
                TaskPriority.HIGH: "High",
                TaskPriority.CRITICAL: "Highest"
            }
            
            # Prepare issue data
            issue_data = {
                'project': {'key': project_key},
                'summary': story.title,
                'description': self._format_description(story),
                'issuetype': {'name': issue_type_map.get(story.task_type, "Story")},
                'priority': {'name': priority_map.get(story.priority, "Medium")}
            }
            
            # Add optional fields
            if story.assignee:
                issue_data['assignee'] = {'name': story.assignee}
            
            if story.labels:
                issue_data['labels'] = story.labels
            
            if story.components:
                issue_data['components'] = [{'name': comp} for comp in story.components]
            
            if story.story_points:
                # Note: Story Points field varies by JIRA configuration
                issue_data['customfield_10002'] = story.story_points  # Common field ID
            
            # Create the issue
            new_issue = self.jira_client.create_issue(fields=issue_data)
            
            logger.info(f"✅ Created JIRA issue: {new_issue.key}")
            return new_issue.key
            
        except Exception as e:
            logger.error(f"❌ Failed to create JIRA issue: {e}")
            return None
    
    async def update_issue(self, issue_key: str, updates: Dict[str, Any]) -> bool:
        """Update a JIRA issue"""
        
        if not self.jira_client:
            return False
        
        try:
            issue = self.jira_client.issue(issue_key)
            
            # Apply updates
            for field, value in updates.items():
                setattr(issue.fields, field, value)
            
            issue.update()
            
            logger.info(f"✅ Updated JIRA issue: {issue_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update JIRA issue {issue_key}: {e}")
            return False
    
    async def get_project_issues(self, project_key: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """Get issues from a JIRA project"""
        
        if not self.jira_client:
            return []
        
        try:
            # Search for issues in the project
            jql = f"project = {project_key} ORDER BY created DESC"
            issues = self.jira_client.search_issues(jql, maxResults=max_results)
            
            # Convert to our format
            converted_issues = []
            for issue in issues:
                converted_issue = {
                    'key': issue.key,
                    'summary': issue.fields.summary,
                    'description': issue.fields.description or "",
                    'status': issue.fields.status.name,
                    'priority': issue.fields.priority.name if issue.fields.priority else "Medium",
                    'assignee': issue.fields.assignee.displayName if issue.fields.assignee else None,
                    'reporter': issue.fields.reporter.displayName if issue.fields.reporter else None,
                    'created': issue.fields.created,
                    'updated': issue.fields.updated,
                    'labels': issue.fields.labels or [],
                    'components': [comp.name for comp in issue.fields.components] if issue.fields.components else []
                }
                converted_issues.append(converted_issue)
            
            logger.info(f"📋 Retrieved {len(converted_issues)} issues from {project_key}")
            return converted_issues
            
        except Exception as e:
            logger.error(f"❌ Failed to get JIRA issues: {e}")
            return []
    
    async def get_sprints(self, board_id: int) -> List[Dict[str, Any]]:
        """Get sprints from a JIRA board"""
        
        if not self.jira_client:
            return []
        
        try:
            # Get board sprints
            sprints = self.jira_client.sprints(board_id)
            
            converted_sprints = []
            for sprint in sprints:
                converted_sprint = {
                    'id': sprint.id,
                    'name': sprint.name,
                    'state': sprint.state,
                    'startDate': sprint.startDate,
                    'endDate': sprint.endDate,
                    'goal': getattr(sprint, 'goal', ''),
                }
                converted_sprints.append(converted_sprint)
            
            logger.info(f"🏃‍♂️ Retrieved {len(converted_sprints)} sprints")
            return converted_sprints
            
        except Exception as e:
            logger.error(f"❌ Failed to get JIRA sprints: {e}")
            return []
    
    def _format_description(self, story: TaskStory) -> str:
        """Format story description for JIRA"""
        
        description_parts = [story.description]
        
        if story.acceptance_criteria:
            description_parts.append("\nAcceptance Criteria:")
            for i, criteria in enumerate(story.acceptance_criteria, 1):
                description_parts.append(f"{i}. {criteria}")
        
        return "\n".join(description_parts)

class LinearIntegration:
    """
    Linear API integration for modern task management
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.linear.app/graphql"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info("⚡ Linear integration initialized")
    
    async def create_issue(self, story: TaskStory, team_id: str) -> Optional[str]:
        """Create a Linear issue from a story"""
        
        try:
            # Map priority
            priority_map = {
                TaskPriority.LOW: 1,
                TaskPriority.MEDIUM: 2,
                TaskPriority.HIGH: 3,
                TaskPriority.CRITICAL: 4
            }
            
            mutation = """
            mutation IssueCreate($input: IssueCreateInput!) {
                issueCreate(input: $input) {
                    success
                    issue {
                        id
                        identifier
                        title
                    }
                }
            }
            """
            
            variables = {
                "input": {
                    "teamId": team_id,
                    "title": story.title,
                    "description": self._format_linear_description(story),
                    "priority": priority_map.get(story.priority, 2),
                    "estimate": story.story_points if story.story_points else None,
                }
            }
            
            if story.assignee:
                # Would need to map assignee to Linear user ID
                pass
            
            if story.labels:
                variables["input"]["labelIds"] = []  # Would need to map labels to Linear label IDs
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={"query": mutation, "variables": variables}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("data", {}).get("issueCreate", {}).get("success"):
                    issue_id = data["data"]["issueCreate"]["issue"]["identifier"]
                    logger.info(f"✅ Created Linear issue: {issue_id}")
                    return issue_id
            
            logger.error(f"❌ Linear issue creation failed: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to create Linear issue: {e}")
            return None
    
    async def get_team_issues(self, team_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get issues from a Linear team"""
        
        try:
            query = """
            query TeamIssues($teamId: String!, $first: Int!) {
                team(id: $teamId) {
                    issues(first: $first) {
                        nodes {
                            id
                            identifier
                            title
                            description
                            priority
                            estimate
                            state {
                                name
                                type
                            }
                            assignee {
                                name
                                email
                            }
                            creator {
                                name
                            }
                            createdAt
                            updatedAt
                            labels {
                                nodes {
                                    name
                                }
                            }
                        }
                    }
                }
            }
            """
            
            variables = {
                "teamId": team_id,
                "first": limit
            }
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={"query": query, "variables": variables}
            )
            
            if response.status_code == 200:
                data = response.json()
                issues = data.get("data", {}).get("team", {}).get("issues", {}).get("nodes", [])
                
                converted_issues = []
                for issue in issues:
                    converted_issue = {
                        'id': issue['identifier'],
                        'title': issue['title'],
                        'description': issue.get('description', ''),
                        'priority': issue.get('priority', 2),
                        'estimate': issue.get('estimate'),
                        'status': issue['state']['name'],
                        'assignee': issue['assignee']['name'] if issue.get('assignee') else None,
                        'creator': issue['creator']['name'] if issue.get('creator') else None,
                        'created': issue['createdAt'],
                        'updated': issue['updatedAt'],
                        'labels': [label['name'] for label in issue.get('labels', {}).get('nodes', [])]
                    }
                    converted_issues.append(converted_issue)
                
                logger.info(f"📋 Retrieved {len(converted_issues)} issues from Linear team")
                return converted_issues
            
            logger.error(f"❌ Linear query failed: {response.text}")
            return []
            
        except Exception as e:
            logger.error(f"❌ Failed to get Linear issues: {e}")
            return []
    
    def _format_linear_description(self, story: TaskStory) -> str:
        """Format story description for Linear"""
        
        description_parts = [story.description]
        
        if story.acceptance_criteria:
            description_parts.append("\n## Acceptance Criteria")
            for criteria in story.acceptance_criteria:
                description_parts.append(f"- [ ] {criteria}")
        
        return "\n".join(description_parts)

class RequirementAnalyzer:
    """
    Analyzes text to extract requirements and generate tasks
    """
    
    def __init__(self, ai_brain):
        self.ai_brain = ai_brain
        logger.info("🔍 Requirement Analyzer initialized")
    
    async def analyze_text(self, text: str, source: str = "unknown") -> List[TaskRequirement]:
        """Analyze text and extract requirements"""
        
        requirements = []
        
        # Extract explicit requirements
        explicit_reqs = self._extract_explicit_requirements(text)
        requirements.extend(explicit_reqs)
        
        # Extract implicit requirements
        implicit_reqs = await self._extract_implicit_requirements(text, source)
        requirements.extend(implicit_reqs)
        
        # Extract user stories
        user_stories = self._extract_user_stories(text)
        requirements.extend(user_stories)
        
        # Score and prioritize requirements
        for req in requirements:
            req.priority = self._assess_priority(req.description)
            req.estimated_effort = self._estimate_effort(req.description)
        
        logger.info(f"📝 Extracted {len(requirements)} requirements from {source}")
        return requirements
    
    def _extract_explicit_requirements(self, text: str) -> List[TaskRequirement]:
        """Extract explicitly stated requirements"""
        
        requirements = []
        
        # Patterns for explicit requirements
        patterns = [
            r'(?:requirement|req|must|should|shall|will)\s*:?\s*(.+?)(?:\.|$)',
            r'(?:we need to|need to|have to|required to)\s+(.+?)(?:\.|$)',
            r'(?:feature|functionality)\s*:?\s*(.+?)(?:\.|$)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                description = match.group(1).strip()
                if len(description) > 10:  # Filter out short matches
                    req = TaskRequirement(
                        requirement_id=f"req_{len(requirements):03d}",
                        description=description,
                        source="explicit",
                        priority=TaskPriority.MEDIUM,
                        estimated_effort=None,
                        acceptance_criteria=[],
                        dependencies=[],
                        stakeholders=[],
                        extracted_confidence=0.8,
                        created_at=datetime.now().isoformat()
                    )
                    requirements.append(req)
        
        return requirements
    
    async def _extract_implicit_requirements(self, text: str, source: str) -> List[TaskRequirement]:
        """Extract implicit requirements using AI analysis"""
        
        requirements = []
        
        # Look for problem statements that imply requirements
        problem_patterns = [
            r'(?:problem|issue|challenge|difficulty)\s*:?\s*(.+?)(?:\.|$)',
            r'(?:users complain|users report|feedback)\s+(.+?)(?:\.|$)',
            r'(?:currently|right now|at the moment)\s+(.+?)(?:but|however|unfortunately)',
        ]
        
        for pattern in problem_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                problem = match.group(1).strip()
                if len(problem) > 10:
                    # Convert problem to requirement
                    implied_req = f"Solve: {problem}"
                    
                    req = TaskRequirement(
                        requirement_id=f"impl_{len(requirements):03d}",
                        description=implied_req,
                        source="implicit",
                        priority=TaskPriority.MEDIUM,
                        estimated_effort=None,
                        acceptance_criteria=[],
                        dependencies=[],
                        stakeholders=[],
                        extracted_confidence=0.6,
                        created_at=datetime.now().isoformat()
                    )
                    requirements.append(req)
        
        return requirements
    
    def _extract_user_stories(self, text: str) -> List[TaskRequirement]:
        """Extract user stories in standard format"""
        
        requirements = []
        
        # Pattern for "As a ... I want ... so that ..." format
        user_story_pattern = r'(?:as\s+a\s+(.+?),?\s+i\s+want\s+(.+?)\s+so\s+that\s+(.+?)(?:\.|$))'
        
        matches = re.finditer(user_story_pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            persona = match.group(1).strip()
            want = match.group(2).strip()
            benefit = match.group(3).strip()
            
            story_description = f"As a {persona}, I want {want} so that {benefit}"
            
            req = TaskRequirement(
                requirement_id=f"story_{len(requirements):03d}",
                description=story_description,
                source="user_story",
                priority=TaskPriority.MEDIUM,
                estimated_effort=None,
                acceptance_criteria=[f"User can {want}", f"Benefit achieved: {benefit}"],
                dependencies=[],
                stakeholders=[persona],
                extracted_confidence=0.9,
                created_at=datetime.now().isoformat()
            )
            requirements.append(req)
        
        return requirements
    
    def _assess_priority(self, description: str) -> TaskPriority:
        """Assess priority based on description content"""
        
        description_lower = description.lower()
        
        # Critical indicators
        critical_words = ['critical', 'urgent', 'asap', 'emergency', 'blocker', 'production', 'security']
        if any(word in description_lower for word in critical_words):
            return TaskPriority.CRITICAL
        
        # High priority indicators
        high_words = ['important', 'high', 'priority', 'deadline', 'customer', 'revenue']
        if any(word in description_lower for word in high_words):
            return TaskPriority.HIGH
        
        # Low priority indicators
        low_words = ['nice to have', 'future', 'eventually', 'low priority', 'enhancement']
        if any(word in description_lower for word in low_words):
            return TaskPriority.LOW
        
        return TaskPriority.MEDIUM
    
    def _estimate_effort(self, description: str) -> int:
        """Estimate effort in story points"""
        
        description_lower = description.lower()
        
        # Complex indicators (high effort)
        complex_indicators = ['architecture', 'refactor', 'migration', 'integration', 'new service']
        if any(indicator in description_lower for indicator in complex_indicators):
            return 8
        
        # Medium complexity indicators
        medium_indicators = ['feature', 'api', 'database', 'ui', 'component']
        if any(indicator in description_lower for indicator in medium_indicators):
            return 5
        
        # Simple indicators (low effort)
        simple_indicators = ['fix', 'update', 'change', 'small', 'minor']
        if any(indicator in description_lower for indicator in simple_indicators):
            return 2
        
        # Default to medium effort
        return 3

class TaskIntelligence:
    """
    Main Task Intelligence System
    Coordinates requirement analysis, task creation, and project management
    """
    
    def __init__(self, ai_brain):
        self.ai_brain = ai_brain
        self.requirement_analyzer = RequirementAnalyzer(ai_brain)
        
        # Task management integrations
        self.jira_integration = None
        self.linear_integration = None
        
        # Initialize integrations if configured
        if Config.JIRA_SERVER and Config.JIRA_USERNAME and Config.JIRA_API_TOKEN:
            self.jira_integration = JIRAIntegration(
                Config.JIRA_SERVER,
                Config.JIRA_USERNAME,
                Config.JIRA_API_TOKEN
            )
        
        if Config.LINEAR_API_KEY:
            self.linear_integration = LinearIntegration(Config.LINEAR_API_KEY)
        
        # In-memory storage for tasks and sprints
        self.tasks: Dict[str, TaskStory] = {}
        self.sprints: Dict[str, Sprint] = {}
        
        logger.info("🎯 Task Intelligence System initialized")
    
    async def process_meeting_for_tasks(self, meeting_data: Dict[str, Any]) -> List[TaskStory]:
        """Process meeting data to extract and create tasks"""
        
        tasks_created = []
        
        # Extract text content from meeting
        text_content = self._extract_meeting_text(meeting_data)
        
        # Analyze requirements
        requirements = await self.requirement_analyzer.analyze_text(text_content, "meeting")
        
        # Convert requirements to tasks
        for req in requirements:
            story = await self._requirement_to_story(req, meeting_data)
            if story:
                tasks_created.append(story)
                self.tasks[story.story_id] = story
        
        # Create external tasks if integrations are available
        for story in tasks_created:
            await self._create_external_task(story)
        
        logger.info(f"📋 Created {len(tasks_created)} tasks from meeting")
        return tasks_created
    
    async def analyze_sprint_capacity(self, sprint_id: str) -> Dict[str, Any]:
        """Analyze sprint capacity and provide recommendations"""
        
        if sprint_id not in self.sprints:
            logger.warning(f"⚠️ Sprint not found: {sprint_id}")
            return {}
        
        sprint = self.sprints[sprint_id]
        
        # Get tasks in sprint
        sprint_tasks = [self.tasks[task_id] for task_id in sprint.tasks if task_id in self.tasks]
        
        # Calculate metrics
        total_points = sum(task.story_points or 0 for task in sprint_tasks)
        completed_points = sum(task.story_points or 0 for task in sprint_tasks if task.status == TaskStatus.DONE)
        
        # Analyze workload by assignee
        workload = {}
        for task in sprint_tasks:
            if task.assignee:
                if task.assignee not in workload:
                    workload[task.assignee] = {'total': 0, 'completed': 0, 'in_progress': 0}
                workload[task.assignee]['total'] += task.story_points or 0
                if task.status == TaskStatus.DONE:
                    workload[task.assignee]['completed'] += task.story_points or 0
                elif task.status == TaskStatus.IN_PROGRESS:
                    workload[task.assignee]['in_progress'] += task.story_points or 0
        
        # Generate recommendations
        recommendations = []
        
        if total_points > sprint.capacity * 1.2:
            recommendations.append("Sprint is over-capacity. Consider moving tasks to next sprint.")
        
        if completed_points / max(total_points, 1) < 0.5:
            recommendations.append("Sprint progress is behind. Consider addressing blockers.")
        
        # Check for unbalanced workload
        max_load = max(data['total'] for data in workload.values()) if workload else 0
        min_load = min(data['total'] for data in workload.values()) if workload else 0
        
        if max_load > min_load * 2:
            recommendations.append("Workload is unbalanced across team members.")
        
        return {
            'sprint_id': sprint_id,
            'total_points': total_points,
            'completed_points': completed_points,
            'capacity': sprint.capacity,
            'capacity_utilization': total_points / max(sprint.capacity, 1),
            'completion_rate': completed_points / max(total_points, 1),
            'workload': workload,
            'recommendations': recommendations,
            'tasks': [asdict(task) for task in sprint_tasks]
        }
    
    async def predict_task_completion(self, task_id: str) -> Dict[str, Any]:
        """Predict when a task will be completed"""
        
        if task_id not in self.tasks:
            logger.warning(f"⚠️ Task not found: {task_id}")
            return {}
        
        task = self.tasks[task_id]
        
        # Simple prediction based on story points and team velocity
        # In production, this would use machine learning models
        
        estimated_days = (task.story_points or 3) * 0.5  # Assuming 2 story points per day
        
        # Adjust based on priority
        if task.priority == TaskPriority.CRITICAL:
            estimated_days *= 0.8
        elif task.priority == TaskPriority.LOW:
            estimated_days *= 1.2
        
        # Adjust based on assignee workload
        if task.assignee:
            # Simple workload adjustment
            estimated_days *= 1.1  # 10% buffer for existing workload
        
        predicted_completion = datetime.now() + timedelta(days=estimated_days)
        
        return {
            'task_id': task_id,
            'estimated_days': estimated_days,
            'predicted_completion': predicted_completion.isoformat(),
            'confidence': 0.7,  # TODO: Calculate actual confidence
            'factors': [
                f"Story points: {task.story_points or 3}",
                f"Priority: {task.priority.value}",
                f"Assignee workload: {task.assignee or 'unassigned'}"
            ]
        }
    
    async def process_task_context(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process task context for AI brain"""
        
        processed_data = {
            'original_data': data,
            'task_complexity': self._assess_complexity(data),
            'dependencies_analysis': self._analyze_dependencies(data),
            'risk_factors': self._identify_risks(data),
            'automation_opportunities': self._identify_automation(data),
            'processed_timestamp': datetime.now().isoformat()
        }
        
        return processed_data
    
    async def generate_task_actions(self, data: Dict[str, Any], insights: Dict[str, Any], 
                                  connections: List[Dict[str, Any]]) -> List:
        """Generate task-specific action recommendations"""
        
        actions = []
        
        # Automatic task creation
        if data.get('requirements'):
            actions.append({
                'type': 'create_tasks',
                'description': 'Create JIRA/Linear tasks from requirements',
                'data': {'requirements': data['requirements']},
                'priority': 'high',
                'estimated_time': 5
            })
        
        # Sprint planning assistance
        if data.get('sprint_analysis'):
            actions.append({
                'type': 'sprint_optimization',
                'description': 'Optimize sprint planning based on capacity analysis',
                'data': {'sprint_data': data['sprint_analysis']},
                'priority': 'medium',
                'estimated_time': 15
            })
        
        # Dependency tracking
        if data.get('dependencies'):
            actions.append({
                'type': 'dependency_tracking',
                'description': 'Set up dependency tracking and alerts',
                'data': {'dependencies': data['dependencies']},
                'priority': 'medium',
                'estimated_time': 10
            })
        
        return actions
    
    def _extract_meeting_text(self, meeting_data: Dict[str, Any]) -> str:
        """Extract text content from meeting data"""
        
        text_parts = []
        
        # Meeting title and description
        if meeting_data.get('title'):
            text_parts.append(meeting_data['title'])
        
        if meeting_data.get('description'):
            text_parts.append(meeting_data['description'])
        
        # Transcript segments
        recording = meeting_data.get('recording')
        if recording and recording.get('segments'):
            for segment in recording['segments']:
                text_parts.append(segment.get('content', ''))
        
        # Action items and decisions
        if recording:
            if recording.get('action_items'):
                for item in recording['action_items']:
                    text_parts.append(item.get('description', ''))
            
            if recording.get('decisions'):
                for decision in recording['decisions']:
                    text_parts.append(decision.get('description', ''))
        
        return '\n'.join(text_parts)
    
    async def _requirement_to_story(self, requirement: TaskRequirement, context: Dict[str, Any]) -> Optional[TaskStory]:
        """Convert a requirement to a task story"""
        
        # Determine task type
        task_type = TaskType.STORY
        if 'bug' in requirement.description.lower() or 'fix' in requirement.description.lower():
            task_type = TaskType.BUG
        elif 'feature' in requirement.description.lower():
            task_type = TaskType.FEATURE
        
        # Generate title from description
        title = requirement.description[:100] + "..." if len(requirement.description) > 100 else requirement.description
        
        story = TaskStory(
            story_id=f"story_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{requirement.requirement_id}",
            title=title,
            description=requirement.description,
            acceptance_criteria=requirement.acceptance_criteria,
            story_points=requirement.estimated_effort,
            priority=requirement.priority,
            task_type=task_type,
            status=TaskStatus.TODO,
            assignee=None,  # To be assigned later
            reporter=context.get('creator', 'AI Assistant'),
            sprint=None,
            epic=None,
            labels=['ai-generated'],
            components=[],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            due_date=None,
            external_id=None,
            metadata={
                'source': requirement.source,
                'confidence': requirement.extracted_confidence,
                'meeting_id': context.get('meeting_id'),
                'stakeholders': requirement.stakeholders
            }
        )
        
        return story
    
    async def _create_external_task(self, story: TaskStory) -> Optional[str]:
        """Create task in external system (JIRA, Linear, etc.)"""
        
        external_id = None
        
        # Try JIRA first
        if self.jira_integration and Config.JIRA_PROJECT_KEY:
            external_id = await self.jira_integration.create_issue(story, Config.JIRA_PROJECT_KEY)
            if external_id:
                story.external_id = external_id
        
        # Try Linear if JIRA failed
        elif self.linear_integration and Config.LINEAR_TEAM_ID:
            external_id = await self.linear_integration.create_issue(story, Config.LINEAR_TEAM_ID)
            if external_id:
                story.external_id = external_id
        
        return external_id
    
    def _assess_complexity(self, data: Dict[str, Any]) -> str:
        """Assess task complexity"""
        
        # Simple complexity assessment based on keywords
        description = data.get('description', '').lower()
        
        high_complexity = ['architecture', 'migration', 'refactor', 'integration', 'new service']
        medium_complexity = ['feature', 'api', 'database', 'component']
        
        if any(keyword in description for keyword in high_complexity):
            return 'high'
        elif any(keyword in description for keyword in medium_complexity):
            return 'medium'
        else:
            return 'low'
    
    def _analyze_dependencies(self, data: Dict[str, Any]) -> List[str]:
        """Analyze task dependencies"""
        
        dependencies = []
        description = data.get('description', '').lower()
        
        # Look for dependency keywords
        dependency_patterns = [
            r'depends on ([^.]+)',
            r'requires ([^.]+)',
            r'blocked by ([^.]+)',
            r'needs ([^.]+) first'
        ]
        
        for pattern in dependency_patterns:
            matches = re.finditer(pattern, description)
            for match in matches:
                dependencies.append(match.group(1).strip())
        
        return dependencies
    
    def _identify_risks(self, data: Dict[str, Any]) -> List[str]:
        """Identify potential risks in the task"""
        
        risks = []
        description = data.get('description', '').lower()
        
        # Risk indicators
        risk_keywords = {
            'technical debt': 'Technical debt accumulation',
            'breaking change': 'Breaking change impact',
            'performance': 'Performance implications',
            'security': 'Security considerations',
            'migration': 'Migration complexity',
            'third party': 'External dependency risk'
        }
        
        for keyword, risk in risk_keywords.items():
            if keyword in description:
                risks.append(risk)
        
        return risks
    
    def _identify_automation(self, data: Dict[str, Any]) -> List[str]:
        """Identify automation opportunities"""
        
        opportunities = []
        description = data.get('description', '').lower()
        
        # Automation opportunities
        automation_keywords = {
            'test': 'Automated testing opportunity',
            'deploy': 'Deployment automation opportunity',
            'build': 'Build automation opportunity',
            'manual': 'Manual process automation opportunity',
            'repeat': 'Repetitive task automation opportunity'
        }
        
        for keyword, opportunity in automation_keywords.items():
            if keyword in description:
                opportunities.append(opportunity)
        
        return opportunities
