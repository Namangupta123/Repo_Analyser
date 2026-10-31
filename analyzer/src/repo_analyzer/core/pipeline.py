from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from time import monotonic

from repo_analyzer.config import AnalyzerConfig
from repo_analyzer.extractors import extract_imports
from repo_analyzer.graph import build_graph
from repo_analyzer.metrics import calculate_metrics, terminal_status
from repo_analyzer.output import write_outputs
from repo_analyzer.parsers import JavaScriptParser, PythonParser
from repo_analyzer.repository import RepositoryManager
from repo_analyzer.resolvers import DependencyResolver
from repo_analyzer.scanner import RepositoryScanner

from .context import AnalysisContext
from .errors import AnalysisDeadlineExceeded, RepositoryTimeoutError
from .models import (
    AnalysisResult,
    ProjectSummary,
    RepositoryMetadata,
    ResolvedImport,
    StructuredError,
)
from .status import AnalysisStatus, FileStatus, ResolutionKind


ProgressCallback = Callable[[str, str], None]


class AnalysisPipeline:
    def __init__(
        self,
        *,
        config: AnalyzerConfig | None = None,
        progress: ProgressCallback | None = None,
        analyzer_version: str = "0.1.0",
    ) -> None:
        self.config = config or AnalyzerConfig()
        self.progress = progress or (lambda _stage, _detail: None)
        self.analyzer_version = analyzer_version

    def run(self, source: str, output_dir: Path, *, cleanup: bool = True) -> AnalysisResult:
        context = AnalysisContext(self.config)
        manager = RepositoryManager(self.config)
        try:
            handle = manager.prepare(source, cleanup=cleanup)
        except Exception as exc:
            status = AnalysisStatus.TIMEOUT if isinstance(exc, RepositoryTimeoutError) else AnalysisStatus.FAILED
            result = self._failed_result(source, status, "repository", exc)
            write_outputs(result, output_dir)
            return result

        self.progress("Preparing repository", handle.metadata.commit_sha or "local directory")
        try:
            with handle:
                context.check_deadline()
                scan = RepositoryScanner(self.config).scan(handle.root)
                self.progress("Scanning repository", f"{len(scan.files)} eligible files")

                projects = [ProjectSummary(
                    root=".",
                    languages=sorted({record.language for record in scan.files}),
                    config_files=scan.config_files,
                )]
                self.progress("Detecting projects", ", ".join(projects[0].languages) or "no supported source")

                facts_by_path: dict[str, list] = {}
                errors = list(scan.errors)
                python_parser = PythonParser()
                javascript_parser = JavaScriptParser()
                for record in scan.files:
                    context.check_deadline()
                    record.status = FileStatus.RUNNING
                    started = monotonic()
                    try:
                        parser = python_parser if record.language == "python" else javascript_parser
                        parsed = parser.parse(record.relative_path, scan.contents[record.relative_path])
                        if monotonic() - started > self.config.per_file_timeout_seconds:
                            raise TimeoutError("Per-file analysis deadline exceeded")
                        facts_by_path[record.relative_path] = extract_imports(parsed)
                        record.parser_version = parsed.parser_version
                        record.status = FileStatus.SUCCESS
                    except TimeoutError as exc:
                        record.status = FileStatus.TIMEOUT
                        errors.append(self._file_error(record.relative_path, "parsing", "TIMEOUT", exc))
                    except SyntaxError as exc:
                        record.status = FileStatus.FAILED
                        errors.append(self._file_error(record.relative_path, "parsing", "SYNTAX_ERROR", exc))
                    except Exception as exc:
                        record.status = FileStatus.FAILED
                        errors.append(self._file_error(record.relative_path, "parsing", type(exc).__name__.upper(), exc))
                self.progress("Parsing files", f"{sum(item.status == FileStatus.SUCCESS for item in scan.files)}/{len(scan.files)}")
                self.progress("Extracting imports", f"{sum(len(items) for items in facts_by_path.values())} imports")

                resolver = DependencyResolver(handle.root, scan.files, scan.config_files)
                records = {record.relative_path: record for record in scan.files}
                resolved: list[ResolvedImport] = []
                for path, facts in facts_by_path.items():
                    context.check_deadline()
                    source_record = records[path]
                    resolved.extend(resolver.resolve(fact, source_record) for fact in facts)
                unresolved = [item for item in resolved if item.kind == ResolutionKind.UNRESOLVED]
                self.progress("Resolving dependencies", f"{len(resolved) - len(unresolved)}/{len(resolved)}")

                nodes, edges = build_graph(scan.files, resolved)
                self.progress("Building graph", f"{len(nodes)} nodes, {len(edges)} edges")
                metrics = calculate_metrics(
                    files_total=scan.files_total,
                    files=scan.files,
                    resolved_imports=resolved,
                )
                status = terminal_status(metrics, low_confidence_threshold=self.config.low_confidence_threshold)
                result = AnalysisResult(
                    analyzer_version=self.analyzer_version,
                    repository=handle.metadata,
                    status=status,
                    projects=projects,
                    files=scan.files,
                    nodes=nodes,
                    edges=edges,
                    metrics=metrics,
                    errors=errors,
                    unresolved=unresolved,
                )
        except AnalysisDeadlineExceeded as exc:
            result = self._failed_result(source, AnalysisStatus.TIMEOUT, "pipeline", exc, handle.metadata)
        except Exception as exc:
            result = self._failed_result(source, AnalysisStatus.FAILED, "pipeline", exc, handle.metadata)

        write_outputs(result, output_dir)
        return result

    def _failed_result(
        self,
        source: str,
        status: AnalysisStatus,
        stage: str,
        exc: Exception,
        repository: RepositoryMetadata | None = None,
    ) -> AnalysisResult:
        return AnalysisResult(
            analyzer_version=self.analyzer_version,
            repository=repository or RepositoryMetadata(source=source),
            status=status,
            errors=[StructuredError(
                stage=stage,
                error_type=type(exc).__name__.upper(),
                message=str(exc),
                retryable=False,
            )],
        )

    @staticmethod
    def _file_error(path: str, stage: str, error_type: str, exc: Exception) -> StructuredError:
        return StructuredError(
            file=path,
            stage=stage,
            error_type=error_type,
            message=str(exc),
            retryable=False,
        )

