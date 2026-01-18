import os
import hashlib
from pathlib import Path
from git import Repo, InvalidGitRepositoryError
from app.core.config import get_settings

settings = get_settings()


class GitService:
    """Service for Git repository operations."""

    def __init__(self, repo_storage_path: str | None = None):
        self.storage_path = Path(repo_storage_path or settings.repo_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def get_repo_path(self, owner: str, name: str) -> Path:
        """Get local path for a repository."""
        return self.storage_path / owner / name

    def clone_or_pull(
        self, owner: str, name: str, github_token: str | None = None
    ) -> tuple[Repo, str, list[str]]:
        """Clone or pull a repository and return changed files.

        Returns:
            Tuple of (Repo, current_commit_hash, list of changed file paths)
        """
        repo_path = self.get_repo_path(owner, name)
        url = self._build_clone_url(owner, name, github_token)

        if repo_path.exists():
            return self._pull_repository(repo_path, url)
        else:
            return self._clone_repository(repo_path, url)

    def _build_clone_url(
        self, owner: str, name: str, github_token: str | None = None
    ) -> str:
        """Build clone URL with optional authentication."""
        if github_token:
            return f"https://{github_token}@github.com/{owner}/{name}.git"
        return f"https://github.com/{owner}/{name}.git"

    def _clone_repository(self, repo_path: Path, url: str) -> tuple[Repo, str, list[str]]:
        """Clone a new repository."""
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        repo = Repo.clone_from(url, repo_path)
        commit_hash = repo.head.commit.hexsha

        # All files are new
        changed_files = self._get_all_files(repo_path)
        return repo, commit_hash, changed_files

    def _pull_repository(self, repo_path: Path, url: str) -> tuple[Repo, str, list[str]]:
        """Pull updates from remote."""
        try:
            repo = Repo(repo_path)
        except InvalidGitRepositoryError:
            # Re-clone if corrupted
            import shutil
            shutil.rmtree(repo_path)
            return self._clone_repository(repo_path, url)

        old_commit = repo.head.commit.hexsha

        # Fetch and reset to latest
        origin = repo.remotes.origin
        origin.fetch()
        repo.head.reset(f"origin/{repo.active_branch.name}", index=True, working_tree=True)

        new_commit = repo.head.commit.hexsha

        # Get changed files
        if old_commit != new_commit:
            changed_files = self._get_changed_files(repo, old_commit, new_commit)
        else:
            changed_files = []

        return repo, new_commit, changed_files

    def _get_changed_files(self, repo: Repo, old_commit: str, new_commit: str) -> list[str]:
        """Get list of changed files between commits."""
        diff = repo.commit(old_commit).diff(repo.commit(new_commit))
        changed = set()
        for d in diff:
            if d.a_path:
                changed.add(d.a_path)
            if d.b_path:
                changed.add(d.b_path)
        return list(changed)

    def _get_all_files(self, repo_path: Path) -> list[str]:
        """Get all files in the repository."""
        files = []
        for root, _, filenames in os.walk(repo_path):
            # Skip .git directory
            if ".git" in root:
                continue
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, repo_path)
                files.append(rel_path)
        return files

    def get_file_content(self, owner: str, name: str, file_path: str) -> str:
        """Read file content from repository."""
        full_path = self.get_repo_path(owner, name) / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return full_path.read_text(encoding="utf-8", errors="replace")

    def get_file_hash(self, owner: str, name: str, file_path: str) -> str:
        """Calculate SHA-256 hash of file content."""
        content = self.get_file_content(owner, name, file_path)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
