from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic

from repo_analyzer.config import AnalyzerConfig

from .errors import AnalysisDeadlineExceeded


@dataclass(slots=True)
class AnalysisContext:
    config: AnalyzerConfig
    started_at: float = field(default_factory=monotonic)

    def check_deadline(self) -> None:
        if monotonic() - self.started_at > self.config.analysis_timeout_seconds:
            raise AnalysisDeadlineExceeded("Analysis deadline exceeded")

