from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .status import AnalysisStatus, FileStatus, NodeType, RelationshipType, ResolutionKind


class AnalyzerModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RepositoryMetadata(AnalyzerModel):
    source: str
    repository_url: str | None = None
    commit_sha: str | None = None


class ProjectSummary(AnalyzerModel):
    root: str = "."
    languages: list[str] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)


class FileRecord(AnalyzerModel):
    file_id: str
    relative_path: str
    extension: str
    language: str
    size: int
    content_hash: str
    status: FileStatus = FileStatus.PENDING
    parser_version: str | None = None


class ImportEvidence(AnalyzerModel):
    module: str
    line: int
    column: int


class ImportFact(AnalyzerModel):
    source_file: str
    module: str
    symbols: list[str] = Field(default_factory=list)
    relative_level: int = 0
    is_from_import: bool = False
    is_dynamic: bool = False
    evidence: ImportEvidence


class ResolvedImport(AnalyzerModel):
    source_file_id: str
    source_path: str
    module: str
    kind: ResolutionKind
    target_file_id: str | None = None
    target_path: str | None = None
    package_name: str | None = None
    ecosystem: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: ImportEvidence
    reason: str | None = None


class GraphNode(AnalyzerModel):
    id: str
    type: NodeType
    name: str
    path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(AnalyzerModel):
    id: str
    source: str
    target: str
    relationship_type: RelationshipType
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: ImportEvidence


class StructuredError(AnalyzerModel):
    file: str | None = None
    stage: str
    error_type: str
    message: str
    retryable: bool = False


class QualityMetrics(AnalyzerModel):
    files_total: int = 0
    files_eligible: int = 0
    files_analyzed: int = 0
    files_failed: int = 0
    files_unsupported: int = 0
    imports_found: int = 0
    imports_resolved: int = 0
    imports_unresolved: int = 0
    file_coverage: float = 0.0
    dependency_resolution_rate: float = 1.0


class AnalysisResult(AnalyzerModel):
    analyzer_version: str
    schema_version: str = "1.0.0"
    repository: RepositoryMetadata
    status: AnalysisStatus
    projects: list[ProjectSummary] = Field(default_factory=list)
    files: list[FileRecord] = Field(default_factory=list)
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    metrics: QualityMetrics = Field(default_factory=QualityMetrics)
    errors: list[StructuredError] = Field(default_factory=list)
    unresolved: list[ResolvedImport] = Field(default_factory=list)


class GraphOutput(AnalyzerModel):
    schema_version: str
    analyzer_version: str
    repository: RepositoryMetadata
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class ReportOutput(AnalyzerModel):
    schema_version: str
    analyzer_version: str
    repository: RepositoryMetadata
    status: AnalysisStatus
    projects: list[ProjectSummary]
    files: list[FileRecord]
    metrics: QualityMetrics


class ErrorsOutput(AnalyzerModel):
    schema_version: str
    analyzer_version: str
    repository: RepositoryMetadata
    errors: list[StructuredError]
    unresolved: list[ResolvedImport]

