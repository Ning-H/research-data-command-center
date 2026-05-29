import Link from "next/link";
import { redirect } from "next/navigation";

import { createResearchProgram } from "../../../lib/api";

export const dynamic = "force-dynamic";

export default function NewResearchProgramPage() {
  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Research Programs</p>
          <h1>Register Program</h1>
          <p className="subtle">
            Create a research container before attaching experiments, runs, evaluations, failures,
            and dataset candidates.
          </p>
        </div>
        <Link className="btn btn--secondary" href="/research-programs">
          All programs
        </Link>
      </div>

      <form className="panel form-panel" action={registerResearchProgram}>
        <div>
          <h2>Program Overview</h2>
          <p className="subtle">Start with the research goal, ownership, and current focus.</p>
        </div>

        <div className="form-grid">
          <label className="field">
            <span>program_name</span>
            <input name="program_name" required placeholder="Improve structured study-material generation" />
          </label>
          <label className="field">
            <span>short_name</span>
            <input name="short_name" placeholder="e.g. safety-evals-v2, long-form-gen" />
          </label>
          <label className="field">
            <span>status</span>
            <select name="status" defaultValue="planning">
              <option value="planning">Planning</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="completed">Completed</option>
              <option value="archived">Archived</option>
            </select>
          </label>
          <label className="field">
            <span>owner_name</span>
            <input name="owner_name" placeholder="Ning Han" />
          </label>
          <label className="field">
            <span>research_area</span>
            <input name="research_area" placeholder="model_behavior_long_form_education" />
          </label>
          <label className="field">
            <span>researcher_names</span>
            <input name="researcher_names" placeholder="Ning Han, reviewer, evaluator" />
          </label>
        </div>

        <label className="field">
          <span>program_description</span>
          <textarea name="program_description" placeholder="What this program studies and why it matters." />
        </label>
        <label className="field">
          <span>research_goal</span>
          <textarea name="research_goal" placeholder="What measurable research goal are we working toward?" />
        </label>
        <label className="field">
          <span>hypothesis</span>
          <textarea name="hypothesis" placeholder="What claim should future experiments test?" />
        </label>
        <label className="field">
          <span>current_focus</span>
          <textarea name="current_focus" placeholder="What is the next slice of work?" />
        </label>
        <label className="field">
          <span>tags</span>
          <input name="tags" placeholder="study_material, python_algorithms, long_form_generation" />
        </label>

        <div className="action-row">
          <button className="btn btn--primary" type="submit">
            Register program
          </button>
        </div>
      </form>
    </section>
  );
}

async function registerResearchProgram(formData: FormData) {
  "use server";

  const program = await createResearchProgram({
    current_focus: field(formData, "current_focus"),
    hypothesis: field(formData, "hypothesis"),
    owner_name: field(formData, "owner_name"),
    program_description: field(formData, "program_description"),
    program_name: field(formData, "program_name"),
    research_area: field(formData, "research_area"),
    research_goal: field(formData, "research_goal"),
    researcher_names: commaList(formData, "researcher_names"),
    short_name: field(formData, "short_name"),
    status: field(formData, "status") || "planning",
    tags: commaList(formData, "tags"),
  });
  redirect(`/research-programs/${program.program_id}`);
}

function field(formData: FormData, name: string) {
  return String(formData.get(name) ?? "").trim();
}

function commaList(formData: FormData, name: string) {
  return field(formData, name)
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}
