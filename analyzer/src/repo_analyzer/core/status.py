from enum import StrEnum


class FileStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    UNSUPPORTED = "UNSUPPORTED"
    SKIPPED = "SKIPPED"
    TIMEOUT = "TIMEOUT"


class AnalysisStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    UNSUPPORTED = "UNSUPPORTED"


class ResolutionKind(StrEnum):
    LOCAL = "LOCAL"
    EXTERNAL = "EXTERNAL"
    UNRESOLVED = "UNRESOLVED"


class NodeType(StrEnum):
    FILE = "file"
    EXTERNAL_PACKAGE = "external_package"


class RelationshipType(StrEnum):
    IMPORTS = "IMPORTS"
    USES_EXTERNAL_PACKAGE = "USES_EXTERNAL_PACKAGE"

