from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb

from .config import Settings
from .database import Database
from .errors import BackendError, NotFoundError
from .models import ACTIVE_STATUSES, AnalysisStatus, TERMINAL_STATUSES


@dataclass(frozen=True)
class QueueMessage:
    message_id: int
    delivery_count: int
    analysis_id: UUID


class AnalysisRepository:
    def __init__(self, database: Database, settings: Settings) -> None:
        self.database = database
        self.settings = settings

    def ready(self) -> bool:
        return self.database.ready()

    def create_and_enqueue(self, user_id: UUID, repository_url: str) -> dict[str, Any]:
        analysis_id = uuid4()
        try:
            with self.database.connection() as connection, connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        insert into public.analyses (id, user_id, repository_url, status)
                        values (%s, %s, %s, 'QUEUED')
                        returning *
                        """,
                        (analysis_id, user_id, repository_url),
                    )
                    row = cursor.fetchone()
                    cursor.execute(
                        "select pgmq.send(%s, %s, 0)",
                        (self.settings.queue_name, Jsonb({"analysis_id": str(analysis_id)})),
                    )
            assert row is not None
            return row
        except UniqueViolation as exc:
            raise BackendError(
                status_code=409,
                code="ACTIVE_ANALYSIS_EXISTS",
                message="Finish the active analysis before submitting another repository.",
            ) from exc

    def list_for_user(self, user_id: UUID, limit: int, offset: int) -> list[dict[str, Any]]:
        with self.database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                select * from public.analyses
                where user_id = %s
                order by created_at desc
                limit %s offset %s
                """,
                (user_id, limit, offset),
            )
            return list(cursor.fetchall())

    def get_for_user(self, user_id: UUID, analysis_id: UUID) -> dict[str, Any]:
        with self.database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "select * from public.analyses where id = %s and user_id = %s",
                (analysis_id, user_id),
            )
            row = cursor.fetchone()
        if row is None:
            raise NotFoundError("Analysis not found.")
        return row

    def get_artifact_for_user(self, user_id: UUID, analysis_id: UUID, field: str) -> dict[str, Any]:
        if field not in {"graph", "report", "errors"}:
            raise ValueError("Invalid artifact field")
        analysis = self.get_for_user(user_id, analysis_id)
        if AnalysisStatus(analysis["status"]) not in TERMINAL_STATUSES:
            raise BackendError(409, "ANALYSIS_NOT_READY", "The analysis has not produced artifacts yet.")
        with self.database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"select {field} from public.analysis_artifacts where analysis_id = %s",
                (analysis_id,),
            )
            row = cursor.fetchone()
        if row is None:
            raise BackendError(409, "ANALYSIS_NOT_READY", "The analysis has no persisted artifacts.")
        return row[field]

    def delete_for_user(self, user_id: UUID, analysis_id: UUID) -> None:
        analysis = self.get_for_user(user_id, analysis_id)
        if AnalysisStatus(analysis["status"]) in ACTIVE_STATUSES:
            raise BackendError(409, "ANALYSIS_ACTIVE", "Queued or running analyses cannot be deleted.")
        with self.database.connection() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                "delete from public.analyses where id = %s and user_id = %s",
                (analysis_id, user_id),
            )

    def read_job(self) -> QueueMessage | None:
        with self.database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "select * from pgmq.read_with_poll(%s, %s, 1, %s, 100)",
                (
                    self.settings.queue_name,
                    self.settings.queue_visibility_seconds,
                    self.settings.queue_poll_seconds,
                ),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return QueueMessage(
            message_id=row["msg_id"],
            delivery_count=row["read_ct"],
            analysis_id=UUID(str(row["message"]["analysis_id"])),
        )

    def get_internal(self, analysis_id: UUID) -> dict[str, Any] | None:
        with self.database.connection() as connection, connection.cursor() as cursor:
            cursor.execute("select * from public.analyses where id = %s", (analysis_id,))
            return cursor.fetchone()

    def mark_running(self, message: QueueMessage) -> None:
        with self.database.connection() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                """
                update public.analyses
                set status = 'RUNNING', started_at = coalesce(started_at, now()),
                    attempt_count = greatest(attempt_count + 1, %s),
                    failure_message = null, updated_at = now()
                where id = %s and status in ('QUEUED', 'RUNNING')
                """,
                (message.delivery_count, message.analysis_id),
            )

    def complete(
        self,
        message: QueueMessage,
        *,
        status: AnalysisStatus,
        commit_sha: str | None,
        analyzer_version: str,
        schema_version: str,
        metrics: dict[str, Any],
        graph: dict[str, Any],
        report: dict[str, Any],
        errors: dict[str, Any],
        failure_message: str | None = None,
    ) -> None:
        with self.database.connection() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                """
                insert into public.analysis_artifacts (analysis_id, graph, report, errors)
                values (%s, %s, %s, %s)
                on conflict (analysis_id) do update
                set graph = excluded.graph, report = excluded.report, errors = excluded.errors,
                    updated_at = now()
                """,
                (message.analysis_id, Jsonb(graph), Jsonb(report), Jsonb(errors)),
            )
            cursor.execute(
                """
                update public.analyses
                set status = %s, commit_sha = %s, analyzer_version = %s,
                    schema_version = %s, metrics = %s, failure_message = %s,
                    completed_at = now(), updated_at = now()
                where id = %s
                """,
                (
                    status.value,
                    commit_sha,
                    analyzer_version,
                    schema_version,
                    Jsonb(metrics),
                    failure_message,
                    message.analysis_id,
                ),
            )
            self._archive(cursor, message.message_id)

    def archive(self, message_id: int) -> None:
        with self.database.connection() as connection, connection.transaction(), connection.cursor() as cursor:
            self._archive(cursor, message_id)

    def record_infrastructure_failure(self, message: QueueMessage, safe_message: str) -> None:
        terminal = message.delivery_count >= self.settings.queue_max_attempts
        with self.database.connection() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                """
                update public.analyses
                set status = %s, failure_message = %s,
                    completed_at = case when %s then now() else null end,
                    updated_at = now()
                where id = %s
                """,
                ("FAILED" if terminal else "QUEUED", safe_message, terminal, message.analysis_id),
            )
            if terminal:
                self._archive(cursor, message.message_id)

    def _archive(self, cursor: Any, message_id: int) -> None:
        cursor.execute("select pgmq.archive(%s, %s)", (self.settings.queue_name, message_id))
