import { ArrowRight, Database, LineChart, Search } from "lucide-react";
import Link from "next/link";

export default function HomePage() {
  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Command Center</p>
          <h1>Research data lifecycle, connected end to end.</h1>
        </div>
        <Link className="button" href="/datasets">
          <Database aria-hidden="true" size={17} />
          Open Datasets
        </Link>
      </div>

      <div className="summary-grid">
        <div className="metric">
          <p className="metric-label">First data asset</p>
          <p className="metric-value">Dolly 15k</p>
        </div>
        <div className="metric">
          <p className="metric-label">Source label</p>
          <p className="metric-value">PUBLIC_REAL</p>
        </div>
        <div className="metric">
          <p className="metric-label">Storage path</p>
          <p className="metric-value">Parquet</p>
        </div>
        <div className="metric">
          <p className="metric-label">Query engine</p>
          <p className="metric-value">DuckDB</p>
        </div>
      </div>

      <div className="placeholder-grid">
        <div className="panel">
          <Database aria-hidden="true" color="#0f766e" size={22} />
          <h2>Datasets</h2>
          <p className="subtle">Catalog, records, schema, quality, versions, lineage, and usage.</p>
          <Link className="button secondary" href="/datasets">
            Catalog <ArrowRight aria-hidden="true" size={16} />
          </Link>
        </div>
        <div className="panel">
          <LineChart aria-hidden="true" color="#0f766e" size={22} />
          <h2>Runs</h2>
          <p className="subtle">Active runs and metrics will attach to approved dataset versions next.</p>
        </div>
        <div className="panel">
          <Search aria-hidden="true" color="#0f766e" size={22} />
          <h2>Models & Evaluations</h2>
          <p className="subtle">Failures and regressions will close the loop back into dataset candidates.</p>
        </div>
      </div>
    </section>
  );
}
