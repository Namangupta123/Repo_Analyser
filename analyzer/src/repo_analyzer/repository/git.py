from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from time import sleep
from urllib.parse import urlsplit

from repo_analyzer.config import AnalyzerConfig
from repo_analyzer.core.errors import (
    RepositoryOperationError,
    RepositoryTimeoutError,
    RepositoryValidationError,
)
from repo_analyzer.core.models import RepositoryMetadata


@dataclass(slots=True)
class RepositoryHandle:
    root: Path
    metadata: RepositoryMetadata
    temporary_root: Path | None = None
    cleanup_enabled: bool = True

    def cleanup(self) -> None:
        if self.cleanup_enabled and self.temporary_root is not None:
            shutil.rmtree(self.temporary_root, ignore_errors=True)

    def __enter__(self) -> RepositoryHandle:
        return self

    def __exit__(self, *_: object) -> None:
        self.cleanup()


class RepositoryManager:
    def __init__(self, config: AnalyzerConfig | None = None) -> None:
        self.config = config or AnalyzerConfig()

    def prepare(self, source: str, *, cleanup: bool = True) -> RepositoryHandle:
        if source.startswith(("http://", "https://")):
            return self._clone(source, cleanup=cleanup)
        return self._open_local(source)

    @staticmethod
    def validate_github_url(source: str) -> str:
        parsed = urlsplit(source)
        if parsed.scheme != "https" or parsed.hostname != "github.com":
            raise RepositoryValidationError("Only HTTPS github.com repository URLs are supported")
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.port:
            raise RepositoryValidationError("Credentials, ports, queries, and fragments are not allowed")
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) != 2:
            raise RepositoryValidationError("GitHub URL must have the form https://github.com/owner/repository")
        owner, repository = parts
        if repository.endswith(".git"):
            repository = repository[:-4]
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
        if not owner or not repository or not set(owner) <= allowed or not set(repository) <= allowed:
            raise RepositoryValidationError("GitHub owner or repository name is invalid")
        return f"https://github.com/{owner}/{repository}"

    def _clone(self, source: str, *, cleanup: bool) -> RepositoryHandle:
        normalized = self.validate_github_url(source)
        last_error = "clone failed"
        last_was_timeout = False
        for attempt in range(self.config.max_io_retries + 1):
            temporary_root = Path(tempfile.mkdtemp(prefix="repo-analyzer-"))
            repository_root = temporary_root / "repository"
            try:
                subprocess.run(
                    ["git", "clone", "--quiet", "--depth", "1", normalized, str(repository_root)],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=self.config.clone_timeout_seconds,
                )
                sha = self._git_value(repository_root, "rev-parse", "HEAD")
                return RepositoryHandle(
                    root=repository_root,
                    metadata=RepositoryMetadata(
                        source=source,
                        repository_url=normalized,
                        commit_sha=sha,
                    ),
                    temporary_root=temporary_root,
                    cleanup_enabled=cleanup,
                )
            except subprocess.TimeoutExpired as exc:
                last_was_timeout = True
                last_error = f"Repository clone timed out after {exc.timeout} seconds"
            except (OSError, subprocess.CalledProcessError) as exc:
                last_was_timeout = False
                stderr = getattr(exc, "stderr", None)
                last_error = (stderr or str(exc)).strip()
            shutil.rmtree(temporary_root, ignore_errors=True)
            if attempt < self.config.max_io_retries:
                sleep(0.1 * (attempt + 1))
        if last_was_timeout:
            raise RepositoryTimeoutError(last_error)
        raise RepositoryOperationError(last_error)

    def _open_local(self, source: str) -> RepositoryHandle:
        root = Path(source).expanduser()
        if not root.exists() or not root.is_dir():
            raise RepositoryValidationError(f"Local repository does not exist or is not a directory: {source}")
        root = root.resolve()
        git_root = self._git_value(root, "rev-parse", "--show-toplevel")
        is_repository_root = git_root is not None and Path(git_root).resolve() == root
        sha = self._git_value(root, "rev-parse", "HEAD") if is_repository_root else None
        remote = self._git_value(root, "config", "--get", "remote.origin.url") if is_repository_root else None
        return RepositoryHandle(
            root=root,
            metadata=RepositoryMetadata(source=source, repository_url=remote, commit_sha=sha),
            cleanup_enabled=False,
        )

    @staticmethod
    def _git_value(root: Path, *args: str) -> str | None:
        try:
            completed = subprocess.run(
                ["git", "-C", str(root), *args],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None
        value = completed.stdout.strip()
        return value or None

