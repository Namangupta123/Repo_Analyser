from pathlib import Path
import subprocess

import pytest

from repo_analyzer.core.errors import RepositoryValidationError
from repo_analyzer.repository import RepositoryManager


@pytest.mark.parametrize("url", [
    "http://github.com/a/b",
    "https://gitlab.com/a/b",
    "https://user:pass@github.com/a/b",
    "https://github.com/a/b?ref=main",
    "https://github.com/a/b/extra",
])
def test_rejects_invalid_github_urls(url: str) -> None:
    with pytest.raises(RepositoryValidationError):
        RepositoryManager.validate_github_url(url)


def test_accepts_and_normalizes_github_url() -> None:
    assert RepositoryManager.validate_github_url("https://github.com/openai/openai-python.git") == "https://github.com/openai/openai-python"


def test_local_git_metadata(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"], check=True)
    (tmp_path / "file.py").write_text("pass\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "file.py"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "fixture"], check=True)
    handle = RepositoryManager().prepare(str(tmp_path))
    assert handle.metadata.commit_sha
    assert handle.root == tmp_path.resolve()


def test_invalid_local_path() -> None:
    with pytest.raises(RepositoryValidationError):
        RepositoryManager().prepare("/definitely/not/a/repository")


def test_nested_non_repository_does_not_inherit_parent_git_metadata(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    nested = tmp_path / "fixture"
    nested.mkdir()
    handle = RepositoryManager().prepare(str(nested))
    assert handle.metadata.commit_sha is None
    assert handle.metadata.repository_url is None

