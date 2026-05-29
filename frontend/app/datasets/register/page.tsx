import Link from "next/link";
import { redirect } from "next/navigation";

import { registerDataset, registerRawDataset } from "../../../lib/api";

export const dynamic = "force-dynamic";

const CATEGORIES = [
  "Raw data",
  "Post-training / SFT",
  "Preference data",
  "Eval data",
  "Safety / red-team",
  "Inference traces",
  "Other",
];

export default function RegisterDatasetPage() {
  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Data Assets</p>
          <h1>Register Data Asset</h1>
          <p className="subtle">
            Register a new data asset as version 1. Structured records are parsed, profiled, and
            quality-scored. Unstructured data and uploaded files are stored as-is.
          </p>
        </div>
        <Link className="btn btn--secondary" href="/datasets">
          All datasets
        </Link>
      </div>

      <form className="panel form-panel" action={registerAssetAction}>
        <div className="form-grid">
          <label className="field">
            <span>name</span>
            <input name="name" required placeholder="Crawl snapshot 2026-05" />
          </label>
          <label className="field">
            <span>data structure</span>
            <select name="data_structure" defaultValue="structured">
              <option value="structured">Structured data</option>
              <option value="unstructured">Unstructured</option>
            </select>
          </label>
          <label className="field">
            <span>category</span>
            <select name="category" defaultValue="Raw data">
              {CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
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
            <span>task_type</span>
            <input name="task_type" placeholder="study_guide_generation (structured only)" />
          </label>
        </div>

        <label className="field">
          <span>data_purpose</span>
          <textarea name="data_purpose" placeholder="Why this asset is being stored and how it will be used." />
        </label>
        <label className="field">
          <span>description</span>
          <textarea name="description" placeholder="What this asset contains." />
        </label>

        <div className="data-input-grid">
          <label className="field">
            <span>enter data</span>
            <textarea name="records" rows={9} className="mono" placeholder={DATA_PLACEHOLDER} />
            <span className="field-hint">
              Structured: a JSON array of objects, or one JSON object per line (JSONL). Unstructured:
              any text. Leave empty if uploading a file.
            </span>
          </label>
          <label className="field">
            <span>or upload a file</span>
            <input name="file" type="file" />
            <span className="field-hint">
              Any file type (Parquet, CSV, images, archives, ...). Always stored as-is.
            </span>
          </label>
        </div>

        <div className="action-row">
          <button className="btn btn--primary" type="submit">
            Register asset
          </button>
        </div>
      </form>
    </section>
  );
}

const DATA_PLACEHOLDER = `Structured example:
[
  { "instruction": "Explain binary search", "response": "Finds a target in sorted data." }
]

Unstructured example:
Any free-form notes, logs, or text.`;

async function registerAssetAction(formData: FormData) {
  "use server";

  const file = formData.get("file");
  const hasFile = file instanceof File && file.size > 0;
  const dataStructure = field(formData, "data_structure") || "structured";
  const text = field(formData, "records");

  // Option A: structured + typed records -> parsed pipeline.
  // Anything else (unstructured text, or any uploaded file) -> stored as-is (raw).
  if (!hasFile && dataStructure === "structured") {
    if (!text) {
      throw new Error("enter records or upload a file");
    }
    const dataset = await registerDataset({
      name: field(formData, "name"),
      task_type: field(formData, "task_type") || "general_records",
      source_label: field(formData, "source_label") || "SYNTHETIC_REALISTIC",
      category: field(formData, "category"),
      data_purpose: field(formData, "data_purpose"),
      description: field(formData, "description"),
      data_structure: "structured",
      records: parseRecords(text),
    });
    redirect(`/datasets/${dataset.dataset_id}`);
  }

  if (!hasFile && !text) {
    throw new Error("enter data or upload a file");
  }

  const rawForm = new FormData();
  if (hasFile) {
    rawForm.set("file", file);
  } else {
    const safeName = field(formData, "name").replace(/[^A-Za-z0-9._-]+/g, "_") || "data";
    rawForm.set("file", new Blob([text], { type: "text/plain" }), `${safeName}.txt`);
  }
  rawForm.set("name", field(formData, "name"));
  rawForm.set("source_label", field(formData, "source_label") || "SYNTHETIC_REALISTIC");
  rawForm.set("category", field(formData, "category"));
  rawForm.set("description", field(formData, "description"));
  rawForm.set("data_purpose", field(formData, "data_purpose"));
  rawForm.set("data_structure", dataStructure);
  const dataset = await registerRawDataset(rawForm);
  redirect(`/datasets/${dataset.dataset_id}`);
}

function field(formData: FormData, name: string) {
  return String(formData.get(name) ?? "").trim();
}

function parseRecords(raw: string): Array<Record<string, unknown>> {
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
    throw new Error("structured data must be a non-empty list of JSON objects");
  }
  return records as Array<Record<string, unknown>>;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
