from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_IGNORE_DIRS = frozenset({
    ".git", ".next", ".venv", "__pycache__", "build",
    "coverage", "dist", "node_modules", "venv",
})
SOURCE_EXTENSIONS = frozenset({".py", ".js", ".jsx", ".ts", ".tsx"})
CONFIG_FILENAMES = frozenset({
    "package.json", "tsconfig.json", "pyproject.toml", "requirements.txt",
    "setup.py", "Dockerfile", "docker-compose.yml", "compose.yml",
})


@dataclass(frozen=True, slots=True)
class AnalyzerConfig:
    ignore_dirs: frozenset[str] = field(default_factory=lambda: DEFAULT_IGNORE_DIRS)
    max_file_size_bytes: int = 2 * 1024 * 1024
    clone_timeout_seconds: float = 120.0
    analysis_timeout_seconds: float = 600.0
    per_file_timeout_seconds: float = 10.0
    max_io_retries: int = 2
    low_confidence_threshold: float = 0.8

