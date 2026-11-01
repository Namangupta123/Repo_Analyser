import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { EmptyState, InlineError, LoadingState } from '../components/States';
import { StatusBadge } from '../components/StatusBadge';
import { ApiError, isPublicGitHubUrl, repositoryName } from '../lib/api';
import type { Analysis, AnalysisList } from '../types/api';

export function AnalysesPage() {
  const { request } = useAuth();
  const navigate = useNavigate();
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [repositoryUrl, setRepositoryUrl] = useState('');
  const [error, setError] = useState<string | null>(null);

  const loadAnalyses = useCallback(async () => {
    try {
      const response = await request<AnalysisList>('/api/v1/analyses?limit=50&offset=0');
      setAnalyses(response.items);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load analyses.');
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    void loadAnalyses();
  }, [loadAnalyses]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const normalized = repositoryUrl.trim();
    if (!isPublicGitHubUrl(normalized)) {
      setError('Enter an exact public GitHub URL, for example https://github.com/owner/repository.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const analysis = await request<Analysis>('/api/v1/analyses', {
        method: 'POST',
        body: JSON.stringify({ repository_url: normalized }),
      });
      navigate(`/analyses/${analysis.id}`);
    } catch (submitError) {
      if (submitError instanceof ApiError && submitError.code === 'ACTIVE_ANALYSIS_EXISTS') {
        setError('You already have an active analysis. Let it finish before submitting another.');
      } else {
        setError(submitError instanceof Error ? submitError.message : 'Could not queue the repository.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page analyses-page">
      <header className="page-header analyses-heading">
        <div>
          <p className="eyebrow">Repository workspace</p>
          <h1>Map a software system.</h1>
          <p>Submit a public GitHub repository and inspect its deterministic dependency graph.</p>
        </div>
        <div className="system-status">
          <span className="live-dot" />
          Analyzer ready
        </div>
      </header>

      <section className="submit-card">
        <div className="submit-card-copy">
          <span className="step-number">01</span>
          <div>
            <h2>Analyze a repository</h2>
            <p>Python, JavaScript, TypeScript, TSX, React and FastAPI are supported.</p>
          </div>
        </div>
        <form className="repository-form" onSubmit={submit}>
          <label htmlFor="repository-url">Public GitHub repository URL</label>
          <div className="repository-input-row">
            <span className="input-prefix" aria-hidden="true">
              git
            </span>
            <input
              id="repository-url"
              type="url"
              value={repositoryUrl}
              onChange={(event) => setRepositoryUrl(event.target.value)}
              placeholder="https://github.com/owner/repository"
              autoComplete="url"
              disabled={submitting}
            />
            <button className="button button-primary" type="submit" disabled={submitting}>
              {submitting ? 'Queuing…' : 'Build graph'}
              <span aria-hidden="true">→</span>
            </button>
          </div>
        </form>
        {error && <InlineError message={error} />}
      </section>

      <section className="history-section">
        <div className="section-heading">
          <div>
            <span className="step-number">02</span>
            <h2>Analysis history</h2>
          </div>
          <button className="button button-ghost button-small" type="button" onClick={loadAnalyses}>
            Refresh
          </button>
        </div>

        {loading ? (
          <LoadingState label="Loading repository history" />
        ) : analyses.length === 0 ? (
          <EmptyState
            eyebrow="Your workspace is clear"
            title="No repositories analyzed yet"
            description="Submit a public repository above. Its graph, quality report, and unresolved imports will appear here."
          />
        ) : (
          <div className="analysis-list">
            {analyses.map((analysis) => (
              <AnalysisRow key={analysis.id} analysis={analysis} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function AnalysisRow({ analysis }: { analysis: Analysis }) {
  const metrics = analysis.metrics;
  return (
    <Link className="analysis-row" to={`/analyses/${analysis.id}`}>
      <div className="repo-icon" aria-hidden="true">
        <span />
      </div>
      <div className="analysis-repository">
        <strong>{repositoryName(analysis.repository_url)}</strong>
        <span>{analysis.repository_url.replace('https://github.com/', '')}</span>
      </div>
      <StatusBadge status={analysis.status} />
      <div className="analysis-stat">
        <span>Files</span>
        <strong>{metrics.files_analyzed ?? '—'}</strong>
      </div>
      <div className="analysis-stat">
        <span>Resolution</span>
        <strong>{formatPercent(metrics.dependency_resolution_rate)}</strong>
      </div>
      <time dateTime={analysis.created_at}>{formatDate(analysis.created_at)}</time>
      <span className="row-arrow" aria-hidden="true">
        →
      </span>
    </Link>
  );
}

function formatPercent(value: number | undefined) {
  return value === undefined ? '—' : `${Math.round(value * 100)}%`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value));
}
