"use client";

import Link from "next/link";
import { useState } from "react";

import { updateResearchProgram } from "../../../lib/api";
import type { ResearchProgramDetail, ResearchProgramPayload } from "../../../lib/api";

type Props = {
  initialProgram: ResearchProgramDetail;
  linkedExperiments: number;
  linkedDatasets: number;
  linkedRuns: number;
  owner: string;
  team: string[];
  researchArea: string;
  programId: number;
  createdAt: string;
  updatedAt: string;
};

const STATUS_OPTIONS = ["planning", "active", "paused", "completed", "archived"];

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

export default function ProgramEditableFields({
  initialProgram,
  linkedExperiments,
  linkedDatasets,
  linkedRuns,
  owner,
  team,
  researchArea,
  programId,
  createdAt,
  updatedAt,
}: Props) {
  const [program, setProgram] = useState(initialProgram);
  const [draft, setDraft] = useState<ResearchProgramPayload>({});
  const [confirming, setConfirming] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const merged = { ...program, ...draft };
  const mergedTags = Array.isArray(draft.tags) ? draft.tags : program.tags;
  const isDirty = Object.keys(draft).length > 0;

  function setField(field: keyof ResearchProgramPayload, value: string | string[]) {
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
      const updated = await updateResearchProgram(String(program.program_id), draft);
      setProgram(updated);
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
        <ProgramTitleField
          value={merged.program_name ?? ""}
          onChange={(v) => setField("program_name", v)}
          owner={owner}
          team={team}
          researchArea={researchArea}
          createdAt={createdAt}
          updatedAt={updatedAt}
        />
        <TagsField
          tags={mergedTags}
          onChange={(tags) => setField("tags", tags)}
        />

        {/* Activity strip — clickable, not editable */}
        <div className="activity-strip">
          <Link className="activity-chip" href="/experiments">
            <strong>{linkedExperiments}</strong>
            <span>Experiments</span>
          </Link>
          <Link className="activity-chip" href="/data-assets">
            <strong>{linkedDatasets}</strong>
            <span>Datasets</span>
          </Link>
          <Link className="activity-chip" href="/training-runs">
            <strong>{linkedRuns}</strong>
            <span>Runs</span>
          </Link>
        </div>

        <StatusField
          value={merged.status ?? "planning"}
          onChange={(v) => setField("status", v)}
        />
        <EditableField
          label="Initiating Context"
          value={merged.initiating_context ?? ""}
          onChange={(v) => setField("initiating_context", v)}
        />
        <EditableField
          label="Problem Statement"
          value={merged.problem_statement ?? ""}
          onChange={(v) => setField("problem_statement", v)}
        />
        <EditableField
          label="Objectives"
          value={merged.research_objectives ?? ""}
          onChange={(v) => setField("research_objectives", v)}
        />
        <EditableField
          label="Research Goal"
          value={merged.research_goal ?? ""}
          onChange={(v) => setField("research_goal", v)}
        />
        <EditableField
          label="Hypothesis"
          value={merged.hypothesis ?? ""}
          onChange={(v) => setField("hypothesis", v)}
        />
        <EditableField
          label="Current Focus"
          value={merged.current_focus ?? ""}
          onChange={(v) => setField("current_focus", v)}
          highlight
        />
      </div>

      {isDirty && (
        <div className="save-bar">
          {error && <span className="save-error">{error}</span>}
          {confirming ? (
            <>
              <span className="save-bar-label">
                Save changes to &ldquo;{merged.program_name}&rdquo;?
              </span>
              <button
                className="btn btn--secondary"
                disabled={saving}
                onClick={() => setConfirming(false)}
                type="button"
              >
                Cancel
              </button>
              <button
                className="btn btn--primary"
                disabled={saving}
                onClick={save}
                type="button"
              >
                {saving ? "Saving…" : "Confirm save"}
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
  isTitle = false,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  multiline?: boolean;
  highlight?: boolean;
  isTitle?: boolean;
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

  function onKeyDown(e: React.KeyboardEvent) {
    if (!multiline && e.key === "Enter") {
      e.preventDefault();
      commit();
    }
    if (e.key === "Escape") {
      setLocal(value);
      setEditing(false);
    }
  }

  const displayClass = [
    "field-row-value",
    !value ? "empty" : "",
    highlight ? "highlight" : "",
    isTitle ? "title" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="field-row">
      <span className={`field-row-label doc-label${highlight ? " highlight" : ""}`}>
        {label}
      </span>
      <div>
        {editing ? (
          multiline ? (
            <textarea
              autoFocus
              className="field-row-input"
              onBlur={commit}
              onChange={(e) => setLocal(e.target.value)}
              onKeyDown={onKeyDown}
              rows={Math.max(3, (local.match(/\n/g) ?? []).length + 2)}
              value={local}
            />
          ) : (
            <input
              autoFocus
              className="field-row-input"
              onBlur={commit}
              onChange={(e) => setLocal(e.target.value)}
              onKeyDown={onKeyDown}
              value={local}
            />
          )
        ) : (
          <p
            className={displayClass}
            onClick={startEdit}
            onKeyDown={(e) => e.key === "Enter" && startEdit()}
            role="button"
            tabIndex={0}
            title="Click to edit"
          >
            {value || "Click to add…"}
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
  onChange: (v: string) => void;
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
            onChange={(e) => setLocal(e.target.value)}
            value={local}
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        ) : (
          <span
            className={statusBadgeClass(value || "planning")}
            onClick={() => { setLocal(value); setEditing(true); }}
            onKeyDown={(e) => e.key === "Enter" && setEditing(true)}
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

function ProgramTitleField({
  value,
  onChange,
  owner,
  team,
  researchArea,
  createdAt,
  updatedAt,
}: {
  value: string;
  onChange: (v: string) => void;
  owner: string;
  team: string[];
  researchArea: string;
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

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") { e.preventDefault(); commit(); }
    if (e.key === "Escape") { setLocal(value); setEditing(false); }
  }

  return (
    <div className="field-row" style={{ borderTop: 0, paddingTop: 0 }}>
      <span className="field-row-label doc-label">Program</span>
      <div>
        {editing ? (
          <input
            autoFocus
            className="field-row-input"
            onBlur={commit}
            onChange={(e) => setLocal(e.target.value)}
            onKeyDown={onKeyDown}
            value={local}
          />
        ) : (
          <p
            className={`field-row-value title${!value ? " empty" : ""}`}
            onClick={startEdit}
            onKeyDown={(e) => e.key === "Enter" && startEdit()}
            role="button"
            tabIndex={0}
            title="Click to edit"
          >
            {value || "Click to add…"}
          </p>
        )}
        <div className="program-meta">
          <div className="program-meta-row">
            {owner && <span>{owner}</span>}
            {team.length > 0 && <span>{team.join(", ")}</span>}
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

function formatFullDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return iso;
  }
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
    onChange(input.split(",").map((t) => t.trim()).filter(Boolean));
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
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && commit()}
            placeholder="tag1, tag2, tag3"
            value={input}
          />
        ) : (
          <div
            className={`tag-chips-edit${!tags.length ? " empty" : ""}`}
            onClick={startEdit}
            onKeyDown={(e) => e.key === "Enter" && startEdit()}
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
              <span className="field-row-value empty">Click to add tags…</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
