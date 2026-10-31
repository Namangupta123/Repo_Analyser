class AnalyzerError(Exception):
    """Base exception for repository preparation failures."""


class RepositoryValidationError(AnalyzerError):
    """The supplied source is not an accepted repository source."""


class RepositoryOperationError(AnalyzerError):
    """A repository operation failed after bounded retries."""


class RepositoryTimeoutError(RepositoryOperationError):
    """A bounded repository operation timed out."""


class AnalysisDeadlineExceeded(AnalyzerError):
    """The configured analysis deadline has elapsed."""

