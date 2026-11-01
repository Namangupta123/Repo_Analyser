interface LoadingStateProps {
  label: string;
  fullPage?: boolean;
}

export function LoadingState({ label, fullPage = false }: LoadingStateProps) {
  return (
    <div className={fullPage ? 'state-screen' : 'state-panel'} role="status">
      <span className="loader" aria-hidden="true" />
      <p>{label}</p>
    </div>
  );
}

interface EmptyStateProps {
  eyebrow?: string;
  title: string;
  description: string;
}

export function EmptyState({ eyebrow = 'Nothing here yet', title, description }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className="empty-orbit" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <p className="eyebrow">{eyebrow}</p>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}

export function InlineError({ message }: { message: string }) {
  return (
    <div className="inline-error" role="alert">
      <span aria-hidden="true">!</span>
      {message}
    </div>
  );
}
