"use client";

import { useState } from "react";

import { updateExperiment } from "../../../lib/api";
import type { ExperimentDetail, ExperimentPayload } from "../../../lib/api";

type Props = {
  initialExperiment: ExperimentDetail;
  programName: string;
};

const STATUS_OPTIONS = ["planning", "active", "paused", "completed", "archived"];

const EXPERIMENT_TYPES = [
  "baseline_comparison",
  "dataset_ablation",
  "prompt_strategy_comparison",
  "model_checkpoint_comparison",
  "failure_replay_comparison",
  "rubric_regression_check",
  "data_mixture_comparison",
  "training_config_comparison",
  "human_review_study",
  "study_material_structure_comparison",
  "other",
];

function statusBadgeClass(value: string) {
  const map: Record<string, string> = {
    active: "badge status-active status-badge",
    planning: "badge status-planning status-badge",
    paused: "badge status-paused status-badge",
    completed: "badge status-completed status-badge",
    archived: "badge status-archived status-badge",
  };
  return map[value] ?? "badge neutral status-badge";
}

export default function ExperimentEditableFields({ initialExperiment, programName }: Props) {
  const [experiment, setExperiment] = useState(initialExperiment);
  const [draft, setDraft] = useState<ExperimentPayload>({});
  const [confirming, setConfirming] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const merged = { ...experiment, ...draft };
  const mergedTags = Array.isArray(draft.tags) ? draft.tags : experiment.tags;
  const isDirty = Object.keys(draft).length > 0;

  function setField(field: keyof ExperimentPayload, value: string | string[]) {
    setDraft((prev) => ({ ...prev, [field]: value }));
  }

  function discard() {
    setDraft({});
    setConfirming(false);
    setError(null);
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateExperiment(String(experiment.experiment_id), draft);
      setExperiment(updated);
      setDraft({});
      setConfirming(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="field-table">
        <ExperimentTitleField
          createdAt={experiment.created_at}
          experimentId={experiment.experiment_id}
          owner={merged.owner_name ?? ""}
          programName={programName}
          updatedAt={experiment.updated_at}
          value={merged.experiment_name ?? ""}
          onChange={(value) => setField("experiment_name", value)}
        />
        <TagsField tags={mergedTags} onChange={(tags) => setField("tags", tags)} />
        <StatusField value={merged.status ?? "planning"} onChange={(value) => setField("status", value)} />
        <SelectField
          label="Experiment Type"
          options={EXPERIMENT_TYPES}
          value={merged.experiment_type ?? "other"}
          onChange={(value) => setField("experiment_type", value)}
        />
        <EditableField
          label="Owner"
          multiline={false}
          value={merged.owner_name ?? ""}
          onChange={(value) => setField("owner_name", value)}
        />
        <EditableField
          label="Description"
          value={merged.experiment_description ?? ""}
          onChange={(value) => setField("experiment_description", value)}
        />
        <EditableField
          label="Research Question"
          highlight
          value={merged.research_question ?? ""}
          onChange={(value) => setField("research_question", value)}
        />
        <EditableField
          label="Hypothesis"
          value={merged.hypothesis ?? ""}
          onChange={(value) => setField("hypothesis", value)}
        />
        <EditableField
          label="Evaluation Plan"
          value={merged.evaluation_plan ?? ""}
          onChange={(value) => setField("evaluation_plan", value)}
        />
        <EditableField
          label="Decision Context"
          value={merged.decision_notes ?? ""}
          onChange={(value) => setField("decision_notes", value)}
        />
      </div>

      {isDirty && (
        <div className="save-bar">
          {error && <span className="save-error">{error}</span>}
          {confirming ? (
            <>
              <span className="save-bar-label">
                Save changes to &ldquo;{merged.experiment_name}&rdquo;?
              </span>
              <button
                className="btn btn--secondary"
                disabled={saving}
                onClick={() => setConfirming(false)}
                type="button"
              >
                Cancel
              </button>
              <button className="btn btn--primary" disabled={saving} onClick={save} type="button">
                {saving ? "Saving..." : "Confirm save"}
              </button>
            </>
          ) : (
            <>
              <span className="save-bar-label">You have unsaved changes.</span>
              <button className="btn btn--secondary" onClick={discard} type="button">
                Discard
              </button>
              <button className="btn btn--primary" onClick={() => setConfirming(true)} type="button">
                Save changes
              </button>
            </>
          )}
        </div>
      )}
    </>
  );
}

function EditableField({
  label,
  value,
  onChange,
  multiline = true,
  highlight = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  multiline?: boolean;
  highlight?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [local, setLocal] = useState(value);

  function startEdit() {
    setLocal(value);
    setEditing(true);
  }

  function commit() {
    setEditing(false);
    if (local !== value) onChange(local);
  }

  function onKeyDown(event: React.KeyboardEvent) {
    if (!multiline && event.key === "Enter") {
      event.preventDefault();
      commit();
    }
    if (event.key === "Escape") {
      setLocal(value);
      setEditing(false);
    }
  }

  const displayClass = [
    "field-row-value",
    !value ? "empty" : "",
    highlight ? "highlight" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="field-row">
      <span className={`field-row-label doc-label${highlight ? " highlight" : ""}`}>{label}</span>
      <div>
        {editing ? (
          multiline ? (
            <textarea
              autoFocus
              className="field-row-input"
              onBlur={commit}
              onChange={(event) => setLocal(event.target.value)}
              onKeyDown={onKeyDown}
              rows={Math.max(3, (local.match(/\n/g) ?? []).length + 2)}
              value={local}
            />
          ) : (
            <input
              autoFocus
              className="field-row-input"
              onBlur={commit}
              onChange={(event) => setLocal(event.target.value)}
              onKeyDown={onKeyDown}
              value={local}
            />
          )
        ) : (
          <p
            className={displayClass}
            onClick={startEdit}
            onKeyDown={(event) => event.key === "Enter" && startEdit()}
            role="button"
            tabIndex={0}
            title="Click to edit"
          >
            {value || "Click to add..."}
          </p>
        )}
      </div>
    </div>
  );
}

function StatusField({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [local, setLocal] = useState(value);

  function commit() {
    setEditing(false);
    if (local !== value) onChange(local);
  }

  return (
    <div className="field-row">
      <span className="field-row-label doc-label">Status</span>
      <div>
        {editing ? (
          <select
            autoFocus
            className="field-row-input"
            onBlur={commit}
            onChange={(event) => setLocal(event.target.value)}
            value={local}
          >
            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        ) : (
          <span
            className={statusBadgeClass(value || "planning")}
            onClick={() => {
              setLocal(value);
              setEditing(true);
            }}
            onKeyDown={(event) => event.key === "Enter" && setEditing(true)}
            role="button"
            tabIndex={0}
            title="Click to edit"
          >
            {value || "planning"}
          </span>
        )}
      </div>
    </div>
  );
}

function SelectField({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string;
  onChange: (value: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [local, setLocal] = useState(value);

  function commit() {
    setEditing(false);
    if (local !== value) onChange(local);
  }

  return (
    <div className="field-row">
      <span className="field-row-label doc-label">{label}</span>
      <div>
        {editing ? (
          <select
            autoFocus
            className="field-row-input"
            onBlur={commit}
            onChange={(event) => setLocal(event.target.value)}
            value={local}
          >
            {options.map((option) => (
              <option key={option} value={option}>
                {humanize(option)}
              </option>
            ))}
          </select>
        ) : (
          <span
            className="badge neutral status-badge"
            onClick={() => {
              setLocal(value);
              setEditing(true);
            }}
            onKeyDown={(event) => event.key === "Enter" && setEditing(true)}
            role="button"
            tabIndex={0}
            title="Click to edit"
          >
            {humanize(value || "other")}
          </span>
        )}
      </div>
    </div>
  );
}

function ExperimentTitleField({
  value,
  onChange,
  owner,
  programName,
  experimentId,
  createdAt,
  updatedAt,
}: {
  value: string;
  onChange: (value: string) => void;
  owner: string;
  programName: string;
  experimentId: number;
  createdAt: string;
  updatedAt: string;
}) {
  const [editing, setEditing] = useState(false);
  const [local, setLocal] = useState(value);

  function startEdit() {
    setLocal(value);
    setEditing(true);
  }

  function commit() {
    setEditing(false);
    if (local !== value) onChange(local);
  }

  function onKeyDown(event: React.KeyboardEvent) {
    if (event.key === "Enter") {
      event.preventDefault();
      commit();
    }
    if (event.key === "Escape") {
      setLocal(value);
      setEditing(false);
    }
  }

  return (
    <div className="field-row" style={{ borderTop: 0, paddingTop: 0 }}>
      <span className="field-row-label doc-label">Experiment</span>
      <div>
        {editing ? (
          <input
            autoFocus
            className="field-row-input"
            onBlur={commit}
            onChange={(event) => setLocal(event.target.value)}
            onKeyDown={onKeyDown}
            value={local}
          />
        ) : (
          <p
            className={`field-row-value title${!value ? " empty" : ""}`}
            onClick={startEdit}
            onKeyDown={(event) => event.key === "Enter" && startEdit()}
            role="button"
            tabIndex={0}
            title="Click to edit"
          >
            {value || "Click to add..."}
          </p>
        )}
        <div className="program-meta">
          <div className="program-meta-row">
            <span>{programName}</span>
            {owner && <span>{owner}</span>}
            <span>experiment_id {experimentId}</span>
          </div>
          <div className="program-meta-row">
            {createdAt && <span>Created {formatFullDate(createdAt)}</span>}
            {updatedAt && <span>Updated {formatFullDate(updatedAt)}</span>}
          </div>
        </div>
      </div>
    </div>
  );
}

function TagsField({
  tags,
  onChange,
}: {
  tags: string[];
  onChange: (tags: string[]) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [input, setInput] = useState("");

  function startEdit() {
    setInput(tags.join(", "));
    setEditing(true);
  }

  function commit() {
    setEditing(false);
    onChange(input.split(",").map((tag) => tag.trim()).filter(Boolean));
  }

  return (
    <div className="field-row">
      <span className="field-row-label doc-label">Tags</span>
      <div>
        {editing ? (
          <input
            autoFocus
            className="field-row-input"
            onBlur={commit}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && commit()}
            placeholder="tag1, tag2, tag3"
            value={input}
          />
        ) : (
          <div
            className={`tag-chips-edit${!tags.length ? " empty" : ""}`}
            onClick={startEdit}
            onKeyDown={(event) => event.key === "Enter" && startEdit()}
            role="button"
            tabIndex={0}
            title="Click to edit"
          >
            {tags.length > 0 ? (
              tags.map((tag) => (
                <span className="badge neutral" key={tag}>
                  {tag}
                </span>
              ))
            ) : (
              <span className="field-row-value empty">Click to add tags...</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function humanize(value: string) {
  return value ? value.replaceAll("_", " ") : "unspecified";
}

function formatFullDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}
