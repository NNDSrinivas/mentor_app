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
import smtplib
from email.mime.text import MIMEText

log = logging.getLogger(__name__)

class BuildMonitor:
    """Monitors CI/CD builds and provides intelligent failure analysis"""
    
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.webhook_processors = {
            "github_actions": getattr(self, "_process_github_actions", lambda *_a, **_k: {}),
            "jenkins": getattr(self, "_process_jenkins", lambda *_a, **_k: {}),
            "circle_ci": getattr(self, "_process_circle_ci", lambda *_a, **_k: {}),
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

        # Notify interested parties if we detected failures
        if analysis["failures"]:
            self._send_notification(analysis)

        return analysis

    def process_build_log(self, build_log: str, build_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a build log and attempt fixes using codegen"""
        analysis = self.analyze_build_failure(build_log, build_info)

        patches: List[str] = []
        try:
            from backend import codegen
            for failure in analysis.get("failures", []):
                context_text = "\n".join(failure.get("line_context", []))
                patch = codegen.generate_patch({"body": context_text})
                if patch:
                    patches.append(patch)
        except Exception as e:
            log.error(f"Code generation failed: {e}")

        if patches:
            combined = "\n".join(patches)
            analysis["proposed_patch"] = combined
            try:
                from backend.patch_apply import apply_patch
                analysis["patch_application"] = apply_patch(combined)
            except Exception as e:
                analysis["patch_application"] = {"success": False, "error": str(e)}

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

    def _send_notification(self, analysis: Dict[str, Any]) -> None:
        """Send notification about build failures via Slack or email."""
        # Compose message
        lines = [
            f"🚨 Build failure detected in {analysis.get('repository')} (ID: {analysis.get('build_id')})",
            f"Severity: {analysis.get('severity')}",
            "Issues:" ,
        ]
        for f in analysis.get("failures", []):
            lines.append(f"- {f.get('type')}: {f.get('matched_text')}")
        message = "\n".join(lines)

        # Slack notification
        slack_url = os.getenv("SLACK_WEBHOOK_URL")
        if slack_url:
            try:
                requests.post(slack_url, json={"text": message})
            except requests.RequestException as e:
                log.error(f"Slack notification failed: {e}")

        # Email notification
        email_to = os.getenv("NOTIFY_EMAIL")
        smtp_server = os.getenv("SMTP_SERVER")
        if email_to and smtp_server:
            try:
                msg = MIMEText(message)
                msg["Subject"] = "Build Failure Detected"
                msg["From"] = os.getenv("SMTP_FROM", "build-monitor@example.com")
                msg["To"] = email_to
                with smtplib.SMTP(smtp_server) as s:
                    s.send_message(msg)
            except Exception as e:
                log.error(f"Email notification failed: {e}")

        if not slack_url and not (email_to and smtp_server):
            log.warning("No notification channels configured. Message: %s", message)
    
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
                
                return self.process_build_log(log_content, build_info)
            else:
                return {"error": f"Could not fetch logs for run {run_id}"}
                
        except requests.RequestException as e:
            return {"error": str(e)}

# Integration with approval system
def submit_build_failure_for_review(analysis: Dict[str, Any], repository: str):
    """Submit build failure analysis for approval/review"""
    try:
        from backend.approvals import approvals
    except ImportError:
        log.warning("Approvals module not available, skipping approval workflow")
        return None

    auto_commit = os.getenv("AUTO_APPROVE_FIXES", "").lower() in {"1", "true", "yes"}
    approval_item = None

    if analysis["severity"] == "high":
        # High severity failures need immediate attention
        approval_item = approvals.submit("ci.fix_suggestions", {
            "repository": repository,
            "analysis": analysis,
            "priority": "high",
            "auto_fix_available": len(analysis["auto_fixes"]) > 0
        })

    # If auto approval is enabled, push commit using GitHubManager
    if auto_commit and analysis.get("proposed_patch"):
        try:
            from backend.integrations.github_manager import GitHubManager
            owner, repo = repository.split("/", 1)
            branch = f"build-fix-{analysis.get('build_id')}"
            base_branch = analysis.get("branch", "main")
            gm = GitHubManager(dry_run=os.getenv("GITHUB_DRY_RUN", "1") != "0")
            gm.create_branch(owner, repo, base_branch, branch)
            gm.commit_file(owner, repo, branch, "auto_fix.patch", analysis["proposed_patch"].encode(), "Automated build fix")
            gm.create_pr(owner, repo, branch, base_branch, f"Automated fix for build {analysis.get('build_id')}")
            if approval_item:
                approvals.resolve(approval_item.id, "approve", {"branch": branch})
        except Exception as e:
            log.error(f"Failed to push auto-fix: {e}")

    return approval_item

def main():
    """CLI entry point for continuous build monitoring"""
    import argparse

    parser = argparse.ArgumentParser(description="Monitor CI builds for a repository")
    parser.add_argument("repository", help="GitHub repository in 'owner/repo' format")
    parser.add_argument("--branch", default="main", help="Branch to monitor")
    parser.add_argument("--interval", type=int, default=300, help="Polling interval in seconds")
    args = parser.parse_args()

    monitor = BuildMonitor()
    try:
        while True:
            result = monitor.monitor_repository(args.repository, args.branch)
            for failure in result.get("recent_failures", []):
                submit_build_failure_for_review(failure["analysis"], args.repository)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        log.info("Stopping build monitor")


if __name__ == "__main__":
    main()

# Provide no-op processors to satisfy attribute references used in webhook_processors
def _ensure_private_methods_exist():
    if not hasattr(BuildMonitor, "_process_github_actions"):
        def _process_github_actions(self, *args, **kwargs):  # type: ignore
            return {}
        setattr(BuildMonitor, "_process_github_actions", _process_github_actions)
    if not hasattr(BuildMonitor, "_process_jenkins"):
        def _process_jenkins(self, *args, **kwargs):  # type: ignore
            return {}
        setattr(BuildMonitor, "_process_jenkins", _process_jenkins)
    if not hasattr(BuildMonitor, "_process_circle_ci"):
        def _process_circle_ci(self, *args, **kwargs):  # type: ignore
            return {}
        setattr(BuildMonitor, "_process_circle_ci", _process_circle_ci)

_ensure_private_methods_exist()
