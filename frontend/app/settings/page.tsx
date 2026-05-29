import { Building2, ShieldCheck, UserRound } from "lucide-react";

const profileFields = [
  { label: "Display name", value: "Demo Reviewer" },
  { label: "Email", value: "reviewer@demo.local" },
  { label: "Organization", value: "Portfolio Review" },
  { label: "Role", value: "Talent reviewer" },
  { label: "Workspace", value: "Research Data Command Center" },
  { label: "Access", value: "Read-only demo" },
];

const preferenceCards = [
  {
    label: "home",
    title: "Landing view",
    body: "Research Programs opens first for a clean product walkthrough.",
  },
  {
    label: "timezone",
    title: "America/New_York",
    body: "Dates and review timestamps use the portfolio owner's local time.",
  },
  {
    label: "digest",
    title: "Quiet notifications",
    body: "Demo account shows a calm review mode instead of operational alerts.",
  },
  {
    label: "display",
    title: "Standard theme",
    body: "Keeps the reviewer experience consistent across the portfolio demo.",
  },
];

export default function SettingsPage() {
  return (
    <section className="page">
      <div className="page-header compact-header">
        <div>
          <p className="eyebrow">Account Settings</p>
          <h1>Demo Reviewer Profile</h1>
          <p className="subtle">
            A dummy account surface for portfolio reviewers exploring the research lifecycle.
          </p>
        </div>
        <span className="badge status-active">active demo</span>
      </div>

      <div className="two-column">
        <div className="panel">
          <div className="dataset-hero-topline">
            <div className="program-kicker">
              <UserRound aria-hidden="true" size={16} />
              Reviewer account
            </div>
            <span className="badge neutral">no live login</span>
          </div>
          <div>
            <h2>Demo Reviewer</h2>
            <p className="subtle">
              A lightweight profile that makes the hosted demo feel signed in without exposing
              operational controls.
            </p>
          </div>
          <div className="metadata-grid">
            {profileFields.map((field) => (
              <MetadataItem key={field.label} label={field.label} value={field.value} />
            ))}
          </div>
        </div>

        <div className="panel">
          <div>
            <h2>Review Context</h2>
            <p className="subtle">
              The account is framed around evaluating the product story, code surface, and research
              workflow.
            </p>
          </div>
          <div className="record-list">
            <article className="record">
              <span className="badge">
                <Building2 aria-hidden="true" size={13} />
                workspace
              </span>
              <h3>Portfolio Review</h3>
              <p className="subtle">
                Inspect programs, data assets, runs, models, evaluations, failures, and dataset
                iteration decisions.
              </p>
            </article>
            <article className="record">
              <span className="badge neutral">
                <ShieldCheck aria-hidden="true" size={13} />
                access mode
              </span>
              <h3>Read-only demo</h3>
              <p className="subtle">
                The reviewer can inspect the product story without changing research data.
              </p>
            </article>
          </div>
        </div>
      </div>

      <div className="panel">
        <div>
          <h2>Account Preferences</h2>
          <p className="subtle">Static defaults for the reviewer-facing demo session.</p>
        </div>
        <div className="component-grid">
          {preferenceCards.map((card) => (
            <div className="component-card" key={card.title}>
              <span>{card.label}</span>
              <strong>{card.title}</strong>
              <p>{card.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function MetadataItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="metadata-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
