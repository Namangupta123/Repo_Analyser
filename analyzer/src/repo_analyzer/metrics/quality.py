from __future__ import annotations

from repo_analyzer.core.models import FileRecord, QualityMetrics, ResolvedImport
from repo_analyzer.core.status import AnalysisStatus, FileStatus, ResolutionKind


def calculate_metrics(
    *,
    files_total: int,
    files: list[FileRecord],
    resolved_imports: list[ResolvedImport],
) -> QualityMetrics:
    analyzed = sum(record.status == FileStatus.SUCCESS for record in files)
    failed = sum(record.status in {FileStatus.FAILED, FileStatus.TIMEOUT} for record in files)
    unsupported = sum(record.status == FileStatus.UNSUPPORTED for record in files)
    imports_found = len(resolved_imports)
    unresolved = sum(item.kind == ResolutionKind.UNRESOLVED for item in resolved_imports)
    resolved = imports_found - unresolved
    eligible = len(files)
    return QualityMetrics(
        files_total=files_total,
        files_eligible=eligible,
        files_analyzed=analyzed,
        files_failed=failed,
        files_unsupported=unsupported,
        imports_found=imports_found,
        imports_resolved=resolved,
        imports_unresolved=unresolved,
        file_coverage=analyzed / eligible if eligible else 0.0,
        dependency_resolution_rate=resolved / imports_found if imports_found else 1.0,
    )


def terminal_status(metrics: QualityMetrics, *, low_confidence_threshold: float) -> AnalysisStatus:
    if metrics.files_eligible == 0:
        return AnalysisStatus.UNSUPPORTED
    if metrics.files_analyzed == 0 and metrics.files_failed:
        return AnalysisStatus.FAILED
    if metrics.files_failed or metrics.files_unsupported:
        return AnalysisStatus.PARTIAL_SUCCESS
    if metrics.dependency_resolution_rate < low_confidence_threshold:
        return AnalysisStatus.LOW_CONFIDENCE
    return AnalysisStatus.COMPLETED

