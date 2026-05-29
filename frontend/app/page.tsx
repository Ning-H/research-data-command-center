import {
  AlertTriangle,
  ArrowRight,
  Boxes,
  BrainCircuit,
  ClipboardCheck,
  Database,
  FlaskConical,
  LineChart,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { listDatasets, listModels, listRuns } from "../lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [datasets, runs, models] = await Promise.all([listDatasets(), listRuns(), listModels()]);
  const failedRuns = runs.filter((run) => run.status === "failed").length;
  const openFailures = 0;
  const datasetCandidates = 0;

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Research Lifecycle Command Center</p>
          <h1>Trace the research goal, data, run, checkpoint, model, eval, failure, and next dataset.</h1>
          <p className="subtle">
            A lineage-first operations platform for understanding what changed, why behavior changed,
            which data/run/checkpoint caused it, and what the team should try next.
          </p>
        </div>
        <Link className="btn btn--primary" href="/research-programs">
          <BrainCircuit aria-hidden="true" size={17} />
          Open Programs
        </Link>
      </div>

      <div className="summary-grid">
        <div className="metric">
          <p className="metric-label">Data assets</p>
          <p className="metric-value">{datasets.length}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Training runs</p>
          <p className="metric-value">{runs.length}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Model candidates</p>
          <p className="metric-value">{models.length}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Failed runs</p>
          <p className="metric-value">{failedRuns}</p>
        </div>
      </div>

      <div className="placeholder-grid">
        <LifecycleCard
          href="/research-programs"
          icon={<BrainCircuit aria-hidden="true" className="accent-icon" size={22} />}
          title="Research Programs"
        >
          Group hypotheses, experiments, data mixtures, model behavior changes, and next actions.
        </LifecycleCard>
        <LifecycleCard
          href="/datasets"
          icon={<Database aria-hidden="true" className="accent-icon" size={22} />}
          title="Data Assets"
        >
          Register public and generated data, validate quality, version it, and create mixtures.
        </LifecycleCard>
        <LifecycleCard
          href="/experiments"
          icon={<FlaskConical aria-hidden="true" className="accent-icon" size={22} />}
          title="Experiments"
        >
          Track the research question and expected metric movement before inspecting runs.
        </LifecycleCard>
        <LifecycleCard
          href="/training-runs"
          icon={<LineChart aria-hidden="true" className="accent-icon" size={22} />}
          title="Training Runs"
        >
          Ingest external run configs, raw metrics, checkpoints, and compute telemetry.
        </LifecycleCard>
        <LifecycleCard
          href="/models-checkpoints"
          icon={<Boxes aria-hidden="true" className="accent-icon" size={22} />}
          title="Models & Checkpoints"
        >
          Promote ranked checkpoints into immutable model versions with derived lineage.
        </LifecycleCard>
        <LifecycleCard
          href="/evaluations"
          icon={<ClipboardCheck aria-hidden="true" className="accent-icon" size={22} />}
          title="Evaluations"
        >
          Compare model versions, track regressions, and send failed cases to the failure library.
        </LifecycleCard>
      </div>

      <div className="two-column">
        <div className="panel">
          <div>
            <h2>Immediate Lifecycle Story</h2>
            <p className="subtle">
              Improve structured Python algorithms study-guide generation by comparing a baseline
              model against variants trained with better outlines, examples, and corrected failures.
            </p>
          </div>
          <div className="record-list">
            <LifecycleStep step="1" title="Research Program" value="Improve structured study-material generation" />
            <LifecycleStep
              step="2"
              title="Hypothesis"
              value="Structured examples, outline-first patterns, and corrected failures improve coverage and depth."
            />
            <LifecycleStep step="3" title="Current Working Spine" value="data asset -> training run -> checkpoint -> model version" />
            <LifecycleStep step="4" title="Next Build Slice" value="evaluation run -> failure case -> dataset candidate" />
          </div>
        </div>
        <div className="panel">
          <div>
            <h2>Open Work Queues</h2>
            <p className="subtle">The next surfaces will turn these from counters into workflows.</p>
          </div>
          <div className="metadata-grid">
            <Metadata label="eval_regressions" value="0" />
            <Metadata label="open_failure_cases" value={openFailures} />
            <Metadata label="dataset_candidates" value={datasetCandidates} />
            <Metadata label="lineage_edges" value="planned" />
          </div>
          <div className="quality-note">
            <span className="badge warning">
              <AlertTriangle aria-hidden="true" size={13} />
              Next phase
            </span>
            <p>Build evaluations and failure capture against `model_version_id`.</p>
          </div>
        </div>
      </div>
    </section>
  );
}

function LifecycleCard({
  children,
  href,
  icon,
  title,
}: {
  children: string;
  href: string;
  icon: ReactNode;
  title: string;
}) {
  return (
    <div className="panel">
      {icon}
      <h2>{title}</h2>
      <p className="subtle">{children}</p>
      <Link className="btn btn--secondary" href={href}>
        Open <ArrowRight aria-hidden="true" size={16} />
      </Link>
    </div>
  );
}

function LifecycleStep({ step, title, value }: { step: string; title: string; value: string }) {
  return (
    <article className="record">
      <span className="badge neutral">Step {step}</span>
      <h3>{title}</h3>
      <p className="subtle">{value}</p>
    </article>
  );
}

function Metadata({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metadata-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
