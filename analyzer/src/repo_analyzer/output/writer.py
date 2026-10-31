from __future__ import annotations

import json
from pathlib import Path

from repo_analyzer.core.models import ErrorsOutput, GraphOutput, ReportOutput, AnalysisResult


def write_outputs(result: AnalysisResult, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    graph = GraphOutput(
        schema_version=result.schema_version,
        analyzer_version=result.analyzer_version,
        repository=result.repository,
        nodes=result.nodes,
        edges=result.edges,
    )
    report = ReportOutput(
        schema_version=result.schema_version,
        analyzer_version=result.analyzer_version,
        repository=result.repository,
        status=result.status,
        projects=result.projects,
        files=result.files,
        metrics=result.metrics,
    )
    errors = ErrorsOutput(
        schema_version=result.schema_version,
        analyzer_version=result.analyzer_version,
        repository=result.repository,
        errors=result.errors,
        unresolved=result.unresolved,
    )
    _write(output_dir / "graph.json", graph.model_dump(mode="json"))
    _write(output_dir / "report.json", report.model_dump(mode="json"))
    _write(output_dir / "errors.json", errors.model_dump(mode="json"))


def _write(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

