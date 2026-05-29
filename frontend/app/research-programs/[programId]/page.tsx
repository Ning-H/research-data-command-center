import Link from "next/link";
import { redirect } from "next/navigation";

import { appendResearchProgramNote, deleteResearchProgramNote, getResearchProgram } from "../../../lib/api";
import ProgramEditableFields from "./ProgramEditableFields";

export const dynamic = "force-dynamic";

type ResearchProgramDetailPageProps = {
  params: {
    programId: string;
  };
};

export default async function ResearchProgramDetailPage({ params }: ResearchProgramDetailPageProps) {
  const program = await getResearchProgram(params.programId);
  const linkedDatasets = program.linked_dataset_ids ?? program.linked_datasets ?? [];
  const linkedExperiments = program.linked_experiment_ids ?? [];
  const linkedRuns = program.linked_run_ids ?? [];

  return (
    <section className="page program-detail-page">
      <nav className="breadcrumb">
        <Link href="/research-programs">Research Programs</Link>
        <span className="breadcrumb-sep" aria-hidden="true">/</span>
        <span>{program.program_name}</span>
      </nav>

      <div className="program-doc">
        <div className="doc-main">
          {/* Editable fields: name, tags, metadata strip, activity strip, status, then content fields */}
          <ProgramEditableFields
            initialProgram={program}
            linkedDatasets={linkedDatasets.length}
            linkedExperiments={linkedExperiments.length}
            linkedRuns={linkedRuns.length}
            owner={program.owner_name || ""}
            team={program.researcher_names}
            researchArea={program.research_area || ""}
            programId={program.program_id}
            createdAt={program.created_at}
            updatedAt={program.updated_at}
          />

          {/* Notes — conversation thread, server-rendered */}
          <div className="doc-section">
            <span className="doc-label">Notes</span>
            {program.notes.length > 0 ? (
              <div className="chat-thread">
                {program.notes.map((note) => (
                  <div className="chat-message" key={note.note_id}>
                    <div className="chat-avatar" aria-hidden="true">
                      {(note.author_name || "?")[0].toUpperCase()}
                    </div>
                    <div className="chat-bubble">
                      <div className="chat-meta">
                        <span className="chat-author">{note.author_name || "Anonymous"}</span>
                        <span className="chat-time">{note.created_at}</span>
                        <form action={deleteNote} className="chat-delete-form">
                          <input name="program_id" type="hidden" value={program.program_id} />
                          <input name="note_id" type="hidden" value={note.note_id} />
                          <button className="chat-delete-btn" title="Delete note" type="submit">
                            ×
                          </button>
                        </form>
                      </div>
                      <p className="chat-body">{note.body}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="doc-text empty">No notes yet. Add the first one below.</p>
            )}
          </div>

          {/* Add note — at the bottom */}
          <div className="doc-section">
            <form action={appendProgramNote} className="chat-compose">
              <input name="program_id" type="hidden" value={program.program_id} />
              <div className="chat-avatar" aria-hidden="true">
                {(program.owner_name || "?")[0].toUpperCase()}
              </div>
              <div className="chat-compose-body">
                <textarea
                  className="chat-compose-input"
                  name="body"
                  placeholder="Add a note…"
                  required
                />
                <div className="chat-compose-footer">
                  <input
                    className="chat-compose-author"
                    defaultValue={program.owner_name || ""}
                    name="author_name"
                    placeholder="Your name"
                  />
                  <button className="btn btn--primary" type="submit">
                    Post note
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>

      </div>
    </section>
  );
}

async function appendProgramNote(formData: FormData) {
  "use server";

  const programId = String(formData.get("program_id") ?? "").trim();
  await appendResearchProgramNote(programId, {
    body: String(formData.get("body") ?? "").trim(),
    author_name: String(formData.get("author_name") ?? "").trim() || undefined,
  });
  redirect(`/research-programs/${programId}`);
}

async function deleteNote(formData: FormData) {
  "use server";

  const programId = String(formData.get("program_id") ?? "").trim();
  const noteId = Number(formData.get("note_id"));
  await deleteResearchProgramNote(programId, noteId);
  redirect(`/research-programs/${programId}`);
}
