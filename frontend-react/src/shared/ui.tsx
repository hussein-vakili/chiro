import { ReactNode } from "react";

interface LoadingStateProps {
  title?: string;
  detail?: string;
}

export function LoadingState({
  title = "Loading portal",
  detail = "Pulling the latest clinic data.",
}: LoadingStateProps) {
  return (
    <section className="rp-empty-card">
      <span className="rp-eyebrow">Loading</span>
      <h2>{title}</h2>
      <p>{detail}</p>
    </section>
  );
}

interface ErrorStateProps {
  title?: string;
  detail: string;
  actionLabel?: string;
  onRetry?: (() => void) | null;
}

export function ErrorState({
  title = "Something went wrong",
  detail,
  actionLabel = "Try again",
  onRetry,
}: ErrorStateProps) {
  return (
    <section className="rp-empty-card rp-empty-card-error">
      <span className="rp-eyebrow">Error</span>
      <h2>{title}</h2>
      <p>{detail}</p>
      {onRetry ? (
        <button type="button" className="rp-button rp-button-primary" onClick={onRetry}>
          {actionLabel}
        </button>
      ) : null}
    </section>
  );
}

interface StatusPillProps {
  tone?: string;
  children: ReactNode;
}

export function StatusPill({ tone = "sky", children }: StatusPillProps) {
  return <span className={`rp-pill tone-${tone}`}>{children}</span>;
}
