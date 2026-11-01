import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { GraphExplorer } from '../components/GraphExplorer';
import { InlineError, LoadingState } from '../components/States';
import { StatusBadge } from '../components/StatusBadge';
import { repositoryName } from '../lib/api';
import type {
  Analysis,
  ErrorsEnvelope,
  GraphEnvelope,
  ReportEnvelope,
} from '../types/api';
import { terminalStatuses } from '../types/api';

type DetailTab = 'graph' | 'quality' | 'issues';

export function AnalysisDetailPage() {
  const { analysisId } = useParams();
  const { request } = useAuth();
  const navigate = useNavigate();
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [graph, setGraph] = useState<GraphEnvelope | null>(null);
  const [report, setReport] = useState<ReportEnvelope | null>(null);
  const [issues, setIssues] = useState<ErrorsEnvelope | null>(null);
  const [activeTab, setActiveTab] = useState<DetailTab>('graph');
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadArtifacts = useCallback(async () => {
    if (!analysisId) return;
    try {
      const [graphResult, reportResult, errorResult] = await Promise.all([
        request<GraphEnvelope>(`/api/v1/analyses/${analysisId}/graph`),
        request<ReportEnvelope>(`/api/v1/analyses/${analysisId}/report`),
        request<ErrorsEnvelope>(`/api/v1/analyses/${analysisId}/errors`),
      ]);
      setGraph(graphResult);
      setReport(reportResult);
      setIssues(errorResult);
      setError(null);
    } catch (artifactError) {
      setError(artifactError instanceof Error ? artifactError.message : 'Artifacts are unavailable.');
    }
  }, [analysisId, request]);

  const loadAnalysis = useCallback(async () => {
    if (!analysisId) return null;
    try {
      const result = await request<Analysis>(`/api/v1/analyses/${analysisId}`);
      setAnalysis(result);
      setError(null);
      return result;
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load this analysis.');
      return null;
    }
  }, [analysisId, request]);

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;

    const poll = async () => {
      const result = await loadAnalysis();
      if (cancelled || !result) return;
      if (terminalStatuses.has(result.status)) {
        await loadArtifacts();
      } else {
        timer = window.setTimeout(poll, 2500);
      }
    };

    void poll();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [loadAnalysis, loadArtifacts]);

  const deleteAnalysis = async () => {
    if (!analysisId || !analysis || !terminalStatuses.has(analysis.status)) return;
    const confirmed = window.confirm(`Delete the analysis for ${repositoryName(analysis.repository_url)}?`);
    if (!confirmed) return;
    setDeleting(true);
    try {
      await request<void>(`/api/v1/analyses/${analysisId}`, { method: 'DELETE' });
      navigate('/analyses', { replace: true });
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Could not delete this analysis.');
      setDeleting(false);
    }
  };

  if (!analysis && !error) {
    return <LoadingState label="Loading repository analysis" fullPage />;
  }

  if (!analysis) {
    return (
      <div className="page error-page">
        <InlineError message={error ?? 'Analysis not found.'} />
        <Link className="button button-secondary" to="/analyses">
          Back to repositories
        </Link>
      </div>
    );
  }

  const terminal = terminalStatuses.has(analysis.status);
  const metrics = report?.metrics ?? analysis.metrics;

  return (
    <div className="page detail-page">
      <div className="detail-breadcrumb">
        <Link to="/analyses">Repositories</Link>
        <span>/</span>
        <strong>{repositoryName(analysis.repository_url)}</strong>
      </div>

      <header className="detail-header">
        <div className="detail-title">
          <div className="repo-icon repo-icon-large" aria-hidden="true"><span /></div>
          <div>
            <div className="title-line">
              <h1>{repositoryName(analysis.repository_url)}</h1>
              <StatusBadge status={analysis.status} />
            </div>
            <a href={analysis.repository_url} target="_blank" rel="noreferrer">
              {analysis.repository_url.replace('https://github.com/', '')} ↗
            </a>
          </div>
        </div>
        <div className="detail-actions">
          <span className="commit-sha" title={analysis.commit_sha ?? 'Commit pending'}>
            commit {analysis.commit_sha?.slice(0, 8) ?? '—'}
          </span>
          {terminal && (
            <button className="button button-danger button-small" type="button" onClick={deleteAnalysis} disabled={deleting}>
              {deleting ? 'Deleting…' : 'Delete'}
            </button>
          )}
        </div>
      </header>

      {!terminal ? (
        <AnalysisProgress analysis={analysis} />
      ) : (
        <>
          <section className="metric-grid" aria-label="Analysis quality metrics">
            <MetricCard label="Files analyzed" value={formatNumber(metrics.files_analyzed)} detail={`of ${formatNumber(metrics.files_eligible)} eligible`} />
            <MetricCard label="File coverage" value={formatPercent(metrics.file_coverage)} detail="successfully analyzed" />
            <MetricCard label="Imports resolved" value={formatNumber(metrics.imports_resolved)} detail={`of ${formatNumber(metrics.imports_found)} found`} />
            <MetricCard label="Resolution rate" value={formatPercent(metrics.dependency_resolution_rate)} detail={`${formatNumber(metrics.imports_unresolved)} unresolved`} />
          </section>

          {analysis.failure_message && <InlineError message={analysis.failure_message} />}
          {error && <InlineError message={error} />}

          <div className="detail-tabs" role="tablist" aria-label="Analysis views">
            <TabButton active={activeTab === 'graph'} onClick={() => setActiveTab('graph')} label="Dependency graph" count={graph?.nodes.length} />
            <TabButton active={activeTab === 'quality'} onClick={() => setActiveTab('quality')} label="Quality report" />
            <TabButton active={activeTab === 'issues'} onClick={() => setActiveTab('issues')} label="Issues" count={(issues?.errors.length ?? 0) + (issues?.unresolved.length ?? 0)} />
          </div>

          <section className="detail-panel">
            {activeTab === 'graph' && (graph ? <GraphExplorer graph={graph} /> : <LoadingState label="Loading dependency graph" />)}
            {activeTab === 'quality' && <QualityPanel report={report} analysis={analysis} />}
            {activeTab === 'issues' && <IssuesPanel issues={issues} />}
          </section>
        </>
      )}
    </div>
  );
}

function AnalysisProgress({ analysis }: { analysis: Analysis }) {
  const running = analysis.status === 'RUNNING';
  return (
    <section className="progress-card">
      <div className="progress-orbit" aria-hidden="true"><span /><span /><span /></div>
      <div>
        <p className="eyebrow">Analysis in progress</p>
        <h2>{running ? 'Mapping repository relationships…' : 'Waiting for an analyzer worker…'}</h2>
        <p>
          {running
            ? 'The analyzer is scanning source files, extracting imports, and resolving dependencies.'
            : 'Your job is safely stored in the durable queue. This page updates automatically.'}
        </p>
        <div className="progress-track"><span className={running ? 'is-running' : ''} /></div>
        <small>Attempt {Math.max(analysis.attempt_count, 1)} · Safe to leave this page</small>
      </div>
    </section>
  );
}

function MetricCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function TabButton({ active, onClick, label, count }: { active: boolean; onClick: () => void; label: string; count?: number }) {
  return (
    <button className={active ? 'is-active' : ''} type="button" role="tab" aria-selected={active} onClick={onClick}>
      {label}
      {count !== undefined && <span>{count}</span>}
    </button>
  );
}

function QualityPanel({ report, analysis }: { report: ReportEnvelope | null; analysis: Analysis }) {
  if (!report) return <LoadingState label="Loading quality report" />;
  return (
    <div className="quality-panel">
      <div className="quality-summary">
        <p className="eyebrow">Analyzer verdict</p>
        <h2>{statusHeadline(analysis.status)}</h2>
        <p>The report is deterministic and tied to analyzer {report.analyzer_version} using schema {report.schema_version}.</p>
      </div>
      <div className="project-list">
        <h3>Detected projects</h3>
        {report.projects.map((project) => (
          <article key={`${project.root}-${project.languages.join('-')}`}>
            <code>{project.root}</code>
            <div>{project.languages.map((language) => <span key={language}>{language}</span>)}</div>
            <small>{project.config_files.length} configuration files</small>
          </article>
        ))}
      </div>
    </div>
  );
}

function IssuesPanel({ issues }: { issues: ErrorsEnvelope | null }) {
  if (!issues) return <LoadingState label="Loading issues" />;
  if (issues.errors.length === 0 && issues.unresolved.length === 0) {
    return <div className="issues-clear"><span>✓</span><h2>No reported issues</h2><p>Every extracted import was understood and every eligible file was processed.</p></div>;
  }
  return (
    <div className="issues-panel">
      {issues.errors.length > 0 && (
        <section>
          <h3>File and pipeline errors <span>{issues.errors.length}</span></h3>
          {issues.errors.map((issue, index) => (
            <article className="issue-row" key={`${issue.file}-${issue.stage}-${index}`}>
              <span className="issue-icon">!</span>
              <div><strong>{issue.error_type.replaceAll('_', ' ')}</strong><code>{issue.file ?? issue.stage}</code><p>{issue.message}</p></div>
            </article>
          ))}
        </section>
      )}
      {issues.unresolved.length > 0 && (
        <section>
          <h3>Unresolved imports <span>{issues.unresolved.length}</span></h3>
          {issues.unresolved.map((issue, index) => (
            <article className="issue-row" key={`${issue.source_path}-${issue.module}-${index}`}>
              <span className="issue-icon issue-icon-muted">?</span>
              <div><strong>{issue.module}</strong><code>{issue.source_path}:{issue.evidence.line}</code><p>{issue.reason ?? 'No deterministic target was found.'}</p></div>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}

function formatNumber(value: number | undefined) {
  return value === undefined ? '—' : new Intl.NumberFormat().format(value);
}

function formatPercent(value: number | undefined) {
  return value === undefined ? '—' : `${Math.round(value * 100)}%`;
}

function statusHeadline(status: Analysis['status']) {
  const headlines: Record<Analysis['status'], string> = {
    QUEUED: 'Queued for analysis', RUNNING: 'Analysis in progress', COMPLETED: 'Repository fully mapped',
    PARTIAL_SUCCESS: 'Useful graph with file-level gaps', LOW_CONFIDENCE: 'Graph built with resolution gaps',
    FAILED: 'Analysis could not complete', TIMEOUT: 'Analysis exceeded its deadline', UNSUPPORTED: 'Repository is not yet supported',
  };
  return headlines[status];
}
