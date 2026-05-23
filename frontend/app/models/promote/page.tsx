import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { redirect } from "next/navigation";

import { registerModelFromCheckpoint } from "../../../lib/api";

type PromotePageProps = {
  searchParams?: Record<string, string | string[] | undefined>;
};

export default function PromoteCheckpointPage({ searchParams = {} }: PromotePageProps) {
  const checkpointId = first(searchParams.checkpoint_id) ?? "";

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Models & Checkpoints / Register</p>
          <h1>Promote Checkpoint</h1>
          <p className="subtle">
            Create an immutable model version from a checkpoint. The API derives run and dataset
            lineage from `checkpoint_id`.
          </p>
        </div>
        <Link className="button secondary" href="/runs/checkpoints">
          <ArrowLeft aria-hidden="true" size={16} />
          Checkpoints
        </Link>
      </div>

      <form className="panel form-panel" action={promoteModelVersion}>
        <div>
          <h2>Registration Metadata</h2>
          <p className="subtle">
            Researchers provide human context here; technical lineage is copied from the checkpoint.
          </p>
        </div>

        <div className="form-grid">
          <label className="field">
            <span>checkpoint_id</span>
            <input name="checkpoint_id" required defaultValue={checkpointId} />
          </label>
          <label className="field">
            <span>model_name</span>
            <input name="model_name" required defaultValue="dolly-pytorch-classifier" />
          </label>
          <label className="field">
            <span>model_version_name</span>
            <input
              name="model_version_name"
              required
              defaultValue={checkpointId ? `candidate-checkpoint-${checkpointId}` : ""}
            />
          </label>
          <label className="field">
            <span>owner_user_id</span>
            <input name="owner_user_id" required defaultValue="user_demo_owner" />
          </label>
        </div>

        <label className="field">
          <span>intended_use</span>
          <textarea
            name="intended_use"
            defaultValue="Candidate model version for instruction category classification evaluation."
          />
        </label>
        <label className="field">
          <span>promotion_reason</span>
          <textarea
            name="promotion_reason"
            defaultValue="Highest ranked checkpoint for the selected dataset, trainer, and metric."
          />
        </label>
        <label className="field">
          <span>promotion_notes</span>
          <textarea name="promotion_notes" defaultValue="Registered from the checkpoint search workflow." />
        </label>

        <div className="action-row">
          <button className="button" type="submit">
            Register model version
          </button>
        </div>
      </form>
    </section>
  );
}

async function promoteModelVersion(formData: FormData) {
  "use server";

  const checkpointId = Number(formData.get("checkpoint_id"));
  const model = await registerModelFromCheckpoint({
    checkpoint_id: checkpointId,
    intended_use: String(formData.get("intended_use") ?? ""),
    model_name: String(formData.get("model_name") ?? ""),
    model_version_name: String(formData.get("model_version_name") ?? ""),
    owner_user_id: String(formData.get("owner_user_id") ?? ""),
    promotion_notes: String(formData.get("promotion_notes") ?? ""),
    promotion_reason: String(formData.get("promotion_reason") ?? ""),
  });
  redirect(`/models/${model.model_version_id}`);
}

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}
