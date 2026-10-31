from __future__ import annotations

from pathlib import Path

from .core.models import AnalysisResult

__version__ = "0.1.0"


def analyze_repository(
    source: str,
    output_dir: Path | None = None,
    cleanup: bool = True,
) -> AnalysisResult:
    from .core.pipeline import AnalysisPipeline

    return AnalysisPipeline(analyzer_version=__version__).run(
        source,
        Path("analysis") if output_dir is None else Path(output_dir),
        cleanup=cleanup,
    )


__all__ = ["AnalysisResult", "analyze_repository", "__version__"]

