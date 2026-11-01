import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export function LandingPage() {
  const { state, login } = useAuth();

  if (state === 'authenticated') {
    return <Navigate to="/analyses" replace />;
  }

  return (
    <main className="landing">
      <nav className="landing-nav">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          <span>SystemLab</span>
          <em>v0</em>
        </div>
        <span className="landing-nav-note">Repository intelligence, made visible.</span>
      </nav>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Understand the system before you touch it</p>
          <h1>
            Turn source code into a <span>living map.</span>
          </h1>
          <p className="hero-description">
            SystemLab analyzes a public repository, resolves its file dependencies, and gives your
            team an interactive graph grounded in source evidence.
          </p>
          <div className="hero-actions">
            <button className="button button-primary button-large" type="button" onClick={login}>
              <GitHubIcon />
              Continue with GitHub
            </button>
            <span>Public repositories only · No code is modified</span>
          </div>
        </div>

        <div className="hero-visual" aria-label="Example repository dependency graph">
          <div className="visual-grid" />
          <div className="flow-line flow-line-one" />
          <div className="flow-line flow-line-two" />
          <div className="flow-line flow-line-three" />
          <VisualNode className="visual-node-app" kind="TSX" title="App.tsx" detail="Application entry" />
          <VisualNode className="visual-node-orders" kind="TSX" title="Orders.tsx" detail="Page component" />
          <VisualNode className="visual-node-api" kind="TS" title="orders.ts" detail="API client" />
          <VisualNode className="visual-node-fastapi" kind="PY" title="orders.py" detail="FastAPI route" />
          <div className="visual-caption">
            <span className="live-dot" />
            Deterministic dependency graph
          </div>
        </div>
      </section>

      <section className="value-strip" aria-label="SystemLab capabilities">
        <article>
          <strong>01</strong>
          <div>
            <h2>Source-grounded</h2>
            <p>Every edge preserves its import evidence and confidence.</p>
          </div>
        </article>
        <article>
          <strong>02</strong>
          <div>
            <h2>Fault tolerant</h2>
            <p>Partial knowledge survives malformed or unresolved files.</p>
          </div>
        </article>
        <article>
          <strong>03</strong>
          <div>
            <h2>Built to explore</h2>
            <p>Search, filter, and trace relationships across the repository.</p>
          </div>
        </article>
      </section>
    </main>
  );
}

function VisualNode({
  className,
  kind,
  title,
  detail,
}: {
  className: string;
  kind: string;
  title: string;
  detail: string;
}) {
  return (
    <div className={`visual-node ${className}`}>
      <span>{kind}</span>
      <div>
        <strong>{title}</strong>
        <small>{detail}</small>
      </div>
    </div>
  );
}

function GitHubIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 .8a11.4 11.4 0 0 0-3.6 22.2c.6.1.8-.2.8-.5v-2.2c-3.3.7-4-1.4-4-1.4-.5-1.4-1.3-1.7-1.3-1.7-1.1-.8.1-.8.1-.8 1.2.1 1.9 1.3 1.9 1.3 1.1 1.9 2.8 1.3 3.4 1 .1-.8.4-1.3.8-1.6-2.7-.3-5.5-1.4-5.5-6a4.7 4.7 0 0 1 1.3-3.3c-.2-.3-.6-1.6.1-3.3 0 0 1-.3 3.5 1.3a12 12 0 0 1 6.3 0c2.4-1.6 3.5-1.3 3.5-1.3.7 1.7.3 3 .1 3.3a4.7 4.7 0 0 1 1.3 3.3c0 4.6-2.8 5.7-5.5 6 .5.4.8 1.1.8 2.2v3.2c0 .3.2.6.8.5A11.4 11.4 0 0 0 12 .8Z"
      />
    </svg>
  );
}
