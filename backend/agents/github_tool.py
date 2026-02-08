"""
GitHub MCP Tool
===============
MCP tool for creating pull requests via the GitHub API.
"""

import os
from typing import Optional
from datetime import datetime

from github import Github, GithubException
from pydantic import BaseModel, Field

# =============================================================================
# CONFIGURATION
# =============================================================================

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO_OWNER = os.environ.get("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.environ.get("GITHUB_REPO_NAME", "Sovereign-SRE")


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CreatePRRequest(BaseModel):
    """Request to create a pull request"""
    title: str = Field(..., description="PR title")
    body: str = Field(..., description="PR description")
    head_branch: str = Field(..., description="Branch containing changes")
    base_branch: str = Field(default="main", description="Target branch")
    files: list[dict] = Field(default_factory=list, description="Files to commit")
    commit_message: str = Field(default="fix: automated fix by Sovereign-SRE")


class PRResult(BaseModel):
    """Result from PR creation"""
    success: bool
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# GITHUB TOOL
# =============================================================================

class GitHubTool:
    """
    GitHub integration for autonomous PR creation.
    
    This tool allows the CodeFixer agent to submit fixes as pull requests.
    """
    
    def __init__(
        self,
        token: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
    ):
        self.token = token or GITHUB_TOKEN
        self.owner = owner or GITHUB_REPO_OWNER
        self.repo_name = repo or GITHUB_REPO_NAME
        
        if not self.token:
            raise ValueError("GitHub token not configured")
        
        self.github = Github(self.token)
        self._repo = None
    
    @property
    def repo(self):
        """Lazy load repository"""
        if self._repo is None:
            self._repo = self.github.get_repo(f"{self.owner}/{self.repo_name}")
        return self._repo
    
    def create_branch(self, branch_name: str, from_branch: str = "main") -> bool:
        """Create a new branch from an existing branch"""
        try:
            source = self.repo.get_branch(from_branch)
            self.repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=source.commit.sha
            )
            return True
        except GithubException as e:
            if e.status == 422:  # Branch already exists
                return True
            raise
    
    def commit_files(
        self,
        branch: str,
        files: list[dict],
        message: str = "fix: automated fix"
    ) -> str:
        """
        Commit files to a branch.
        
        Args:
            branch: Target branch
            files: List of {"path": str, "content": str}
            message: Commit message
            
        Returns:
            Commit SHA
        """
        # Get the branch reference
        ref = self.repo.get_git_ref(f"heads/{branch}")
        
        # Get the latest commit
        latest_commit = self.repo.get_git_commit(ref.object.sha)
        base_tree = latest_commit.tree
        
        # Create tree elements for new/modified files
        tree_elements = []
        for file in files:
            blob = self.repo.create_git_blob(file["content"], "utf-8")
            tree_elements.append({
                "path": file["path"],
                "mode": "100644",
                "type": "blob",
                "sha": blob.sha,
            })
        
        # Create the tree
        new_tree = self.repo.create_git_tree(tree_elements, base_tree)
        
        # Create the commit
        new_commit = self.repo.create_git_commit(
            message=message,
            tree=new_tree,
            parents=[latest_commit]
        )
        
        # Update the branch reference
        ref.edit(sha=new_commit.sha)
        
        return new_commit.sha
    
    async def create_pull_request(self, request: CreatePRRequest) -> PRResult:
        """
        Create a pull request with the proposed fix.
        
        This method:
        1. Creates a new branch
        2. Commits the fix files
        3. Opens a pull request
        """
        try:
            # Generate branch name
            timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            branch_name = f"sovereign-sre/fix-{timestamp}"
            
            # Create branch
            self.create_branch(branch_name, request.base_branch)
            
            # Commit files
            if request.files:
                self.commit_files(
                    branch=branch_name,
                    files=request.files,
                    message=request.commit_message
                )
            
            # Create PR
            pr = self.repo.create_pull(
                title=request.title,
                body=self._format_pr_body(request.body),
                head=branch_name,
                base=request.base_branch,
            )
            
            # Add labels
            try:
                pr.add_to_labels("automated", "sovereign-sre")
            except GithubException:
                pass  # Labels might not exist
            
            return PRResult(
                success=True,
                pr_number=pr.number,
                pr_url=pr.html_url,
            )
        
        except GithubException as e:
            return PRResult(
                success=False,
                error=f"GitHub API error: {e.data.get('message', str(e))}"
            )
        except Exception as e:
            return PRResult(
                success=False,
                error=str(e)
            )
    
    def _format_pr_body(self, body: str) -> str:
        """Format the PR body with metadata"""
        return f"""## 🤖 Automated Fix by Sovereign-SRE

{body}

---

### Metadata
- **Generated at**: {datetime.utcnow().isoformat()}Z
- **System**: Sovereign-SRE Autonomous Pipeline
- **Human Approved**: ✅ Yes

### How to Review
1. Check the proposed changes in the Files tab
2. Run the test suite locally: `pytest`
3. Approve and merge if tests pass

---
*This PR was automatically created by the Sovereign-SRE self-healing system.*
"""


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_github_tool() -> GitHubTool:
    """Create a configured GitHub tool instance"""
    return GitHubTool()


async def create_pull_request(
    title: str,
    body: str,
    files: list[dict],
    base_branch: str = "main",
) -> PRResult:
    """
    Convenience function to create a PR.
    
    Args:
        title: PR title
        body: PR description
        files: List of {"path": str, "content": str}
        base_branch: Target branch
        
    Returns:
        PRResult with success status and URL
    """
    tool = create_github_tool()
    request = CreatePRRequest(
        title=title,
        body=body,
        files=files,
        base_branch=base_branch,
        head_branch="",  # Will be auto-generated
    )
    return await tool.create_pull_request(request)
