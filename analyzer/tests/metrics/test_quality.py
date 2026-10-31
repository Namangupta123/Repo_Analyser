from repo_analyzer.core.models import FileRecord, ImportEvidence, ResolvedImport
from repo_analyzer.metrics import calculate_metrics, terminal_status


def _file(path: str, status: str = "SUCCESS") -> FileRecord:
    return FileRecord(
        file_id=path,
        relative_path=path,
        extension=".py",
        language="python",
        size=1,
        content_hash="0" * 64,
        status=status,
    )


def _resolution(kind: str) -> ResolvedImport:
    return ResolvedImport(
        source_file_id="a",
        source_path="a.py",
        module="x",
        kind=kind,
        confidence=1.0 if kind != "UNRESOLVED" else 0.0,
        evidence=ImportEvidence(module="x", line=1, column=1),
        reason="MODULE_NOT_FOUND" if kind == "UNRESOLVED" else None,
    )


def test_metrics_and_status_precedence() -> None:
    low = calculate_metrics(files_total=1, files=[_file("a.py")], resolved_imports=[_resolution("UNRESOLVED")])
    assert terminal_status(low, low_confidence_threshold=0.8) == "LOW_CONFIDENCE"

    partial = calculate_metrics(files_total=2, files=[_file("a.py"), _file("b.py", "FAILED")], resolved_imports=[])
    assert terminal_status(partial, low_confidence_threshold=0.8) == "PARTIAL_SUCCESS"

    failed = calculate_metrics(files_total=1, files=[_file("a.py", "FAILED")], resolved_imports=[])
    assert terminal_status(failed, low_confidence_threshold=0.8) == "FAILED"


def test_zero_import_rate_is_one() -> None:
    metrics = calculate_metrics(files_total=1, files=[_file("a.py")], resolved_imports=[])
    assert metrics.dependency_resolution_rate == 1.0
    assert terminal_status(metrics, low_confidence_threshold=0.8) == "COMPLETED"
