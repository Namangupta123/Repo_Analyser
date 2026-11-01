import type { AnalysisStatus } from '../types/api';

const labels: Record<AnalysisStatus, string> = {
  QUEUED: 'Queued',
  RUNNING: 'Running',
  COMPLETED: 'Complete',
  PARTIAL_SUCCESS: 'Partial',
  LOW_CONFIDENCE: 'Low confidence',
  FAILED: 'Failed',
  TIMEOUT: 'Timed out',
  UNSUPPORTED: 'Unsupported',
};

export function StatusBadge({ status }: { status: AnalysisStatus }) {
  return (
    <span className={`status-badge status-${status.toLowerCase().replace('_', '-')}`}>
      <i aria-hidden="true" />
      {labels[status]}
    </span>
  );
}
