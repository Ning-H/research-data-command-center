import { ArrowRight } from "lucide-react";
import Link from "next/link";

type LifecyclePageProps = {
  eyebrow: string;
  title: string;
  description: string;
  status: string;
  primaryHref?: string;
  primaryLabel?: string;
  cards: Array<{
    title: string;
    body: string;
    label?: string;
  }>;
  apiRoutes: string[];
};

export function LifecyclePage({
  apiRoutes,
  cards,
  description,
  eyebrow,
  primaryHref,
  primaryLabel = "Open working slice",
  status,
  title,
}: LifecyclePageProps) {
  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p className="subtle">{description}</p>
        </div>
        {primaryHref ? (
          <Link className="btn btn--secondary" href={primaryHref}>
            {primaryLabel}
            <ArrowRight aria-hidden="true" size={16} />
          </Link>
        ) : null}
      </div>

      <div className="panel">
        <div>
          <h2>Lifecycle Role</h2>
          <p className="subtle">{status}</p>
        </div>
        <div className="component-grid">
          {cards.map((card) => (
            <div className="component-card" key={card.title}>
              <span>{card.label ?? "workflow"}</span>
              <strong>{card.title}</strong>
              <p>{card.body}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="two-column">
        <div className="panel">
          <div>
            <h2>API Direction</h2>
            <p className="subtle">
              These endpoints define the next backend surface for this product area.
            </p>
          </div>
          <div className="record-list">
            {apiRoutes.map((route) => (
              <article className="record" key={route}>
                <span className="badge neutral">planned api</span>
                <p className="mono">{route}</p>
              </article>
            ))}
          </div>
        </div>

        <div className="panel">
          <div>
            <h2>Lineage Question</h2>
            <p className="subtle">
              This page exists only if it helps answer what changed, what caused it, how the model
              behaved, or what dataset/version should be created next.
            </p>
          </div>
          <div className="quality-note">
            <span className="badge">lineage first</span>
            <p>Every future table here must carry explicit source and target IDs.</p>
          </div>
        </div>
      </div>
    </section>
  );
}
