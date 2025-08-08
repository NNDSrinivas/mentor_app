# patch_apply.py
from __future__ import annotations
from typing import List, Tuple, Optional
import os
import subprocess
import tempfile
from pathlib import Path

class PatchApplier:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        
    def parse_unified_diff(self, patch_content: str) -> List[Tuple[str, str, List[str]]]:
        """Parse unified diff format into file changes"""
        changes = []
        current_file = None
        current_old_path = None
        current_lines = []
        
        for line in patch_content.split('\n'):
            if line.startswith('--- '):
                if current_file and current_lines:
                    changes.append((current_old_path, current_file, current_lines))
                current_old_path = line[4:].strip()
                current_lines = []
            elif line.startswith('+++ '):
                current_file = line[4:].strip()
            elif line.startswith('@@') or line.startswith(' ') or line.startswith('+') or line.startswith('-'):
                if current_file:
                    current_lines.append(line)
                    
        if current_file and current_lines:
            changes.append((current_old_path, current_file, current_lines))
            
        return changes
    
    def create_branch(self, branch_name: str) -> bool:
        """Create new Git branch for patch application"""
        try:
            subprocess.run(['git', 'checkout', '-b', branch_name], 
                         cwd=self.repo_path, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def apply_patch_file(self, patch_content: str, file_path: str) -> bool:
        """Apply patch content to specific file"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
                f.write(patch_content)
                patch_file = f.name
            
            subprocess.run(['patch', '-p1', file_path, patch_file], 
                         cwd=self.repo_path, check=True, capture_output=True)
            
            os.unlink(patch_file)
            return True
        except (subprocess.CalledProcessError, OSError):
            return False
    
    def commit_changes(self, message: str) -> bool:
        """Commit applied changes"""
        try:
            subprocess.run(['git', 'add', '.'], cwd=self.repo_path, check=True)
            subprocess.run(['git', 'commit', '-m', message], 
                         cwd=self.repo_path, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def create_pull_request(self, branch_name: str, title: str, body: str = "") -> Optional[str]:
        """Create GitHub pull request (requires gh CLI)"""
        try:
            result = subprocess.run([
                'gh', 'pr', 'create', 
                '--title', title,
                '--body', body,
                '--head', branch_name
            ], cwd=self.repo_path, check=True, capture_output=True, text=True)
            
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    def apply_unified_diff(self, patch_content: str, branch_name: str, 
                          commit_message: str, pr_title: str) -> dict:
        """Full workflow: parse diff, create branch, apply patches, commit, create PR"""
        
        # Parse the unified diff
        changes = self.parse_unified_diff(patch_content)
        if not changes:
            return {"success": False, "error": "No valid changes found in patch"}
        
        # Create new branch
        if not self.create_branch(branch_name):
            return {"success": False, "error": f"Failed to create branch {branch_name}"}
        
        # Apply changes file by file
        failed_files = []
        for old_path, new_path, diff_lines in changes:
            file_patch = '\n'.join(diff_lines)
            if not self.apply_patch_file(file_patch, new_path):
                failed_files.append(new_path)
        
        if failed_files:
            return {"success": False, "error": f"Failed to apply patches to: {failed_files}"}
        
        # Commit changes
        if not self.commit_changes(commit_message):
            return {"success": False, "error": "Failed to commit changes"}
        
        # Create PR
        pr_url = self.create_pull_request(branch_name, pr_title, 
                                        f"Applied patch with {len(changes)} file changes")
        
        return {
            "success": True,
            "branch": branch_name,
            "files_changed": len(changes),
            "pr_url": pr_url
        }


def apply_patch(patch_content: str, branch_name: str = None, 
               commit_message: str = None, pr_title: str = None) -> dict:
    """Main entry point for patch application"""
    
    if not branch_name:
        branch_name = f"auto-patch-{os.urandom(4).hex()}"
    
    if not commit_message:
        commit_message = f"Apply automated patch changes"
    
    if not pr_title:
        pr_title = f"Automated patch application: {branch_name}"
    
    applier = PatchApplier()
    return applier.apply_unified_diff(patch_content, branch_name, commit_message, pr_title)
