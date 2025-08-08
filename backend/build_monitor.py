# backend/build_monitor.py
"""
Advanced CI/CD build monitoring with failure analysis and automated fixes.
Monitors GitHub Actions, Jenkins, and other CI systems.
"""

from __future__ import annotations
import os
import time
import requests
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import re

log = logging.getLogger(__name__)

class BuildMonitor:
    """Monitors CI/CD builds and provides intelligent failure analysis"""
    
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.webhook_processors = {
            "github_actions": self._process_github_actions,
            "jenkins": self._process_jenkins,
            "circle_ci": self._process_circle_ci
        }
        self.failure_patterns = self._load_failure_patterns()
    
    def _load_failure_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load common failure patterns and their fixes"""
        return {
            "dependency_error": {
                "patterns": [
                    r"ModuleNotFoundError: No module named '(\w+)'",
                    r"ImportError: cannot import name '(\w+)'",
                    r"pip.*install.*failed",
                    r"requirements\.txt.*not found"
                ],
                "severity": "medium",
                "auto_fix": "dependency_fix",
                "description": "Missing or incompatible dependencies"
            },
            "syntax_error": {
                "patterns": [
                    r"SyntaxError: (.+)",
                    r"IndentationError: (.+)",
                    r"TabError: (.+)"
                ],
                "severity": "high", 
                "auto_fix": "syntax_fix",
                "description": "Python syntax or indentation errors"
            },
            "test_failure": {
                "patterns": [
                    r"FAILED (.+) - (.+)",
                    r"AssertionError: (.+)",
                    r"(\d+) failed, (\d+) passed"
                ],
                "severity": "medium",
                "auto_fix": "test_fix",
                "description": "Unit test failures"
            },
            "lint_error": {
                "patterns": [
                    r"flake8.*error",
                    r"pylint.*error",
                    r"black.*error",
                    r"mypy.*error"
                ],
                "severity": "low",
                "auto_fix": "lint_fix",
                "description": "Code quality and linting issues"
            },
            "docker_error": {
                "patterns": [
                    r"Dockerfile.*not found",
                    r"docker build.*failed",
                    r"container.*failed to start"
                ],
                "severity": "high",
                "auto_fix": "docker_fix", 
                "description": "Docker build or runtime errors"
            },
            "environment_error": {
                "patterns": [
                    r"Environment variable.*not set",
                    r"Configuration.*missing",
                    r"Secret.*not found"
                ],
                "severity": "medium",
                "auto_fix": "env_fix",
                "description": "Environment configuration issues"
            }
        }
    
    def analyze_build_failure(self, build_log: str, build_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze build failure and suggest fixes"""
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "build_id": build_info.get("id", "unknown"),
            "repository": build_info.get("repository", "unknown"),
            "branch": build_info.get("branch", "unknown"),
            "failures": [],
            "suggestions": [],
            "auto_fixes": [],
            "severity": "unknown"
        }
        
        # Analyze failure patterns
        for error_type, config in self.failure_patterns.items():
            for pattern in config["patterns"]:
                matches = re.finditer(pattern, build_log, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    failure = {
                        "type": error_type,
                        "description": config["description"],
                        "severity": config["severity"],
                        "matched_text": match.group(0),
                        "line_context": self._extract_context(build_log, match.start()),
                        "suggested_fix": self._generate_fix_suggestion(error_type, match.groups())
                    }
                    analysis["failures"].append(failure)
                    
                    # Add auto-fix if available
                    if config.get("auto_fix"):
                        analysis["auto_fixes"].append({
                            "type": config["auto_fix"],
                            "error_type": error_type,
                            "fix_data": match.groups()
                        })
        
        # Determine overall severity
        if any(f["severity"] == "high" for f in analysis["failures"]):
            analysis["severity"] = "high"
        elif any(f["severity"] == "medium" for f in analysis["failures"]):
            analysis["severity"] = "medium"
        else:
            analysis["severity"] = "low"
        
        # Generate intelligent suggestions
        analysis["suggestions"] = self._generate_intelligent_suggestions(analysis["failures"], build_info)
        
        return analysis
    
    def _extract_context(self, log: str, match_pos: int, context_lines: int = 3) -> List[str]:
        """Extract context lines around a failure"""
        lines = log.split('\n')
        
        # Find the line number of the match
        char_count = 0
        match_line = 0
        for i, line in enumerate(lines):
            char_count += len(line) + 1  # +1 for newline
            if char_count >= match_pos:
                match_line = i
                break
        
        # Extract context
        start = max(0, match_line - context_lines)
        end = min(len(lines), match_line + context_lines + 1)
        
        return lines[start:end]
    
    def _generate_fix_suggestion(self, error_type: str, match_groups: tuple) -> str:
        """Generate specific fix suggestions based on error type"""
        if error_type == "dependency_error" and match_groups:
            module_name = match_groups[0] if match_groups else "unknown"
            return f"Add '{module_name}' to requirements.txt or install with: pip install {module_name}"
        
        elif error_type == "syntax_error":
            return "Review the code for syntax errors. Use a linter like flake8 or pylint to identify issues."
        
        elif error_type == "test_failure":
            return "Review failing test cases. Check if the test expectations match the current implementation."
        
        elif error_type == "lint_error":
            return "Run code formatters: black . && flake8 . && mypy ."
        
        elif error_type == "docker_error":
            return "Check Dockerfile syntax and ensure all required files are included in the build context."
        
        elif error_type == "environment_error":
            return "Verify environment variables are set in your CI/CD configuration and secrets are properly configured."
        
        return "Review the error log and documentation for resolution steps."
    
    def _generate_intelligent_suggestions(self, failures: List[Dict], build_info: Dict) -> List[str]:
        """Generate high-level intelligent suggestions"""
        suggestions = []
        
        failure_types = [f["type"] for f in failures]
        
        # Pattern-based suggestions
        if "dependency_error" in failure_types:
            suggestions.append("🔧 Consider using a dependency management tool like Poetry or Pipenv")
            suggestions.append("📋 Pin dependency versions in requirements.txt to avoid compatibility issues")
        
        if "test_failure" in failure_types:
            suggestions.append("🧪 Run tests locally before pushing: pytest tests/")
            suggestions.append("📊 Consider adding more comprehensive test coverage")
        
        if len(failure_types) > 3:
            suggestions.append("⚡ Multiple issues detected - consider running a comprehensive code review")
            suggestions.append("🔄 Set up pre-commit hooks to catch issues before pushing")
        
        # Build-specific suggestions
        if build_info.get("branch") != "main":
            suggestions.append("🌿 Consider merging latest main branch to resolve conflicts")
        
        if any("docker" in f["type"] for f in failures):
            suggestions.append("🐳 Test Docker builds locally: docker build -t test-image .")
        
        return suggestions
    
    def generate_auto_fix_pr(self, analysis: Dict[str, Any], repository: str) -> Optional[str]:
        """Generate automated fix PR for common issues"""
        if not analysis["auto_fixes"]:
            return None
        
        fixes = []
        
        for auto_fix in analysis["auto_fixes"]:
            fix_type = auto_fix["type"]
            
            if fix_type == "dependency_fix":
                fixes.extend(self._generate_dependency_fixes(auto_fix))
            elif fix_type == "lint_fix":
                fixes.extend(self._generate_lint_fixes(auto_fix))
            elif fix_type == "test_fix":
                fixes.extend(self._generate_test_fixes(auto_fix))
        
        if not fixes:
            return None
        
        # Create fix branch and PR
        return self._create_fix_pr(repository, fixes, analysis)
    
    def _generate_dependency_fixes(self, fix_data: Dict) -> List[Dict]:
        """Generate dependency-related fixes"""
        return [
            {
                "file": "requirements.txt",
                "action": "append",
                "content": f"{fix_data['fix_data'][0] if fix_data['fix_data'] else 'missing-package'}>=1.0.0\n"
            },
            {
                "file": ".github/workflows/test.yml", 
                "action": "ensure_exists",
                "content": """name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - run: pip install -r requirements.txt
    - run: pytest
"""
            }
        ]
    
    def _generate_lint_fixes(self, fix_data: Dict) -> List[Dict]:
        """Generate linting-related fixes"""
        return [
            {
                "file": ".pre-commit-config.yaml",
                "action": "create",
                "content": """repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
"""
            },
            {
                "file": "pyproject.toml",
                "action": "create",
                "content": """[tool.black]
line-length = 88
target-version = ['py39']

[tool.flake8]
max-line-length = 88
extend-ignore = E203, W503
"""
            }
        ]
    
    def _generate_test_fixes(self, fix_data: Dict) -> List[Dict]:
        """Generate test-related fixes"""
        return [
            {
                "file": "pytest.ini",
                "action": "create", 
                "content": """[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
"""
            }
        ]
    
    def _create_fix_pr(self, repository: str, fixes: List[Dict], analysis: Dict) -> str:
        """Create a GitHub PR with automated fixes"""
        # This would use GitHub API to create a branch and PR
        # For now, return a summary
        
        pr_description = f"""## 🤖 Automated Build Fix

**Build ID**: {analysis['build_id']}
**Failures Detected**: {len(analysis['failures'])}
**Severity**: {analysis['severity']}

### Issues Fixed:
"""
        
        for failure in analysis['failures']:
            pr_description += f"- **{failure['type']}**: {failure['description']}\n"
        
        pr_description += "\n### Changes Made:\n"
        for fix in fixes:
            pr_description += f"- {fix['action'].title()} `{fix['file']}`\n"
        
        pr_description += "\n### Suggestions:\n"
        for suggestion in analysis['suggestions']:
            pr_description += f"- {suggestion}\n"
        
        pr_description += "\n*This PR was automatically generated by AI Mentor Build Monitor*"
        
        return pr_description
    
    def monitor_repository(self, repository: str, branch: str = "main") -> Dict[str, Any]:
        """Monitor a repository for build status"""
        if not self.github_token:
            return {"error": "GitHub token not configured"}
        
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json"
        }
        
        # Get latest workflow runs
        url = f"https://api.github.com/repos/{repository}/actions/runs"
        params = {"branch": branch, "per_page": 10}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            runs = response.json()["workflow_runs"]
            
            monitoring_result = {
                "repository": repository,
                "branch": branch,
                "total_runs": len(runs),
                "failed_runs": 0,
                "success_rate": 0,
                "recent_failures": [],
                "trends": {}
            }
            
            # Analyze recent runs
            for run in runs:
                if run["conclusion"] == "failure":
                    monitoring_result["failed_runs"] += 1
                    
                    # Get failure details
                    failure_analysis = self._analyze_workflow_failure(repository, run["id"])
                    monitoring_result["recent_failures"].append({
                        "run_id": run["id"],
                        "created_at": run["created_at"],
                        "head_commit": run["head_commit"]["message"],
                        "analysis": failure_analysis
                    })
            
            # Calculate success rate
            if len(runs) > 0:
                monitoring_result["success_rate"] = (len(runs) - monitoring_result["failed_runs"]) / len(runs) * 100
            
            return monitoring_result
            
        except requests.RequestException as e:
            log.error(f"Failed to monitor repository {repository}: {e}")
            return {"error": str(e)}
    
    def _analyze_workflow_failure(self, repository: str, run_id: str) -> Dict[str, Any]:
        """Analyze a specific workflow failure"""
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json"
        }
        
        # Get workflow run logs
        url = f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/logs"
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                # Process the log content
                log_content = response.text
                build_info = {
                    "id": run_id,
                    "repository": repository
                }
                
                return self.analyze_build_failure(log_content, build_info)
            else:
                return {"error": f"Could not fetch logs for run {run_id}"}
                
        except requests.RequestException as e:
            return {"error": str(e)}

# Integration with approval system
def submit_build_failure_for_review(analysis: Dict[str, Any], repository: str):
    """Submit build failure analysis for approval/review"""
    from backend.approvals import approvals
    
    if analysis["severity"] == "high":
        # High severity failures need immediate attention
        approval_item = approvals.submit("ci.fix_suggestions", {
            "repository": repository,
            "analysis": analysis,
            "priority": "high",
            "auto_fix_available": len(analysis["auto_fixes"]) > 0
        })
        
        return approval_item
    
    return None

if __name__ == "__main__":
    monitor = BuildMonitor()
    
    # Example usage
    result = monitor.monitor_repository("NNDSrinivas/mentor_app")
    print(json.dumps(result, indent=2))
