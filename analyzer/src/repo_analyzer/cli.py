from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from repo_analyzer import __version__
from repo_analyzer.core.pipeline import AnalysisPipeline
from repo_analyzer.core.status import AnalysisStatus


STAGES = {
    "Preparing repository": 1,
    "Scanning repository": 2,
    "Detecting projects": 3,
    "Parsing files": 4,
    "Extracting imports": 5,
    "Resolving dependencies": 6,
    "Building graph": 7,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a file dependency graph for a source repository")
    parser.add_argument("source", help="Local repository path or public HTTPS GitHub URL")
    parser.add_argument("--output", type=Path, default=Path("analysis"), help="Output directory (default: ./analysis)")
    parser.add_argument("--keep-clone", action="store_true", help="Keep a temporary GitHub clone after analysis")
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print("Repository Analyzer\n")

    def progress(stage: str, detail: str) -> None:
        number = STAGES[stage]
        print(f"[{number}/7] {stage:<24} ✓ {detail}")

    result = AnalysisPipeline(progress=progress, analyzer_version=__version__).run(
        args.source,
        args.output,
        cleanup=not args.keep_clone,
    )
    print("\nAnalysis complete")
    print(f"Status: {result.status.value}")
    print(f"Files: {result.metrics.files_analyzed}/{result.metrics.files_eligible} analyzed")
    print(f"Dependencies: {result.metrics.imports_resolved}/{result.metrics.imports_found} resolved")
    print(f"Output: {args.output}")
    return 1 if result.status in {AnalysisStatus.FAILED, AnalysisStatus.TIMEOUT} else 0


if __name__ == "__main__":
    raise SystemExit(main())

