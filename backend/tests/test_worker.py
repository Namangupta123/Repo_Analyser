from __future__ import annotations

from uuid import uuid4

from repo_analyzer.core.models import AnalysisResult, RepositoryMetadata, StructuredError
from repo_analyzer.core.status import AnalysisStatus as AnalyzerStatus

from systemlab_backend.models import AnalysisStatus
from systemlab_backend.repositories import QueueMessage
from systemlab_backend.worker import AnalysisWorker


class WorkerRepository:
    def __init__(self, status="QUEUED"):
        self.status = status
        self.archived = []
        self.completed = None
        self.failures = []

    def get_internal(self, analysis_id):
        return {"id": analysis_id, "status": self.status, "repository_url": "https://github.com/owner/repo"}

    def archive(self, message_id):
        self.archived.append(message_id)

    def mark_running(self, message):
        self.status = "RUNNING"

    def complete(self, message, **kwargs):
        self.completed = kwargs

    def record_infrastructure_failure(self, message, safe_message):
        self.failures.append((message, safe_message))


def result(status=AnalyzerStatus.COMPLETED):
    return AnalysisResult(
        analyzer_version="0.1.0",
        repository=RepositoryMetadata(
            source="https://github.com/owner/repo",
            repository_url="https://github.com/owner/repo",
            commit_sha="abc123",
        ),
        status=status,
    )


def test_worker_persists_canonical_envelopes() -> None:
    repository = WorkerRepository()
    worker = AnalysisWorker(repository, analyzer=lambda *_: result())
    worker.process(QueueMessage(10, 1, uuid4()))
    assert repository.completed["status"] == AnalysisStatus.COMPLETED
    assert repository.completed["graph"]["schema_version"] == "1.0.0"
    assert repository.completed["report"]["status"] == "COMPLETED"
    assert repository.completed["errors"]["errors"] == []


def test_analyzer_terminal_failure_is_persisted_not_retried() -> None:
    repository = WorkerRepository()
    failed = result(AnalyzerStatus.FAILED)
    failed.errors.append(StructuredError(stage="repository", error_type="CLONE_FAILED", message="safe"))
    AnalysisWorker(repository, analyzer=lambda *_: failed).process(QueueMessage(11, 1, uuid4()))
    assert repository.completed["status"] == AnalysisStatus.FAILED
    assert repository.failures == []


def test_unexpected_analyzer_error_uses_infrastructure_retry_path() -> None:
    repository = WorkerRepository()

    def broken(*_):
        raise RuntimeError("secret internal detail")

    message = QueueMessage(12, 2, uuid4())
    AnalysisWorker(repository, analyzer=broken).process(message)
    assert repository.completed is None
    assert repository.failures[0][0] == message
    assert "secret" not in repository.failures[0][1]


def test_duplicate_terminal_message_is_archived_without_analysis() -> None:
    repository = WorkerRepository(status="COMPLETED")
    called = False

    def analyzer(*_):
        nonlocal called
        called = True
        return result()

    AnalysisWorker(repository, analyzer=analyzer).process(QueueMessage(13, 2, uuid4()))
    assert repository.archived == [13]
    assert not called
