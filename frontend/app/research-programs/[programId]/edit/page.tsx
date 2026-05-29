import Link from "next/link";
import { redirect } from "next/navigation";

import { getResearchProgram, updateResearchProgram } from "../../../../lib/api";

export const dynamic = "force-dynamic";

type EditResearchProgramPageProps = {
  params: {
    programId: string;
  };
};

export default async function EditResearchProgramPage({ params }: EditResearchProgramPageProps) {
  const program = await getResearchProgram(params.programId);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Research Program</p>
          <h1>Edit Program</h1>
          <p className="subtle">{program.program_name}</p>
        </div>
        <Link className="btn btn--secondary" href={`/research-programs/${program.program_id}`}>
          Program detail
        </Link>
      </div>

      <form className="panel form-panel" action={updateProgram}>
        <input name="program_id" type="hidden" value={program.program_id} />
        <div>
          <h2>Program Overview</h2>
          <p className="subtle">
            Update the program name, status, ownership, and research context.
          </p>
        </div>

        <div className="form-grid">
          <label className="field">
            <span>program_name</span>
            <input name="program_name" required defaultValue={program.program_name} />
          </label>
          <label className="field">
            <span>short_name</span>
            <input name="short_name" defaultValue={program.short_name} />
          </label>
          <label className="field">
            <span>status</span>
            <select name="status" defaultValue={program.status}>
              <option value="planning">Planning</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="completed">Completed</option>
              <option value="archived">Archived</option>
            </select>
          </label>
          <label className="field">
            <span>owner_name</span>
            <input name="owner_name" defaultValue={program.owner_name} />
          </label>
          <label className="field">
            <span>research_area</span>
            <input name="research_area" defaultValue={program.research_area} />
          </label>
          <label className="field">
            <span>researcher_names</span>
            <input name="researcher_names" defaultValue={program.researcher_names.join(", ")} />
          </label>
        </div>

        <label className="field">
          <span>program_description</span>
          <textarea name="program_description" defaultValue={program.program_description} />
        </label>
        <label className="field">
          <span>problem_statement</span>
          <textarea name="problem_statement" defaultValue={program.problem_statement} />
        </label>
        <label className="field">
          <span>initiating_context</span>
          <textarea name="initiating_context" defaultValue={program.initiating_context} />
        </label>
        <label className="field">
          <span>research_goal</span>
          <textarea name="research_goal" defaultValue={program.research_goal} />
        </label>
        <label className="field">
          <span>hypothesis</span>
          <textarea name="hypothesis" defaultValue={program.hypothesis} />
        </label>
        <label className="field">
          <span>current_focus</span>
          <textarea name="current_focus" defaultValue={program.current_focus} />
        </label>
        <label className="field">
          <span>tags</span>
          <input name="tags" defaultValue={program.tags.join(", ")} />
        </label>

        <div className="action-row">
          <Link className="btn btn--secondary" href={`/research-programs/${program.program_id}`}>
            Cancel
          </Link>
          <button className="btn btn--primary" type="submit">
            Save updates
          </button>
        </div>
      </form>
    </section>
  );
}

async function updateProgram(formData: FormData) {
  "use server";

  const programId = field(formData, "program_id");
  await updateResearchProgram(programId, {
    current_focus: field(formData, "current_focus"),
    hypothesis: field(formData, "hypothesis"),
    initiating_context: field(formData, "initiating_context"),
    owner_name: field(formData, "owner_name"),
    problem_statement: field(formData, "problem_statement"),
    program_description: field(formData, "program_description"),
    program_name: field(formData, "program_name"),
    research_area: field(formData, "research_area"),
    research_goal: field(formData, "research_goal"),
    researcher_names: commaList(formData, "researcher_names"),
    short_name: field(formData, "short_name"),
    status: field(formData, "status"),
    tags: commaList(formData, "tags"),
  });
  redirect(`/research-programs/${programId}`);
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
