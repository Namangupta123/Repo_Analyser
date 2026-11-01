from __future__ import annotations

import logging
import signal
import tempfile
import time
from pathlib import Path
from types import FrameType
from typing import Callable

from repo_analyzer import AnalysisResult, analyze_repository
from repo_analyzer.core.models import ErrorsOutput, GraphOutput, ReportOutput

from .config import Settings, get_settings
from .database import Database
from .models import AnalysisStatus, TERMINAL_STATUSES
from .repositories import AnalysisRepository, QueueMessage


logger = logging.getLogger("systemlab_backend.worker")
Analyzer = Callable[[str, Path | None, bool], AnalysisResult]


class AnalysisWorker:
    def __init__(
        self,
        repository: AnalysisRepository,
        analyzer: Analyzer = analyze_repository,
    ) -> None:
        self.repository = repository
        self.analyzer = analyzer

    def process_next(self) -> bool:
        message = self.repository.read_job()
        if message is None:
            return False
        self.process(message)
        return True

    def process(self, message: QueueMessage) -> None:
        row = self.repository.get_internal(message.analysis_id)
        if row is None or AnalysisStatus(row["status"]) in TERMINAL_STATUSES:
            self.repository.archive(message.message_id)
            return

        try:
            self.repository.mark_running(message)
            with tempfile.TemporaryDirectory(prefix="systemlab-analysis-") as directory:
                result = self.analyzer(row["repository_url"], Path(directory), True)
            self._persist_result(message, result)
        except Exception:
            logger.exception("Infrastructure failure while processing analysis %s", message.analysis_id)
            self.repository.record_infrastructure_failure(
                message,
                "The analysis worker encountered an infrastructure failure.",
            )

    def _persist_result(self, message: QueueMessage, result: AnalysisResult) -> None:
        graph = GraphOutput(
            schema_version=result.schema_version,
            analyzer_version=result.analyzer_version,
            repository=result.repository,
            nodes=result.nodes,
            edges=result.edges,
        ).model_dump(mode="json")
        report = ReportOutput(
            schema_version=result.schema_version,
            analyzer_version=result.analyzer_version,
            repository=result.repository,
            status=result.status,
            projects=result.projects,
            files=result.files,
            metrics=result.metrics,
        ).model_dump(mode="json")
        errors = ErrorsOutput(
            schema_version=result.schema_version,
            analyzer_version=result.analyzer_version,
            repository=result.repository,
            errors=result.errors,
            unresolved=result.unresolved,
        ).model_dump(mode="json")
        status = AnalysisStatus(result.status.value)
        failure_message = None
        if status in {AnalysisStatus.FAILED, AnalysisStatus.TIMEOUT, AnalysisStatus.UNSUPPORTED}:
            failure_message = "The analyzer could not complete this repository. See errors for details."
        self.repository.complete(
            message,
            status=status,
            commit_sha=result.repository.commit_sha,
            analyzer_version=result.analyzer_version,
            schema_version=result.schema_version,
            metrics=result.metrics.model_dump(mode="json"),
            graph=graph,
            report=report,
            errors=errors,
            failure_message=failure_message,
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings: Settings = get_settings()
    database = Database(settings)
    repository = AnalysisRepository(database, settings)
    worker = AnalysisWorker(repository)
    stopping = False

    def stop(_: int, __: FrameType | None) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    database.open()
    logger.info("Worker started for queue %s", settings.queue_name)
    try:
        while not stopping:
            try:
                worker.process_next()
            except Exception:
                logger.exception("Queue polling failed")
                time.sleep(2)
    finally:
        database.close()
        logger.info("Worker stopped")


if __name__ == "__main__":
    main()
