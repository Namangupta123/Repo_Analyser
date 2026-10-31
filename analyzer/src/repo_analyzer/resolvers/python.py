from __future__ import annotations

import importlib.metadata
import posixpath
import re
import sys
import tomllib
from pathlib import Path, PurePosixPath

from repo_analyzer.core.models import FileRecord, ImportFact, ResolvedImport


class PythonResolver:
    DECLARED_IMPORT_ALIASES = {
        "pyjwt": "jwt",
        "python_multipart": "multipart",
    }

    def __init__(self, files: list[FileRecord], declared: set[str], recognizable: set[str]) -> None:
        self.files = {record.relative_path: record for record in files if record.extension == ".py"}
        normalized_declared = {_normalize_package(value) for value in declared}
        self.declared = normalized_declared | {
            import_name
            for distribution, import_name in self.DECLARED_IMPORT_ALIASES.items()
            if distribution in normalized_declared
        }
        self.recognizable = {_normalize_package(value) for value in recognizable}

    @classmethod
    def load(cls, root: Path, files: list[FileRecord], config_files: list[str]) -> PythonResolver:
        declared: set[str] = set()
        for relative in config_files:
            path = root / relative
            if path.name == "requirements.txt":
                declared.update(_requirements(path))
            elif path.name == "pyproject.toml":
                declared.update(_pyproject_dependencies(path))
        try:
            recognizable = set(importlib.metadata.packages_distributions())
        except Exception:
            recognizable = set()
        return cls(files, declared, recognizable)

    def resolve(self, fact: ImportFact, source: FileRecord) -> ResolvedImport:
        bases = self._module_bases(fact, source)
        for base in bases:
            target = self._find(base)
            if target is not None:
                return self._local(fact, source, target)

        top_level = fact.module.split(".", 1)[0] if fact.module else (fact.symbols[0] if fact.symbols else "")
        if fact.relative_level:
            return self._unresolved(fact, source, "RELATIVE_MODULE_NOT_FOUND")
        if top_level in sys.stdlib_module_names:
            return self._external(fact, source, top_level, "python-stdlib")
        normalized = _normalize_package(top_level)
        if normalized in self.declared or normalized in self.recognizable:
            return self._external(fact, source, top_level, "python")
        return self._unresolved(fact, source, "MODULE_NOT_FOUND")

    def _module_bases(self, fact: ImportFact, source: FileRecord) -> list[str]:
        module_path = fact.module.replace(".", "/")
        if fact.relative_level:
            parent = PurePosixPath(source.relative_path).parent
            for _ in range(max(0, fact.relative_level - 1)):
                parent = parent.parent
            if module_path:
                base = posixpath.normpath(posixpath.join(str(parent), module_path))
                submodules = [f"{base}/{symbol.replace('.', '/')}" for symbol in fact.symbols]
                return submodules + [base]
            return [posixpath.normpath(posixpath.join(str(parent), symbol.replace(".", "/"))) for symbol in fact.symbols]

        bases = []
        if module_path and fact.is_from_import:
            bases.extend(f"{module_path}/{symbol.replace('.', '/')}" for symbol in fact.symbols)
        if module_path:
            bases.append(module_path)
        if module_path:
            suffixes = (
                module_path + ".py",
                module_path + "/__init__.py",
            )
            matches = sorted(
                path for path in self.files
                if any(path == suffix[0:] or path.endswith("/" + suffix) for suffix in suffixes)
            )
            for match in matches:
                if match.endswith("/__init__.py"):
                    bases.append(match[:-12])
                elif match.endswith(".py"):
                    bases.append(match[:-3])
        return list(dict.fromkeys(bases))

    def _find(self, base: str) -> FileRecord | None:
        candidates = (base + ".py", base + "/__init__.py")
        for candidate in candidates:
            if candidate in self.files:
                return self.files[candidate]
        suffix_matches = sorted([
            record
            for path, record in self.files.items()
            if any(path.endswith("/" + candidate) for candidate in candidates)
        ], key=lambda record: record.relative_path)
        if len(suffix_matches) == 1:
            return suffix_matches[0]
        return None

    @staticmethod
    def _local(fact: ImportFact, source: FileRecord, target: FileRecord) -> ResolvedImport:
        return ResolvedImport(
            source_file_id=source.file_id,
            source_path=source.relative_path,
            module=fact.module,
            kind="LOCAL",
            target_file_id=target.file_id,
            target_path=target.relative_path,
            confidence=1.0,
            evidence=fact.evidence,
        )

    @staticmethod
    def _external(fact: ImportFact, source: FileRecord, package: str, ecosystem: str) -> ResolvedImport:
        return ResolvedImport(
            source_file_id=source.file_id,
            source_path=source.relative_path,
            module=fact.module,
            kind="EXTERNAL",
            package_name=package,
            ecosystem=ecosystem,
            confidence=1.0,
            evidence=fact.evidence,
        )

    @staticmethod
    def _unresolved(fact: ImportFact, source: FileRecord, reason: str) -> ResolvedImport:
        return ResolvedImport(
            source_file_id=source.file_id,
            source_path=source.relative_path,
            module=fact.module,
            kind="UNRESOLVED",
            confidence=0.0,
            evidence=fact.evidence,
            reason=reason,
        )


def _normalize_package(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def _requirements(path: Path) -> set[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return set()
    names: set[str] = set()
    for line in lines:
        value = line.split("#", 1)[0].strip()
        if not value or value.startswith(("-", "git+", "http:" , "https:")):
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)", value)
        if match:
            names.add(match.group(1))
    return names


def _pyproject_dependencies(path: Path) -> set[str]:
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return set()
    values = payload.get("project", {}).get("dependencies", [])
    names: set[str] = set()
    for value in values if isinstance(values, list) else []:
        if isinstance(value, str):
            match = re.match(r"([A-Za-z0-9_.-]+)", value)
            if match:
                names.add(match.group(1))
    groups = payload.get("dependency-groups", {})
    if isinstance(groups, dict):
        for group_values in groups.values():
            if not isinstance(group_values, list):
                continue
            for value in group_values:
                if isinstance(value, str):
                    match = re.match(r"([A-Za-z0-9_.-]+)", value.strip())
                    if match:
                        names.add(match.group(1))
    return names

