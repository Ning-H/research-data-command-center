"use client";

import { GitCompareArrows } from "lucide-react";
import { useMemo, useState } from "react";

import type { RunCheckpoint } from "../../../lib/api";

type CheckpointCompareProps = {
  bestCheckpointId?: number;
  checkpoints: RunCheckpoint[];
};

export default function CheckpointCompare({ bestCheckpointId, checkpoints }: CheckpointCompareProps) {
  const sortedCheckpoints = useMemo(
    () => [...checkpoints].sort((left, right) => left.step - right.step),
    [checkpoints],
  );
  const [selectedIds, setSelectedIds] = useState<number[]>(() => defaultSelectedIds(checkpoints, bestCheckpointId));
  const selectedCheckpoints = sortedCheckpoints.filter((checkpoint) => selectedIds.includes(checkpoint.checkpoint_id));
  const metricKeys = metricColumns(selectedCheckpoints);

  function toggleCheckpoint(checkpointId: number) {
    setSelectedIds((current) => {
      if (current.includes(checkpointId)) {
        return current.filter((id) => id !== checkpointId);
      }
      const next = [...current, checkpointId];
      return sortedCheckpoints
        .map((checkpoint) => checkpoint.checkpoint_id)
        .filter((id) => next.includes(id));
    });
  }

  if (!sortedCheckpoints.length) {
    return <p className="subtle">No checkpoints were submitted for this run.</p>;
  }

  return (
    <div className="checkpoint-compare">
      <div className="checkpoint-compare-toolbar">
        <div>
          <strong>Checkpoint comparison</strong>
          <span>Select two or more checkpoints to compare metric snapshots side by side.</span>
        </div>
        <div className="checkpoint-compare-actions">
          <button className="btn btn--secondary btn--sm" onClick={() => setSelectedIds(defaultSelectedIds(checkpoints, bestCheckpointId))} type="button">
            Recommended
          </button>
          <button className="btn btn--secondary btn--sm" onClick={() => setSelectedIds(sortedCheckpoints.map((checkpoint) => checkpoint.checkpoint_id))} type="button">
            Select all
          </button>
          <button className="btn btn--ghost btn--sm" onClick={() => setSelectedIds([])} type="button">
            Clear
          </button>
        </div>
      </div>

      <div className="checkpoint-selector-grid" aria-label="Selectable checkpoints">
        {sortedCheckpoints.map((checkpoint) => {
          const isSelected = selectedIds.includes(checkpoint.checkpoint_id);
          const isBest = checkpoint.checkpoint_id === bestCheckpointId;
          return (
            <label
              className={isSelected ? "checkpoint-selector checkpoint-selector--selected" : "checkpoint-selector"}
              key={checkpoint.checkpoint_id}
            >
              <input
                checked={isSelected}
                onChange={() => toggleCheckpoint(checkpoint.checkpoint_id)}
                type="checkbox"
              />
              <span className="checkpoint-selector-kicker">
                {isBest ? "Best candidate" : checkpoint.status}
              </span>
              <strong>checkpoint_id {checkpoint.checkpoint_id}</strong>
              <span>step {checkpoint.step}</span>
              <span>{formatMetric(checkpoint.metrics_snapshot["train.loss"])} loss</span>
            </label>
          );
        })}
      </div>

      {selectedCheckpoints.length >= 2 ? (
        <div className="checkpoint-comparison-wrap">
          <table className="checkpoint-comparison-table">
            <thead>
              <tr>
                <th>Metric</th>
                {selectedCheckpoints.map((checkpoint) => (
                  <th key={checkpoint.checkpoint_id}>checkpoint {checkpoint.checkpoint_id}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <ComparisonRow checkpoints={selectedCheckpoints} label="step" value={(checkpoint) => checkpoint.step} />
              <ComparisonRow checkpoints={selectedCheckpoints} label="status" value={(checkpoint) => checkpoint.status} />
              <ComparisonRow
                checkpoints={selectedCheckpoints}
                label="created_at"
                value={(checkpoint) => formatDateTime(checkpoint.created_at)}
              />
              {metricKeys.map((metricKey) => (
                <ComparisonRow
                  checkpoints={selectedCheckpoints}
                  key={metricKey}
                  label={metricKey}
                  value={(checkpoint) => formatMetric(checkpoint.metrics_snapshot[metricKey])}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="checkpoint-compare-empty">
          <GitCompareArrows aria-hidden="true" size={18} />
          <span>Select at least two checkpoints to compare performance snapshots.</span>
        </div>
      )}
    </div>
  );
}

function ComparisonRow({
  checkpoints,
  label,
  value,
}: {
  checkpoints: RunCheckpoint[];
  label: string;
  value: (checkpoint: RunCheckpoint) => number | string;
}) {
  return (
    <tr>
      <td>{label}</td>
      {checkpoints.map((checkpoint) => (
        <td key={checkpoint.checkpoint_id}>{value(checkpoint)}</td>
      ))}
    </tr>
  );
}

function defaultSelectedIds(checkpoints: RunCheckpoint[], bestCheckpointId?: number) {
  const sorted = [...checkpoints].sort((left, right) => left.step - right.step);
  const selected = new Set<number>();
  if (bestCheckpointId !== undefined) {
    selected.add(bestCheckpointId);
  }
  if (sorted[0]) {
    selected.add(sorted[0].checkpoint_id);
  }
  if (sorted[sorted.length - 1]) {
    selected.add(sorted[sorted.length - 1].checkpoint_id);
  }
  return sorted
    .map((checkpoint) => checkpoint.checkpoint_id)
    .filter((checkpointId) => selected.has(checkpointId))
    .slice(0, 3);
}

function metricColumns(checkpoints: RunCheckpoint[]) {
  const keys = new Set<string>();
  for (const checkpoint of checkpoints) {
    for (const key of Object.keys(checkpoint.metrics_snapshot)) {
      keys.add(key);
    }
  }
  return [...keys].sort((left, right) => metricPriority(left) - metricPriority(right) || left.localeCompare(right));
}

function metricPriority(metricName: string) {
  const priority = ["train.loss", "train.accuracy", "eval.loss", "eval.accuracy"];
  const index = priority.indexOf(metricName);
  return index === -1 ? priority.length : index;
}

function formatMetric(value: number | undefined) {
  if (value === undefined || Number.isNaN(value)) {
    return "not logged";
  }
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(4);
}

function formatDateTime(value: string) {
  if (!value) {
    return "not available";
  }
  return value.replace("T", " ").replace("Z", " UTC");
}
