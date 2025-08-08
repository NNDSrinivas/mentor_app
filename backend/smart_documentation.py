"""
Smart Documentation Updates Module
AI-powered documentation system that auto-updates based on code changes and meeting discussions
"""

import asyncio
import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import sqlite3
import ast
import re
from dataclasses import dataclass
from pathlib import Path
import difflib
import git
from markdown import markdown
from bs4 import BeautifulSoup
import openai
from jinja2 import Template
import yaml

logger = logging.getLogger(__name__)

@dataclass
class DocumentationSection:
    """Represents a section of documentation"""
    section_id: str
    title: str
    content: str
    file_path: str
    line_start: int
    line_end: int
    last_updated: datetime
    auto_generated: bool
    dependencies: List[str]  # Files/functions this section depends on
    tags: List[str]

@dataclass
class CodeChange:
    """Represents a code change that might affect documentation"""
    file_path: str
    change_type: str  # 'added', 'modified', 'deleted'
    function_name: Optional[str]
    class_name: Optional[str]
    description: str
    diff_content: str
    timestamp: datetime

@dataclass
class MeetingInsight:
    """Insight from meeting that should update documentation"""
    insight_id: str
    content: str
    related_files: List[str]
    related_functions: List[str]
    action_type: str  # 'clarification', 'new_requirement', 'bug_fix', 'enhancement'
    priority: int
    timestamp: datetime

class CodeAnalyzer:
    """Analyze code changes for documentation impacts"""
    
    def __init__(self):
        self.repo = None
        self._init_git_repo()
    
    def _init_git_repo(self):
        """Initialize git repository connection"""
        try:
            self.repo = git.Repo(search_parent_directories=True)
            logger.info(f"Initialized git repo: {self.repo.working_dir}")
        except git.InvalidGitRepositoryError:
            logger.warning("No git repository found")
    
    def analyze_file_changes(self, file_path: str) -> List[CodeChange]:
        """Analyze changes in a specific file"""
        changes = []
        
        try:
            if not self.repo:
                return changes
            
            # Get recent commits for this file
            commits = list(self.repo.iter_commits(paths=file_path, max_count=5))
            
            if len(commits) >= 2:
                # Compare latest commit with previous
                latest_commit = commits[0]
                previous_commit = commits[1]
                
                # Get diff
                diff = self.repo.git.diff(
                    previous_commit.hexsha, 
                    latest_commit.hexsha, 
                    file_path
                )
                
                # Parse diff for function/class changes
                changes.extend(self._parse_diff_for_changes(file_path, diff, latest_commit))
            
        except Exception as e:
            logger.error(f"Error analyzing file changes for {file_path}: {e}")
        
        return changes
    
    def _parse_diff_for_changes(self, file_path: str, diff: str, commit) -> List[CodeChange]:
        """Parse git diff to identify specific code changes"""
        changes = []
        
        try:
            lines = diff.split('\n')
            current_function = None
            current_class = None
            
            for line in lines:
                if line.startswith('@@'):
                    # New hunk - reset context
                    current_function = None
                    current_class = None
                
                elif line.startswith('+') and not line.startswith('+++'):
                    # Added line - check if it's a function/class definition
                    clean_line = line[1:].strip()
                    
                    # Check for function definition
                    func_match = re.match(r'def\s+(\w+)\s*\(', clean_line)
                    if func_match:
                        current_function = func_match.group(1)
                        changes.append(CodeChange(
                            file_path=file_path,
                            change_type='added' if 'new file' in diff else 'modified',
                            function_name=current_function,
                            class_name=current_class,
                            description=f"Function '{current_function}' was modified/added",
                            diff_content=line,
                            timestamp=datetime.fromtimestamp(commit.committed_date)
                        ))
                    
                    # Check for class definition
                    class_match = re.match(r'class\s+(\w+)', clean_line)
                    if class_match:
                        current_class = class_match.group(1)
                        changes.append(CodeChange(
                            file_path=file_path,
                            change_type='added' if 'new file' in diff else 'modified',
                            function_name=None,
                            class_name=current_class,
                            description=f"Class '{current_class}' was modified/added",
                            diff_content=line,
                            timestamp=datetime.fromtimestamp(commit.committed_date)
                        ))
        
        except Exception as e:
            logger.error(f"Error parsing diff: {e}")
        
        return changes
    
    def analyze_ast_changes(self, file_path: str) -> List[Dict[str, Any]]:
        """Analyze Python file using AST to extract documentation metadata"""
        try:
            if not file_path.endswith('.py'):
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            metadata = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    metadata.append({
                        'type': 'function',
                        'name': node.name,
                        'docstring': ast.get_docstring(node),
                        'line_number': node.lineno,
                        'args': [arg.arg for arg in node.args.args],
                        'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list]
                    })
                
                elif isinstance(node, ast.ClassDef):
                    metadata.append({
                        'type': 'class',
                        'name': node.name,
                        'docstring': ast.get_docstring(node),
                        'line_number': node.lineno,
                        'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    })
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error analyzing AST for {file_path}: {e}")
            return []

class DocumentationGenerator:
    """Generate documentation content using AI"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
    
    async def generate_function_documentation(self, 
                                            function_info: Dict[str, Any],
                                            code_context: str) -> str:
        """Generate documentation for a function"""
        try:
            prompt = f"""
            Generate comprehensive documentation for this Python function:
            
            Function Name: {function_info.get('name', 'Unknown')}
            Arguments: {function_info.get('args', [])}
            Current Docstring: {function_info.get('docstring', 'None')}
            
            Code Context:
            ```python
            {code_context}
            ```
            
            Please provide:
            1. A clear description of what the function does
            2. Parameter descriptions with types
            3. Return value description
            4. Usage examples
            5. Any important notes or warnings
            
            Format as Markdown.
            """
            
            if self.openai_api_key:
                response = await openai.ChatCompletion.acreate(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a technical documentation expert."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1000,
                    temperature=0.3
                )
                
                return response.choices[0].message.content
            else:
                # Fallback to template-based generation
                return self._generate_template_documentation(function_info)
                
        except Exception as e:
            logger.error(f"Error generating function documentation: {e}")
            return self._generate_template_documentation(function_info)
    
    def _generate_template_documentation(self, function_info: Dict[str, Any]) -> str:
        """Generate documentation using templates when AI is not available"""
        template = Template("""
## {{ function_name }}

{{ description }}

### Parameters
{% for arg in args %}
- `{{ arg }}`: Description needed
{% endfor %}

### Returns
Return value description needed

### Example
```python
result = {{ function_name }}({{ args|join(', ') }})
```

### Notes
Additional notes and considerations.
        """)
        
        return template.render(
            function_name=function_info.get('name', 'Unknown'),
            description=function_info.get('docstring', 'Function description needed'),
            args=function_info.get('args', [])
        )
    
    async def update_documentation_with_meeting_insights(self, 
                                                        original_content: str,
                                                        insights: List[MeetingInsight]) -> str:
        """Update documentation based on meeting insights"""
        try:
            if not self.openai_api_key:
                return self._manual_insight_integration(original_content, insights)
            
            insights_text = "\n".join([
                f"- {insight.content} (Priority: {insight.priority}, Type: {insight.action_type})"
                for insight in insights
            ])
            
            prompt = f"""
            Update the following documentation based on new insights from team meetings:
            
            Original Documentation:
            {original_content}
            
            Meeting Insights:
            {insights_text}
            
            Please:
            1. Integrate relevant insights into the documentation
            2. Update any outdated information
            3. Add clarifications where needed
            4. Maintain the original structure and format
            5. Highlight any breaking changes or important updates
            
            Return the updated documentation in the same format.
            """
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a technical documentation expert helping maintain accurate and up-to-date documentation."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error updating documentation with insights: {e}")
            return self._manual_insight_integration(original_content, insights)
    
    def _manual_insight_integration(self, original_content: str, insights: List[MeetingInsight]) -> str:
        """Manually integrate insights when AI is not available"""
        # Add insights as a new section
        insights_section = "\n\n## Recent Updates from Team Discussions\n\n"
        
        for insight in sorted(insights, key=lambda x: x.priority, reverse=True):
            insights_section += f"- **{insight.action_type.title()}**: {insight.content}\n"
        
        return original_content + insights_section

class DocumentationManager:
    """Main documentation management system"""
    
    def __init__(self, docs_path: str = "docs", db_path: str = "data/documentation.db"):
        self.docs_path = Path(docs_path)
        self.db_path = db_path
        self.code_analyzer = CodeAnalyzer()
        self.doc_generator = DocumentationGenerator()
        
        self.docs_path.mkdir(exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize documentation tracking database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Documentation sections table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS doc_sections (
                    section_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    file_path TEXT,
                    line_start INTEGER,
                    line_end INTEGER,
                    last_updated TEXT,
                    auto_generated BOOLEAN,
                    dependencies TEXT,
                    tags TEXT
                )
            ''')
            
            # Code changes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS code_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT,
                    change_type TEXT,
                    function_name TEXT,
                    class_name TEXT,
                    description TEXT,
                    timestamp TEXT,
                    processed BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Meeting insights table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS meeting_insights (
                    insight_id TEXT PRIMARY KEY,
                    content TEXT,
                    related_files TEXT,
                    related_functions TEXT,
                    action_type TEXT,
                    priority INTEGER,
                    timestamp TEXT,
                    processed BOOLEAN DEFAULT FALSE
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error initializing documentation database: {e}")
    
    async def process_code_changes(self, file_paths: List[str]) -> Dict[str, Any]:
        """Process code changes and update documentation"""
        results = {
            "files_processed": 0,
            "sections_updated": 0,
            "new_sections": 0,
            "errors": []
        }
        
        try:
            for file_path in file_paths:
                try:
                    # Analyze changes
                    changes = self.code_analyzer.analyze_file_changes(file_path)
                    ast_metadata = self.code_analyzer.analyze_ast_changes(file_path)
                    
                    # Store changes in database
                    self._store_code_changes(changes)
                    
                    # Update documentation for functions/classes
                    for metadata in ast_metadata:
                        await self._update_documentation_for_code_element(file_path, metadata)
                    
                    results["files_processed"] += 1
                    
                except Exception as e:
                    error_msg = f"Error processing {file_path}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in process_code_changes: {e}")
            results["errors"].append(str(e))
            return results
    
    async def _update_documentation_for_code_element(self, file_path: str, metadata: Dict[str, Any]):
        """Update documentation for a specific code element"""
        try:
            element_name = metadata['name']
            element_type = metadata['type']
            
            # Generate section ID
            section_id = f"{file_path}#{element_type}#{element_name}"
            
            # Read current file content for context
            with open(file_path, 'r', encoding='utf-8') as f:
                code_context = f.read()
            
            # Generate new documentation
            new_content = await self.doc_generator.generate_function_documentation(
                metadata, code_context
            )
            
            # Create or update documentation section
            section = DocumentationSection(
                section_id=section_id,
                title=f"{element_type.title()}: {element_name}",
                content=new_content,
                file_path=file_path,
                line_start=metadata.get('line_number', 0),
                line_end=metadata.get('line_number', 0),
                last_updated=datetime.now(),
                auto_generated=True,
                dependencies=[file_path],
                tags=[element_type, 'auto-generated']
            )
            
            self._save_documentation_section(section)
            
            # Generate markdown file
            await self._generate_markdown_file(file_path)
            
        except Exception as e:
            logger.error(f"Error updating documentation for {metadata}: {e}")
    
    async def process_meeting_insights(self, insights: List[MeetingInsight]) -> Dict[str, Any]:
        """Process meeting insights and update relevant documentation"""
        results = {
            "insights_processed": 0,
            "sections_updated": 0,
            "errors": []
        }
        
        try:
            # Store insights in database
            self._store_meeting_insights(insights)
            
            # Group insights by related files
            file_insights = {}
            for insight in insights:
                for file_path in insight.related_files:
                    if file_path not in file_insights:
                        file_insights[file_path] = []
                    file_insights[file_path].append(insight)
            
            # Update documentation for each file
            for file_path, file_specific_insights in file_insights.items():
                await self._update_documentation_with_insights(file_path, file_specific_insights)
                results["sections_updated"] += 1
            
            results["insights_processed"] = len(insights)
            
        except Exception as e:
            logger.error(f"Error processing meeting insights: {e}")
            results["errors"].append(str(e))
        
        return results
    
    async def _update_documentation_with_insights(self, file_path: str, insights: List[MeetingInsight]):
        """Update documentation for a file based on meeting insights"""
        try:
            # Get existing documentation sections for this file
            sections = self._get_documentation_sections_for_file(file_path)
            
            for section in sections:
                # Update content with insights
                updated_content = await self.doc_generator.update_documentation_with_meeting_insights(
                    section.content, insights
                )
                
                # Update section
                section.content = updated_content
                section.last_updated = datetime.now()
                self._save_documentation_section(section)
            
            # Regenerate markdown file
            await self._generate_markdown_file(file_path)
            
        except Exception as e:
            logger.error(f"Error updating documentation with insights for {file_path}: {e}")
    
    async def _generate_markdown_file(self, file_path: str):
        """Generate markdown documentation file"""
        try:
            sections = self._get_documentation_sections_for_file(file_path)
            
            if not sections:
                return
            
            # Create markdown content
            markdown_content = f"# Documentation for {file_path}\n\n"
            markdown_content += f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
            
            for section in sections:
                markdown_content += f"## {section.title}\n\n"
                markdown_content += f"{section.content}\n\n"
                
                if section.auto_generated:
                    markdown_content += "*This section was auto-generated based on code analysis.*\n\n"
            
            # Save to docs directory
            doc_file_path = self.docs_path / f"{Path(file_path).stem}_docs.md"
            with open(doc_file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Generated documentation file: {doc_file_path}")
            
        except Exception as e:
            logger.error(f"Error generating markdown file for {file_path}: {e}")
    
    def _store_code_changes(self, changes: List[CodeChange]):
        """Store code changes in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for change in changes:
                cursor.execute('''
                    INSERT INTO code_changes 
                    (file_path, change_type, function_name, class_name, description, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    change.file_path,
                    change.change_type,
                    change.function_name,
                    change.class_name,
                    change.description,
                    change.timestamp.isoformat()
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing code changes: {e}")
    
    def _store_meeting_insights(self, insights: List[MeetingInsight]):
        """Store meeting insights in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for insight in insights:
                cursor.execute('''
                    INSERT OR REPLACE INTO meeting_insights 
                    (insight_id, content, related_files, related_functions, action_type, priority, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    insight.insight_id,
                    insight.content,
                    json.dumps(insight.related_files),
                    json.dumps(insight.related_functions),
                    insight.action_type,
                    insight.priority,
                    insight.timestamp.isoformat()
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing meeting insights: {e}")
    
    def _save_documentation_section(self, section: DocumentationSection):
        """Save documentation section to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO doc_sections 
                (section_id, title, content, file_path, line_start, line_end, 
                 last_updated, auto_generated, dependencies, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                section.section_id,
                section.title,
                section.content,
                section.file_path,
                section.line_start,
                section.line_end,
                section.last_updated.isoformat(),
                section.auto_generated,
                json.dumps(section.dependencies),
                json.dumps(section.tags)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving documentation section: {e}")
    
    def _get_documentation_sections_for_file(self, file_path: str) -> List[DocumentationSection]:
        """Get all documentation sections for a file"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM doc_sections WHERE file_path = ?
            ''', (file_path,))
            
            rows = cursor.fetchall()
            sections = []
            
            for row in rows:
                section = DocumentationSection(
                    section_id=row[0],
                    title=row[1],
                    content=row[2],
                    file_path=row[3],
                    line_start=row[4],
                    line_end=row[5],
                    last_updated=datetime.fromisoformat(row[6]),
                    auto_generated=bool(row[7]),
                    dependencies=json.loads(row[8]) if row[8] else [],
                    tags=json.loads(row[9]) if row[9] else []
                )
                sections.append(section)
            
            conn.close()
            return sections
            
        except Exception as e:
            logger.error(f"Error getting documentation sections for {file_path}: {e}")
            return []
    
    async def generate_project_overview(self) -> str:
        """Generate comprehensive project documentation overview"""
        try:
            # Get all documentation sections
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM doc_sections')
            all_sections = cursor.fetchall()
            conn.close()
            
            # Generate overview
            overview = "# Project Documentation Overview\n\n"
            overview += f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
            
            # Group by file
            files = {}
            for section in all_sections:
                file_path = section[3]
                if file_path not in files:
                    files[file_path] = []
                files[file_path].append(section)
            
            for file_path, sections in files.items():
                overview += f"## {file_path}\n\n"
                overview += f"**Sections: {len(sections)}**\n\n"
                
                for section in sections:
                    overview += f"- {section[1]}\n"
                
                overview += "\n"
            
            # Save overview
            overview_path = self.docs_path / "README.md"
            with open(overview_path, 'w', encoding='utf-8') as f:
                f.write(overview)
            
            return overview
            
        except Exception as e:
            logger.error(f"Error generating project overview: {e}")
            return f"Error generating overview: {e}"

# Initialize global documentation manager
documentation_manager = DocumentationManager()

if __name__ == "__main__":
    # Test the documentation system
    async def test_documentation():
        manager = DocumentationManager()
        
        # Test processing code changes
        test_files = ["app/ai_assistant.py", "app/transcription.py"]
        result = await manager.process_code_changes(test_files)
        print(f"Code processing result: {json.dumps(result, indent=2)}")
        
        # Test meeting insights
        insights = [
            MeetingInsight(
                insight_id="insight_1",
                content="Need to add error handling to the transcription service",
                related_files=["app/transcription.py"],
                related_functions=["transcribe_audio"],
                action_type="enhancement",
                priority=8,
                timestamp=datetime.now()
            )
        ]
        
        insight_result = await manager.process_meeting_insights(insights)
        print(f"Insight processing result: {json.dumps(insight_result, indent=2)}")
        
        # Generate project overview
        overview = await manager.generate_project_overview()
        print(f"Project overview generated: {len(overview)} characters")
    
    # Run test
    asyncio.run(test_documentation())
