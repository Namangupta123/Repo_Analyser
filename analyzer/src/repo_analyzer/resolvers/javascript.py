from __future__ import annotations

import posixpath
from pathlib import PurePosixPath

from repo_analyzer.core.models import FileRecord, ImportFact, ResolvedImport

from .typescript import TypeScriptAliases


class JavaScriptResolver:
    EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")

    def __init__(self, files: list[FileRecord], aliases: TypeScriptAliases) -> None:
        self.files = {record.relative_path: record for record in files}
        self.aliases = aliases

    def resolve(self, fact: ImportFact, source: FileRecord) -> ResolvedImport:
        bases: list[str] = []
        if fact.module.startswith("."):
            parent = str(PurePosixPath(source.relative_path).parent)
            bases.append(posixpath.normpath(posixpath.join(parent, fact.module)))
        else:
            bases.extend(self.aliases.candidates(fact.module, source.relative_path))

        for base in bases:
            target = self._find(base)
            if target is not None:
                return self._local(fact, source, target)

        if fact.module.startswith((".", "/")) or bases:
            return self._unresolved(fact, source, "LOCAL_MODULE_NOT_FOUND")

        package = self._package_name(fact.module)
        return ResolvedImport(
            source_file_id=source.file_id,
            source_path=source.relative_path,
            module=fact.module,
            kind="EXTERNAL",
            package_name=package,
            ecosystem="npm",
            confidence=1.0,
            evidence=fact.evidence,
        )

    def _find(self, base: str) -> FileRecord | None:
        candidates = [base]
        if PurePosixPath(base).suffix not in self.EXTENSIONS:
            candidates.extend(base + extension for extension in self.EXTENSIONS)
            candidates.extend(posixpath.join(base, "index" + extension) for extension in self.EXTENSIONS)
        for candidate in candidates:
            if candidate in self.files:
                return self.files[candidate]
        return None

    @staticmethod
    def _package_name(module: str) -> str:
        parts = module.split("/")
        return "/".join(parts[:2]) if module.startswith("@") else parts[0]

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

