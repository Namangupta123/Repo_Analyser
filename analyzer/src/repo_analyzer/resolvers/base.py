from __future__ import annotations

from pathlib import Path

from repo_analyzer.core.models import FileRecord, ImportFact, ResolvedImport

from .javascript import JavaScriptResolver
from .python import PythonResolver
from .typescript import TypeScriptAliases


class DependencyResolver:
    def __init__(self, root: Path, files: list[FileRecord], config_files: list[str]) -> None:
        aliases = TypeScriptAliases.load(root, config_files)
        self._javascript = JavaScriptResolver(files, aliases)
        self._python = PythonResolver.load(root, files, config_files)

    def resolve(self, fact: ImportFact, source: FileRecord) -> ResolvedImport:
        if fact.is_dynamic:
            return ResolvedImport(
                source_file_id=source.file_id,
                source_path=source.relative_path,
                module=fact.module,
                kind="UNRESOLVED",
                confidence=0.0,
                evidence=fact.evidence,
                reason="DYNAMIC_IMPORT",
            )
        if source.language == "python":
            return self._python.resolve(fact, source)
        return self._javascript.resolve(fact, source)

