"""
Code Intelligence System
Advanced code analysis, generation, and automation system.

This system:
- Analyzes code quality and patterns
- Generates code from requirements
- Automates PR reviews and suggestions
- Monitors build systems and deployments
- Provides intelligent code recommendations
"""
import asyncio
import json
import logging
import os
import subprocess
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Git integration
try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

# GitHub API
try:
    import requests
    GITHUB_API_AVAILABLE = True
except ImportError:
    GITHUB_API_AVAILABLE = False

from .config import Config

logger = logging.getLogger(__name__)

class CodeQuality(Enum):
    """Code quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair" 
    POOR = "poor"
    CRITICAL = "critical"

class CodeType(Enum):
    """Types of code"""
    FEATURE = "feature"
    BUG_FIX = "bug_fix"
    REFACTOR = "refactor"
    TEST = "test"
    DOCUMENTATION = "documentation"
    CONFIGURATION = "configuration"

@dataclass
class CodeAnalysis:
    """Results of code analysis"""
    analysis_id: str
    file_path: str
    language: str
    lines_of_code: int
    complexity_score: float
    quality: CodeQuality
    issues: List[Dict[str, Any]]
    suggestions: List[str]
    test_coverage: Optional[float]
    dependencies: List[str]
    security_concerns: List[str]
    performance_concerns: List[str]
    maintainability_score: float
    analyzed_at: str

@dataclass
class CodeGeneration:
    """Code generation request and result"""
    generation_id: str
    requirement: str
    language: str
    framework: Optional[str]
    generated_code: str
    tests: str
    documentation: str
    confidence: float
    estimated_quality: CodeQuality
    generated_at: str

@dataclass
class PullRequest:
    """Pull request information"""
    pr_id: str
    title: str
    description: str
    source_branch: str
    target_branch: str
    author: str
    files_changed: List[str]
    lines_added: int
    lines_removed: int
    status: str  # "open", "merged", "closed"
    reviews: List[Dict[str, Any]]
    automated_analysis: Optional[CodeAnalysis]
    created_at: str

class GitIntegration:
    """
    Git repository integration for code management
    """
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.repo = None
        
        if GIT_AVAILABLE:
            try:
                self.repo = git.Repo(repo_path)
                logger.info(f"🔧 Git repository initialized: {repo_path}")
            except Exception as e:
                logger.error(f"❌ Git initialization failed: {e}")
        else:
            logger.warning("⚠️ Git library not available")
    
    async def get_recent_commits(self, branch: str = "main", limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent commits from the repository"""
        
        if not self.repo:
            return []
        
        try:
            commits = []
            for commit in self.repo.iter_commits(branch, max_count=limit):
                commit_data = {
                    'hash': commit.hexsha,
                    'message': commit.message.strip(),
                    'author': commit.author.name,
                    'date': commit.committed_datetime.isoformat(),
                    'files_changed': len(commit.stats.files),
                    'insertions': commit.stats.total['insertions'],
                    'deletions': commit.stats.total['deletions']
                }
                commits.append(commit_data)
            
            logger.info(f"📊 Retrieved {len(commits)} recent commits")
            return commits
            
        except Exception as e:
            logger.error(f"❌ Failed to get commits: {e}")
            return []
    
    async def get_file_changes(self, file_path: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent changes for a specific file"""
        
        if not self.repo:
            return []
        
        try:
            changes = []
            for commit in self.repo.iter_commits(paths=file_path, max_count=limit):
                change_data = {
                    'hash': commit.hexsha,
                    'message': commit.message.strip(),
                    'author': commit.author.name,
                    'date': commit.committed_datetime.isoformat(),
                    'file_path': file_path
                }
                changes.append(change_data)
            
            return changes
            
        except Exception as e:
            logger.error(f"❌ Failed to get file changes: {e}")
            return []
    
    async def create_branch(self, branch_name: str, from_branch: str = "main") -> bool:
        """Create a new branch"""
        
        if not self.repo:
            return False
        
        try:
            # Create new branch
            new_branch = self.repo.create_head(branch_name, from_branch)
            new_branch.checkout()
            
            logger.info(f"🌿 Created branch: {branch_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create branch: {e}")
            return False
    
    async def commit_changes(self, message: str, files: Optional[List[str]] = None) -> Optional[str]:
        """Commit changes to the repository"""
        
        if not self.repo:
            return None
        
        try:
            # Add files (all if none specified)
            if files:
                self.repo.index.add(files)
            else:
                self.repo.git.add('.')
            
            # Commit changes
            commit = self.repo.index.commit(message)
            
            logger.info(f"💾 Committed changes: {commit.hexsha}")
            return commit.hexsha
            
        except Exception as e:
            logger.error(f"❌ Failed to commit changes: {e}")
            return None

class GitHubIntegration:
    """
    GitHub API integration for PR management
    """
    
    def __init__(self, token: str, repo_owner: str, repo_name: str):
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        logger.info(f"🐙 GitHub integration initialized: {repo_owner}/{repo_name}")
    
    async def create_pull_request(self, title: str, body: str, head: str, base: str = "main") -> Optional[Dict[str, Any]]:
        """Create a pull request"""
        
        try:
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls"
            data = {
                "title": title,
                "body": body,
                "head": head,
                "base": base
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code == 201:
                pr_data = response.json()
                logger.info(f"🔄 Created PR: #{pr_data['number']}")
                return pr_data
            
            logger.error(f"❌ PR creation failed: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to create PR: {e}")
            return None
    
    async def get_pull_requests(self, state: str = "open", limit: int = 10) -> List[Dict[str, Any]]:
        """Get pull requests"""
        
        try:
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls"
            params = {"state": state, "per_page": limit}
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                prs = response.json()
                logger.info(f"📋 Retrieved {len(prs)} pull requests")
                return prs
            
            logger.error(f"❌ Failed to get PRs: {response.text}")
            return []
            
        except Exception as e:
            logger.error(f"❌ Failed to get PRs: {e}")
            return []
    
    async def review_pull_request(self, pr_number: int, body: str, event: str = "COMMENT") -> bool:
        """Submit a PR review"""
        
        try:
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls/{pr_number}/reviews"
            data = {
                "body": body,
                "event": event  # APPROVE, REQUEST_CHANGES, COMMENT
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code == 200:
                logger.info(f"✅ Submitted PR review: #{pr_number}")
                return True
            
            logger.error(f"❌ PR review failed: {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to review PR: {e}")
            return False

class CodeAnalyzer:
    """
    Advanced code analyzer for quality and patterns
    """
    
    def __init__(self):
        self.language_patterns = {
            'python': {
                'extensions': ['.py'],
                'complexity_patterns': [
                    r'if\s+.*:',  # if statements
                    r'for\s+.*:',  # for loops
                    r'while\s+.*:',  # while loops
                    r'try\s*:',  # try blocks
                    r'except\s+.*:',  # except blocks
                ],
                'quality_indicators': {
                    'good': [r'def\s+test_', r'""".*"""', r'#\s+.*'],
                    'bad': [r'TODO:', r'FIXME:', r'XXX:', r'print\(']
                }
            },
            'javascript': {
                'extensions': ['.js', '.jsx', '.ts', '.tsx'],
                'complexity_patterns': [
                    r'if\s*\(',
                    r'for\s*\(',
                    r'while\s*\(',
                    r'try\s*\{',
                    r'catch\s*\(',
                ],
                'quality_indicators': {
                    'good': [r'test\(', r'/\*\*.*\*/', r'//\s+.*'],
                    'bad': [r'TODO:', r'FIXME:', r'console\.log\(']
                }
            }
        }
        
        logger.info("🔍 Code Analyzer initialized")
    
    async def analyze_file(self, file_path: str) -> Optional[CodeAnalysis]:
        """Analyze a single code file"""
        
        if not os.path.exists(file_path):
            logger.warning(f"⚠️ File not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Detect language
            language = self._detect_language(file_path)
            
            # Count lines of code
            lines = content.split('\n')
            loc = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
            
            # Calculate complexity
            complexity = self._calculate_complexity(content, language)
            
            # Identify issues
            issues = self._identify_issues(content, language)
            
            # Generate suggestions
            suggestions = self._generate_suggestions(content, language, issues)
            
            # Calculate maintainability
            maintainability = self._calculate_maintainability(content, language, complexity, len(issues))
            
            # Determine overall quality
            quality = self._determine_quality(complexity, len(issues), maintainability)
            
            analysis = CodeAnalysis(
                analysis_id=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                file_path=file_path,
                language=language,
                lines_of_code=loc,
                complexity_score=complexity,
                quality=quality,
                issues=issues,
                suggestions=suggestions,
                test_coverage=None,  # TODO: Implement test coverage detection
                dependencies=self._extract_dependencies(content, language),
                security_concerns=self._identify_security_concerns(content, language),
                performance_concerns=self._identify_performance_concerns(content, language),
                maintainability_score=maintainability,
                analyzed_at=datetime.now().isoformat()
            )
            
            logger.info(f"📊 Analyzed {file_path}: {quality.value} quality, {complexity:.1f} complexity")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze {file_path}: {e}")
            return None
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        
        ext = os.path.splitext(file_path)[1].lower()
        
        for language, config in self.language_patterns.items():
            if ext in config['extensions']:
                return language
        
        return 'unknown'
    
    def _calculate_complexity(self, content: str, language: str) -> float:
        """Calculate cyclomatic complexity"""
        
        if language not in self.language_patterns:
            return 1.0
        
        patterns = self.language_patterns[language]['complexity_patterns']
        complexity = 1  # Base complexity
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            complexity += len(matches)
        
        # Normalize by lines of code
        lines = len(content.split('\n'))
        return min(complexity / max(lines, 1) * 100, 20.0)  # Cap at 20
    
    def _identify_issues(self, content: str, language: str) -> List[Dict[str, Any]]:
        """Identify code issues"""
        
        issues = []
        lines = content.split('\n')
        
        # Generic issues
        for i, line in enumerate(lines, 1):
            line_content = line.strip()
            
            # Long lines
            if len(line) > 120:
                issues.append({
                    'type': 'style',
                    'severity': 'minor',
                    'line': i,
                    'message': 'Line too long (>120 characters)',
                    'suggestion': 'Consider breaking this line into multiple lines'
                })
            
            # TODO comments
            if 'TODO:' in line_content:
                issues.append({
                    'type': 'maintenance',
                    'severity': 'minor',
                    'line': i,
                    'message': 'TODO comment found',
                    'suggestion': 'Consider creating a task for this TODO'
                })
        
        # Language-specific issues
        if language in self.language_patterns:
            bad_patterns = self.language_patterns[language]['quality_indicators']['bad']
            for pattern in bad_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    issues.append({
                        'type': 'quality',
                        'severity': 'minor',
                        'line': line_num,
                        'message': f'Potentially problematic pattern: {pattern}',
                        'suggestion': 'Review this pattern for potential improvements'
                    })
        
        return issues
    
    def _generate_suggestions(self, content: str, language: str, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate improvement suggestions"""
        
        suggestions = []
        
        # Based on issues
        if len(issues) > 10:
            suggestions.append("Consider refactoring this file - it has many issues")
        
        # Based on size
        lines = len(content.split('\n'))
        if lines > 500:
            suggestions.append("Consider breaking this large file into smaller modules")
        
        # Language-specific suggestions
        if language == 'python':
            if 'class ' in content and 'def __init__' not in content:
                suggestions.append("Consider adding an __init__ method to your class")
            
            if 'def ' in content and '"""' not in content:
                suggestions.append("Consider adding docstrings to your functions")
        
        elif language == 'javascript':
            if 'function' in content and '/*' not in content:
                suggestions.append("Consider adding JSDoc comments to your functions")
        
        return suggestions
    
    def _calculate_maintainability(self, content: str, language: str, complexity: float, issue_count: int) -> float:
        """Calculate maintainability score (0-100)"""
        
        lines = len(content.split('\n'))
        
        # Base score
        score = 100.0
        
        # Penalize complexity
        score -= complexity * 2
        
        # Penalize issues
        score -= issue_count * 3
        
        # Penalize large files
        if lines > 1000:
            score -= (lines - 1000) * 0.01
        
        # Bonus for good practices
        if language in self.language_patterns:
            good_patterns = self.language_patterns[language]['quality_indicators']['good']
            for pattern in good_patterns:
                matches = len(re.findall(pattern, content, re.IGNORECASE))
                score += matches * 2
        
        return max(0, min(100, score))
    
    def _determine_quality(self, complexity: float, issue_count: int, maintainability: float) -> CodeQuality:
        """Determine overall code quality"""
        
        if maintainability >= 80 and complexity <= 5 and issue_count <= 3:
            return CodeQuality.EXCELLENT
        elif maintainability >= 60 and complexity <= 10 and issue_count <= 8:
            return CodeQuality.GOOD
        elif maintainability >= 40 and complexity <= 15 and issue_count <= 15:
            return CodeQuality.FAIR
        elif maintainability >= 20:
            return CodeQuality.POOR
        else:
            return CodeQuality.CRITICAL
    
    def _extract_dependencies(self, content: str, language: str) -> List[str]:
        """Extract dependencies from code"""
        
        dependencies = []
        
        if language == 'python':
            # Import statements
            import_patterns = [
                r'import\s+([^\s,]+)',
                r'from\s+([^\s]+)\s+import'
            ]
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                dependencies.extend(matches)
        
        elif language == 'javascript':
            # Import/require statements
            import_patterns = [
                r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]',
                r'require\([\'"]([^\'"]+)[\'"]\)'
            ]
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                dependencies.extend(matches)
        
        return list(set(dependencies))  # Remove duplicates
    
    def _identify_security_concerns(self, content: str, language: str) -> List[str]:
        """Identify potential security concerns"""
        
        concerns = []
        
        # Generic security patterns
        security_patterns = {
            'SQL Injection': [r'SELECT\s+.*\s+WHERE\s+.*\+', r'INSERT\s+.*\s+VALUES\s+.*\+'],
            'XSS': [r'innerHTML\s*=\s*.*\+', r'document\.write\s*\('],
            'Hardcoded Secrets': [r'password\s*=\s*[\'"][^\'"]+[\'"]', r'api_key\s*=\s*[\'"][^\'"]+[\'"]'],
            'Unsafe Eval': [r'eval\s*\(', r'exec\s*\(']
        }
        
        for concern_type, patterns in security_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    concerns.append(concern_type)
                    break
        
        return concerns
    
    def _identify_performance_concerns(self, content: str, language: str) -> List[str]:
        """Identify potential performance concerns"""
        
        concerns = []
        
        # Generic performance patterns
        if language == 'python':
            perf_patterns = {
                'Nested Loops': [r'for\s+.*:\s*.*for\s+.*:'],
                'Inefficient String Concat': [r'\+\s*=\s*.*\+'],
                'Global Variables': [r'global\s+\w+']
            }
        elif language == 'javascript':
            perf_patterns = {
                'Nested Loops': [r'for\s*\(.*\)\s*{.*for\s*\('],
                'DOM Queries in Loops': [r'for\s*\(.*document\.'],
                'Memory Leaks': [r'setInterval\s*\(', r'addEventListener\s*\(']
            }
        else:
            perf_patterns = {}
        
        for concern_type, patterns in perf_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                    concerns.append(concern_type)
                    break
        
        return concerns

class CodeGenerator:
    """
    AI-powered code generator
    """
    
    def __init__(self, ai_brain):
        self.ai_brain = ai_brain
        logger.info("🤖 Code Generator initialized")
    
    async def generate_code(self, requirement: str, language: str = "python", 
                          framework: Optional[str] = None) -> Optional[CodeGeneration]:
        """Generate code from requirements"""
        
        try:
            # Prepare the prompt
            prompt = self._build_generation_prompt(requirement, language, framework)
            
            # Generate code using AI
            if self.ai_brain.openai_client:
                response = await self._generate_with_openai(prompt)
            else:
                response = self._generate_mock_code(requirement, language)
            
            # Parse response
            generated_code, tests, documentation = self._parse_generation_response(response, language)
            
            # Assess quality
            quality = self._assess_generated_quality(generated_code, language)
            
            generation = CodeGeneration(
                generation_id=f"gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                requirement=requirement,
                language=language,
                framework=framework,
                generated_code=generated_code,
                tests=tests,
                documentation=documentation,
                confidence=0.8,  # TODO: Calculate actual confidence
                estimated_quality=quality,
                generated_at=datetime.now().isoformat()
            )
            
            logger.info(f"🤖 Generated code for: {requirement[:50]}...")
            return generation
            
        except Exception as e:
            logger.error(f"❌ Code generation failed: {e}")
            return None
    
    def _build_generation_prompt(self, requirement: str, language: str, framework: Optional[str]) -> str:
        """Build prompt for code generation"""
        
        framework_text = f" using {framework}" if framework else ""
        
        prompt = f"""
Generate high-quality {language} code{framework_text} for the following requirement:

Requirement: {requirement}

Please provide:
1. Clean, well-commented code
2. Unit tests
3. Brief documentation

Code should follow best practices and be production-ready.
        """.strip()
        
        return prompt
    
    async def _generate_with_openai(self, prompt: str) -> str:
        """Generate code using OpenAI"""
        
        try:
            response = await self.ai_brain.openai_client.chat.completions.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert software engineer. Generate clean, well-tested code."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"❌ OpenAI generation failed: {e}")
            return ""
    
    def _generate_mock_code(self, requirement: str, language: str) -> str:
        """Generate mock code for testing"""
        
        if language == "python":
            return f'''
# Generated code for: {requirement}

def main():
    """Main function for {requirement}"""
    # TODO: Implement {requirement}
    pass

if __name__ == "__main__":
    main()

# Tests
def test_main():
    """Test main function"""
    assert main() is None

# Documentation
"""
This module implements: {requirement}
"""
            '''.strip()
        
        elif language == "javascript":
            return f'''
// Generated code for: {requirement}

function main() {{
    // TODO: Implement {requirement}
}}

// Tests
function testMain() {{
    // Test main function
    console.assert(main() === undefined);
}}

// Documentation
/**
 * This module implements: {requirement}
 */
            '''.strip()
        
        return f"# Generated code for: {requirement}\n# TODO: Implement {requirement}"
    
    def _parse_generation_response(self, response: str, language: str) -> Tuple[str, str, str]:
        """Parse the generated response into code, tests, and docs"""
        
        # Simple parsing - in production, use more sophisticated parsing
        sections = response.split('\n\n')
        
        code = ""
        tests = ""
        documentation = ""
        
        for section in sections:
            if 'test' in section.lower():
                tests += section + '\n'
            elif 'doc' in section.lower() or 'comment' in section.lower():
                documentation += section + '\n'
            else:
                code += section + '\n'
        
        return code.strip(), tests.strip(), documentation.strip()
    
    def _assess_generated_quality(self, code: str, language: str) -> CodeQuality:
        """Assess the quality of generated code"""
        
        # Simple quality assessment
        if len(code) < 50:
            return CodeQuality.POOR
        
        # Check for good practices
        good_indicators = 0
        
        if 'def ' in code or 'function' in code:
            good_indicators += 1
        
        if '#' in code or '//' in code or '"""' in code:
            good_indicators += 1
        
        if 'TODO' not in code:
            good_indicators += 1
        
        if good_indicators >= 2:
            return CodeQuality.GOOD
        elif good_indicators >= 1:
            return CodeQuality.FAIR
        else:
            return CodeQuality.POOR

class CodeIntelligence:
    """
    Main Code Intelligence System
    Coordinates code analysis, generation, and automation
    """
    
    def __init__(self, ai_brain):
        self.ai_brain = ai_brain
        self.analyzer = CodeAnalyzer()
        self.generator = CodeGenerator(ai_brain)
        
        # Git integration
        self.git_integration = GitIntegration()
        
        # GitHub integration (if configured)
        self.github_integration = None
        if hasattr(Config, 'GITHUB_TOKEN') and hasattr(Config, 'GITHUB_REPO_OWNER'):
            self.github_integration = GitHubIntegration(
                Config.GITHUB_TOKEN,
                Config.GITHUB_REPO_OWNER, 
                Config.GITHUB_REPO_NAME
            )
        
        logger.info("💻 Code Intelligence System initialized")
    
    async def process_code_context(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process code context for AI brain"""
        
        processed_data = {
            'original_data': data,
            'code_type': self._classify_code_type(data),
            'complexity_assessment': self._assess_complexity(data),
            'quality_indicators': self._identify_quality_indicators(data),
            'automation_opportunities': self._identify_automation_opportunities(data),
            'processed_timestamp': datetime.now().isoformat()
        }
        
        return processed_data
    
    async def generate_code_actions(self, data: Dict[str, Any], insights: Dict[str, Any], 
                                  connections: List[Dict[str, Any]]) -> List:
        """Generate code-specific action recommendations"""
        
        actions = []
        
        # Code generation from requirements
        if data.get('requirements'):
            actions.append({
                'type': 'generate_code',
                'description': 'Generate code from requirements',
                'data': {'requirements': data['requirements']},
                'priority': 'high',
                'estimated_time': 30
            })
        
        # Code review automation
        if data.get('pull_request'):
            actions.append({
                'type': 'automated_review',
                'description': 'Perform automated code review',
                'data': {'pr_data': data['pull_request']},
                'priority': 'medium',
                'estimated_time': 15
            })
        
        # Refactoring suggestions
        if data.get('code_analysis') and data['code_analysis'].get('quality') == 'poor':
            actions.append({
                'type': 'refactor_suggestions',
                'description': 'Provide code refactoring suggestions',
                'data': {'analysis': data['code_analysis']},
                'priority': 'medium',
                'estimated_time': 20
            })
        
        return actions
    
    async def generate_code(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code from requirements"""
        
        requirement = step_data.get('requirement', 'No requirement specified')
        language = step_data.get('language', 'python')
        framework = step_data.get('framework')
        
        generation = await self.generator.generate_code(requirement, language, framework)
        
        if generation:
            return {
                'success': True,
                'generation': asdict(generation),
                'message': f'Generated {language} code for: {requirement[:50]}...'
            }
        else:
            return {
                'success': False,
                'message': 'Code generation failed'
            }
    
    async def create_file(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new code file"""
        
        file_path = step_data.get('file_path')
        content = step_data.get('content', '')
        
        if not file_path:
            return {'success': False, 'message': 'No file path specified'}
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"📄 Created file: {file_path}")
            return {
                'success': True,
                'file_path': file_path,
                'message': f'Created file: {file_path}'
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to create file {file_path}: {e}")
            return {'success': False, 'message': f'Failed to create file: {e}'}
    
    async def commit_changes(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Commit changes to git"""
        
        message = step_data.get('message', 'Automated commit')
        files = step_data.get('files')
        
        commit_hash = await self.git_integration.commit_changes(message, files)
        
        if commit_hash:
            return {
                'success': True,
                'commit_hash': commit_hash,
                'message': f'Committed changes: {commit_hash}'
            }
        else:
            return {'success': False, 'message': 'Failed to commit changes'}
    
    async def create_pull_request(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a pull request"""
        
        if not self.github_integration:
            return {'success': False, 'message': 'GitHub integration not configured'}
        
        title = step_data.get('title', 'Automated PR')
        body = step_data.get('body', 'Generated by AI Assistant')
        head = step_data.get('head_branch', 'feature/ai-generated')
        base = step_data.get('base_branch', 'main')
        
        pr_data = await self.github_integration.create_pull_request(title, body, head, base)
        
        if pr_data:
            return {
                'success': True,
                'pr_number': pr_data['number'],
                'pr_url': pr_data['html_url'],
                'message': f'Created PR #{pr_data["number"]}'
            }
        else:
            return {'success': False, 'message': 'Failed to create PR'}
    
    async def update_documentation(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update project documentation"""
        
        doc_type = step_data.get('type', 'README')
        content = step_data.get('content', '')
        
        # Simple documentation update
        if doc_type == 'README':
            file_path = 'README.md'
        else:
            file_path = f'docs/{doc_type}.md'
        
        return await self.create_file({'file_path': file_path, 'content': content})
    
    def _classify_code_type(self, data: Dict[str, Any]) -> str:
        """Classify the type of code change"""
        
        description = data.get('description', '').lower()
        
        if 'bug' in description or 'fix' in description:
            return 'bug_fix'
        elif 'test' in description:
            return 'test'
        elif 'refactor' in description:
            return 'refactor'
        elif 'feature' in description:
            return 'feature'
        elif 'doc' in description:
            return 'documentation'
        else:
            return 'unknown'
    
    def _assess_complexity(self, data: Dict[str, Any]) -> str:
        """Assess code complexity"""
        
        # Simple complexity assessment
        description = data.get('description', '').lower()
        
        high_complexity = ['architecture', 'refactor', 'migration', 'performance']
        medium_complexity = ['feature', 'api', 'integration']
        
        if any(keyword in description for keyword in high_complexity):
            return 'high'
        elif any(keyword in description for keyword in medium_complexity):
            return 'medium'
        else:
            return 'low'
    
    def _identify_quality_indicators(self, data: Dict[str, Any]) -> List[str]:
        """Identify code quality indicators"""
        
        indicators = []
        description = data.get('description', '').lower()
        
        quality_keywords = {
            'has_tests': ['test', 'testing', 'unit test'],
            'has_docs': ['documentation', 'readme', 'comments'],
            'follows_standards': ['lint', 'format', 'style'],
            'has_reviews': ['review', 'approved', 'lgtm']
        }
        
        for indicator, keywords in quality_keywords.items():
            if any(keyword in description for keyword in keywords):
                indicators.append(indicator)
        
        return indicators
    
    def _identify_automation_opportunities(self, data: Dict[str, Any]) -> List[str]:
        """Identify automation opportunities"""
        
        opportunities = []
        description = data.get('description', '').lower()
        
        automation_keywords = {
            'ci_cd': ['build', 'deploy', 'pipeline'],
            'testing': ['manual test', 'regression'],
            'code_review': ['review', 'approval'],
            'documentation': ['update docs', 'readme']
        }
        
        for opportunity, keywords in automation_keywords.items():
            if any(keyword in description for keyword in keywords):
                opportunities.append(opportunity)
        
        return opportunities
