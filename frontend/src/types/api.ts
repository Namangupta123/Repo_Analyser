export type AnalysisStatus =
  | 'QUEUED'
  | 'RUNNING'
  | 'COMPLETED'
  | 'PARTIAL_SUCCESS'
  | 'LOW_CONFIDENCE'
  | 'FAILED'
  | 'TIMEOUT'
  | 'UNSUPPORTED';

export const terminalStatuses = new Set<AnalysisStatus>([
  'COMPLETED',
  'PARTIAL_SUCCESS',
  'LOW_CONFIDENCE',
  'FAILED',
  'TIMEOUT',
  'UNSUPPORTED',
]);

export interface User {
  id: string;
  email: string | null;
  display_name: string | null;
  avatar_url: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
  user: User;
}

export interface QualityMetrics {
  files_total?: number;
  files_eligible?: number;
  files_analyzed?: number;
  files_failed?: number;
  files_unsupported?: number;
  imports_found?: number;
  imports_resolved?: number;
  imports_unresolved?: number;
  file_coverage?: number;
  dependency_resolution_rate?: number;
  [key: string]: number | undefined;
}

export interface Analysis {
  id: string;
  repository_url: string;
  status: AnalysisStatus;
  commit_sha: string | null;
  analyzer_version: string | null;
  schema_version: string | null;
  metrics: QualityMetrics;
  attempt_count: number;
  failure_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
}

export interface AnalysisList {
  items: Analysis[];
  limit: number;
  offset: number;
}

export interface RepositoryMetadata {
  source: string;
  repository_url: string | null;
  commit_sha: string | null;
}

export interface GraphNode {
  id: string;
  type: 'file' | 'external_package';
  name: string;
  path: string | null;
  metadata: Record<string, unknown>;
}

export interface ImportEvidence {
  module: string;
  line: number;
  column: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship_type: 'IMPORTS' | 'USES_EXTERNAL_PACKAGE';
  confidence: number;
  evidence: ImportEvidence;
}

export interface GraphEnvelope {
  schema_version: string;
  analyzer_version: string;
  repository: RepositoryMetadata;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ProjectSummary {
  root: string;
  languages: string[];
  config_files: string[];
}

export interface ReportEnvelope {
  schema_version: string;
  analyzer_version: string;
  repository: RepositoryMetadata;
  status: AnalysisStatus;
  projects: ProjectSummary[];
  files: Array<Record<string, unknown>>;
  metrics: QualityMetrics;
}

export interface StructuredError {
  file: string | null;
  stage: string;
  error_type: string;
  message: string;
  retryable: boolean;
}

export interface UnresolvedImport {
  source_path: string;
  module: string;
  reason: string | null;
  evidence: ImportEvidence;
}

export interface ErrorsEnvelope {
  schema_version: string;
  analyzer_version: string;
  repository: RepositoryMetadata;
  errors: StructuredError[];
  unresolved: UnresolvedImport[];
}

export interface ApiErrorBody {
  detail?: {
    code?: string;
    message?: string;
  };
}
