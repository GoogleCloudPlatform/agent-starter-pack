"""GitHub integration utilities for the Lighthouse auditor."""

import base64
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from github import Github, InputFileContent, Repository
from github.PullRequest import PullRequest


@dataclass
class CodeFix:
    """Represents a code fix to be applied."""
    file_path: str
    original_content: str
    fixed_content: str
    description: str
    issue_title: str


class GitHubIntegration:
    """Handles GitHub repository operations and pull request creation."""
    
    def __init__(self, token: str):
        """Initialize GitHub integration.
        
        Args:
            token: GitHub personal access token
        """
        self.github = Github(token)
        
    def get_repository(self, repo_name: str) -> Repository:
        """Get a GitHub repository by name.
        
        Args:
            repo_name: Repository name in format "owner/repo"
            
        Returns:
            GitHub Repository object
        """
        return self.github.get_repo(repo_name)
        
    def create_branch(self, repo: Repository, base_branch: str, new_branch: str) -> str:
        """Create a new branch in the repository.
        
        Args:
            repo: GitHub Repository object
            base_branch: Name of the base branch
            new_branch: Name of the new branch to create
            
        Returns:
            SHA of the new branch's HEAD
        """
        # Get the SHA of the base branch's HEAD
        base_sha = repo.get_branch(base_branch).commit.sha
        
        # Create the new branch
        ref = f"refs/heads/{new_branch}"
        repo.create_git_ref(ref=ref, sha=base_sha)
        
        return base_sha
        
    def get_file_content(self, repo: Repository, path: str, ref: Optional[str] = None) -> Tuple[str, str]:
        """Get the content and SHA of a file from the repository.
        
        Args:
            repo: GitHub Repository object
            path: Path to the file
            ref: Optional reference (branch, tag, or commit SHA)
            
        Returns:
            Tuple of (decoded content, file SHA)
        """
        content_file = repo.get_contents(path, ref=ref)
        content = base64.b64decode(content_file.content).decode('utf-8')
        return content, content_file.sha
        
    def update_file(
        self,
        repo: Repository,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: Optional[str] = None
    ) -> None:
        """Update a file in the repository.
        
        Args:
            repo: GitHub Repository object
            path: Path to the file
            content: New content
            message: Commit message
            branch: Branch to commit to
            sha: Optional SHA of the file to update
        """
        if sha is None:
            # Get the current file's SHA
            _, sha = self.get_file_content(repo, path, branch)
            
        repo.update_file(
            path=path,
            message=message,
            content=content,
            sha=sha,
            branch=branch
        )
        
    def create_pull_request(
        self,
        repo: Repository,
        title: str,
        body: str,
        head: str,
        base: str = "main",
        draft: bool = False
    ) -> PullRequest:
        """Create a pull request.
        
        Args:
            repo: GitHub Repository object
            title: PR title
            body: PR description
            head: Head branch
            base: Base branch
            draft: Whether to create as draft PR
            
        Returns:
            Created PullRequest object
        """
        return repo.create_pull(
            title=title,
            body=body,
            head=head,
            base=base,
            draft=draft
        )
        
    def apply_fixes(
        self,
        repo_name: str,
        fixes: List[CodeFix],
        base_branch: str = "main"
    ) -> PullRequest:
        """Apply fixes and create a pull request.
        
        Args:
            repo_name: Repository name (owner/repo)
            fixes: List of CodeFix objects
            base_branch: Base branch name
            
        Returns:
            Created PullRequest object
        """
        repo = self.get_repository(repo_name)
        
        # Create a new branch for the fixes
        branch_name = "lighthouse-fixes"
        self.create_branch(repo, base_branch, branch_name)
        
        # Apply each fix
        for fix in fixes:
            try:
                # Get current content and SHA
                current_content, sha = self.get_file_content(repo, fix.file_path, branch_name)
                
                # Update the file
                commit_message = f"Fix: {fix.issue_title}\n\n{fix.description}"
                self.update_file(
                    repo=repo,
                    path=fix.file_path,
                    content=fix.fixed_content,
                    message=commit_message,
                    branch=branch_name,
                    sha=sha
                )
            except Exception as e:
                print(f"Failed to apply fix to {fix.file_path}: {str(e)}")
                
        # Create pull request
        pr_title = "🚨 Lighthouse Performance Improvements"
        pr_body = self._generate_pr_description(fixes)
        
        return self.create_pull_request(
            repo=repo,
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=base_branch,
            draft=True  # Create as draft PR for review
        )
        
    def _generate_pr_description(self, fixes: List[CodeFix]) -> str:
        """Generate a detailed pull request description.
        
        Args:
            fixes: List of applied fixes
            
        Returns:
            Formatted PR description
        """
        description = [
            "# 🚨 Lighthouse Performance Improvements",
            "\nThis PR contains automated fixes for issues identified by Lighthouse audits.\n",
            "## 🔧 Changes Made\n"
        ]
        
        # Group fixes by file
        fixes_by_file: Dict[str, List[CodeFix]] = {}
        for fix in fixes:
            if fix.file_path not in fixes_by_file:
                fixes_by_file[fix.file_path] = []
            fixes_by_file[fix.file_path].append(fix)
            
        # Add details for each file
        for file_path, file_fixes in fixes_by_file.items():
            description.append(f"\n### 📄 `{file_path}`\n")
            for fix in file_fixes:
                description.extend([
                    f"- **{fix.issue_title}**",
                    f"  - {fix.description}\n"
                ])
                
        description.extend([
            "\n## 🔍 Review Notes",
            "- This PR was automatically generated by the Lighthouse Auditor",
            "- Please review the changes carefully before merging",
            "- Test the changes to ensure no regressions",
            "\n## 📊 Expected Improvements",
            "- Improved performance metrics",
            "- Better accessibility compliance",
            "- Enhanced SEO optimization"
        ])
        
        return "\n".join(description)
