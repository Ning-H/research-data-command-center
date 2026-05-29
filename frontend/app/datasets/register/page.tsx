import Link from "next/link";
import { redirect } from "next/navigation";

import { registerDataset, registerRawDataset } from "../../../lib/api";
import { RegisterTabs } from "./RegisterTabs";

export const dynamic = "force-dynamic";

export default function RegisterDatasetPage() {
  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Data Assets</p>
          <h1>Register Dataset</h1>
          <p className="subtle">
            Register a new data asset as version 1. Use structured records for normalized, quality-scored
            datasets, or upload any file as a raw asset stored as-is.
          </p>
        </div>
        <Link className="btn btn--secondary" href="/datasets">
          All datasets
        </Link>
      </div>

      <RegisterTabs structured={<StructuredForm />} raw={<RawForm />} />
    </section>
  );
}

function StructuredForm() {
  return (
    <form className="panel form-panel" action={registerDatasetAction}>
      <div>
        <h2>Structured records</h2>
        <p className="subtle">
          Records are normalized into versioned storage with schema profiling, quality metrics, and lineage.
        </p>
      </div>

      <div className="form-grid">
        <label className="field">
          <span>name</span>
          <input name="name" required placeholder="Registered Python Study Notes" />
        </label>
        <label className="field">
          <span>task_type</span>
          <input name="task_type" required placeholder="study_guide_generation" />
        </label>
        <label className="field">
          <span>source_label</span>
          <select name="source_label" defaultValue="SYNTHETIC_REALISTIC">
            <option value="PUBLIC_REAL">PUBLIC_REAL</option>
            <option value="GENERATED_REAL">GENERATED_REAL</option>
            <option value="SYNTHETIC_REALISTIC">SYNTHETIC_REALISTIC</option>
          </select>
        </label>
        <label className="field">
          <span>category</span>
          <input name="category" placeholder="Study-guide generation" />
        </label>
        <label className="field">
          <span>source_dataset_name</span>
          <input name="source_dataset_name" placeholder="registered/python-study-notes" />
        </label>
        <label className="field">
          <span>source_url</span>
          <input name="source_url" placeholder="s3://research-data/raw/python-study-notes.jsonl" />
        </label>
      </div>

      <label className="field">
        <span>data_purpose</span>
        <textarea name="data_purpose" placeholder="Training data for structured technical study-guide generation." />
      </label>
      <label className="field">
        <span>description</span>
        <textarea name="description" placeholder="What this dataset contains and how it should be used." />
      </label>
      <label className="field">
        <span>records</span>
        <textarea name="records" required rows={10} className="mono" placeholder={RECORDS_PLACEHOLDER} />
        <span className="field-hint">
          Paste a JSON array of objects, or one JSON object per line (JSONL). Must be non-empty.
        </span>
      </label>

      <div className="action-row">
        <button className="btn btn--primary" type="submit">
          Register dataset
        </button>
      </div>
    </form>
  );
}

function RawForm() {
  return (
    <form className="panel form-panel" action={registerRawAction}>
      <div>
        <h2>Raw file upload</h2>
        <p className="subtle">
          Upload any file (Parquet, CSV, images, archives, unstructured data). It is stored as-is in object
          storage without parsing. No quality score or schema is generated.
        </p>
      </div>

      <label className="field">
        <span>file</span>
        <input name="file" type="file" required />
        <span className="field-hint">Any file type. Stored verbatim as the raw asset.</span>
      </label>

      <div className="form-grid">
        <label className="field">
          <span>name</span>
          <input name="name" required placeholder="Crawl snapshot 2026-05" />
        </label>
        <label className="field">
          <span>source_label</span>
          <select name="source_label" defaultValue="SYNTHETIC_REALISTIC">
            <option value="PUBLIC_REAL">PUBLIC_REAL</option>
            <option value="GENERATED_REAL">GENERATED_REAL</option>
            <option value="SYNTHETIC_REALISTIC">SYNTHETIC_REALISTIC</option>
          </select>
        </label>
        <label className="field">
          <span>category</span>
          <input name="category" placeholder="Raw blob" />
        </label>
      </div>

      <label className="field">
        <span>data_purpose</span>
        <textarea name="data_purpose" placeholder="Why this raw asset is being stored." />
      </label>
      <label className="field">
        <span>description</span>
        <textarea name="description" placeholder="What this file contains." />
      </label>

      <div className="action-row">
        <button className="btn btn--primary" type="submit">
          Upload raw asset
        </button>
      </div>
    </form>
  );
}

const RECORDS_PLACEHOLDER = `[
  { "instruction": "Explain binary search for Python learners.", "response": "Binary search finds a target in sorted data." },
  { "instruction": "Explain sliding window for Python learners.", "response": "Sliding window tracks a contiguous range." }
]`;

async function registerDatasetAction(formData: FormData) {
  "use server";

  const dataset = await registerDataset({
    name: field(formData, "name"),
    task_type: field(formData, "task_type"),
    source_label: field(formData, "source_label") || "SYNTHETIC_REALISTIC",
    category: field(formData, "category"),
    source_dataset_name: field(formData, "source_dataset_name"),
    source_url: field(formData, "source_url"),
    data_purpose: field(formData, "data_purpose"),
    description: field(formData, "description"),
    records: parseRecords(field(formData, "records")),
  });
  redirect(`/datasets/${dataset.dataset_id}`);
}

async function registerRawAction(formData: FormData) {
  "use server";

  const file = formData.get("file");
  if (!(file instanceof File) || file.size === 0) {
    throw new Error("a non-empty file is required");
  }
  const dataset = await registerRawDataset(formData);
  redirect(`/datasets/${dataset.dataset_id}`);
}

function field(formData: FormData, name: string) {
  return String(formData.get(name) ?? "").trim();
}

function parseRecords(raw: string): Array<Record<string, unknown>> {
  if (!raw) {
    throw new Error("records is required");
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    parsed = raw
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => JSON.parse(line));
  }

  const records = Array.isArray(parsed) ? parsed : [parsed];
  if (records.length === 0 || !records.every((record) => isPlainObject(record))) {
    throw new Error("records must be a non-empty list of JSON objects");
  }
  return records as Array<Record<string, unknown>>;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
