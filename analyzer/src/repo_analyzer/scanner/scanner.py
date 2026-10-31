from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

from repo_analyzer.config import CONFIG_FILENAMES, SOURCE_EXTENSIONS, AnalyzerConfig
from repo_analyzer.core.models import FileRecord, StructuredError


LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:24]}"


@dataclass(slots=True)
class ScanResult:
    root: Path
    files_total: int = 0
    files: list[FileRecord] = field(default_factory=list)
    contents: dict[str, str] = field(default_factory=dict)
    config_files: list[str] = field(default_factory=list)
    errors: list[StructuredError] = field(default_factory=list)


class RepositoryScanner:
    def __init__(self, config: AnalyzerConfig | None = None) -> None:
        self.config = config or AnalyzerConfig()

    def scan(self, root: Path) -> ScanResult:
        root = root.resolve()
        result = ScanResult(root=root)
        for directory, dirnames, filenames in os.walk(root, followlinks=False):
            current = Path(directory)
            dirnames[:] = sorted(
                name for name in dirnames
                if name not in self.config.ignore_dirs and not (current / name).is_symlink()
            )
            for name in sorted(filenames):
                path = current / name
                result.files_total += 1
                relative = path.relative_to(root).as_posix()
                if self._is_config(name):
                    result.config_files.append(relative)
                if path.suffix.lower() not in SOURCE_EXTENSIONS:
                    continue
                self._scan_source(path, relative, root, result)
        result.files.sort(key=lambda item: item.relative_path)
        result.config_files.sort()
        return result

    @staticmethod
    def _is_config(name: str) -> bool:
        return (
            name in CONFIG_FILENAMES
            or name.startswith("vite.config.")
            or name.startswith("next.config.")
        )

    def _scan_source(self, path: Path, relative: str, root: Path, result: ScanResult) -> None:
        try:
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                result.errors.append(self._skip_error(relative, "UNSAFE_SYMLINK", "Symlink source files are not followed"))
                return
            size = path.stat().st_size
            if size > self.config.max_file_size_bytes:
                result.errors.append(self._skip_error(relative, "FILE_TOO_LARGE", f"File exceeds {self.config.max_file_size_bytes} bytes"))
                return
            data = path.read_bytes()
            if b"\x00" in data:
                result.errors.append(self._skip_error(relative, "BINARY_FILE", "Binary source file skipped"))
                return
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            result.errors.append(self._skip_error(relative, "MALFORMED_ENCODING", "Source file is not valid UTF-8"))
            return
        except (OSError, PermissionError) as exc:
            result.errors.append(StructuredError(
                file=relative,
                stage="scanning",
                error_type="IO_ERROR",
                message=str(exc),
                retryable=True,
            ))
            return

        extension = path.suffix.lower()
        result.files.append(FileRecord(
            file_id=stable_id("file", relative),
            relative_path=relative,
            extension=extension,
            language=LANGUAGES[extension],
            size=len(data),
            content_hash=hashlib.sha256(data).hexdigest(),
        ))
        result.contents[relative] = text

    @staticmethod
    def _skip_error(relative: str, error_type: str, message: str) -> StructuredError:
        return StructuredError(
            file=relative,
            stage="scanning",
            error_type=error_type,
            message=message,
            retryable=False,
        )

