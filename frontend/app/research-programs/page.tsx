import Link from "next/link";

import { listResearchPrograms } from "../../lib/api";

export const dynamic = "force-dynamic";

type ResearchProgramsPageProps = {
  searchParams?: Record<string, string | string[] | undefined>;
};

export default async function ResearchProgramsPage({ searchParams = {} }: ResearchProgramsPageProps) {
  const q = first(searchParams.q) ?? "";
  const status = first(searchParams.status) ?? "";
  const researcherName = first(searchParams.researcher_name) ?? "";

  const [programs, allPrograms] = await Promise.all([
    listResearchPrograms({ q, researcher_name: researcherName, status }),
    listResearchPrograms({}),
  ]);

  const suggestions = buildSuggestions(allPrograms);
  const peopleSuggestions = buildPeopleSuggestions(allPrograms);

  return (
    <section className="page">
      <h1>Research Programs</h1>
      <div className="page-desc-row">
        <p className="subtle">
          Research programs organize hypotheses, datasets, experiments, runs, and evaluations into a single tracked lifecycle.
          Register a program before attaching experiments or runs.
        </p>
        <Link className="btn btn--primary" href="/research-programs/new">
          + New program
        </Link>
      </div>

      <form className="program-filters" action="/research-programs">
        <input
          className="filter-input"
          defaultValue={q}
          list="program-suggestions"
          name="q"
          placeholder="Search by name, goal, hypothesis, tags…"
        />
        <datalist id="program-suggestions">
          {suggestions.map((s) => <option key={s} value={s} />)}
        </datalist>

        <input
          className="filter-input"
          defaultValue={researcherName}
          list="people-suggestions"
          name="researcher_name"
          placeholder="Owner or researcher"
        />
        <datalist id="people-suggestions">
          {peopleSuggestions.map((s) => <option key={s} value={s} />)}
        </datalist>

        <select className="filter-input" defaultValue={status} name="status">
          <option value="">Any status</option>
          <option value="planning">Planning</option>
          <option value="active">Active</option>
          <option value="paused">Paused</option>
          <option value="completed">Completed</option>
          <option value="archived">Archived</option>
        </select>
        <button className="btn btn--secondary" type="submit">
          Filter
        </button>
      </form>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Program</th>
              <th>Status</th>
              <th>Tags</th>
              <th>Owner</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {programs.map((program) => (
              <tr className="program-row" key={program.program_id}>
                <td>
                  <Link className="program-name-link" href={`/research-programs/${program.program_id}`}>
                    {program.program_name}
                  </Link>
                </td>
                <td>
                  <span className={statusBadgeClass(program.status)}>
                    {program.status}
                  </span>
                </td>
                <td>
                  <div className="tag-row">
                    {program.tags.slice(0, 3).map((tag) => (
                      <span className="badge neutral" key={tag}>{tag}</span>
                    ))}
                    {program.tags.length > 3 && (
                      <span className="badge neutral">+{program.tags.length - 3}</span>
                    )}
                    {!program.tags.length && <span className="muted-row">—</span>}
                  </div>
                </td>
                <td>
                  <span>{program.owner_name || "Unassigned"}</span>
                  {program.researcher_names.length > 0 && (
                    <div className="muted-row">{program.researcher_names.join(", ")}</div>
                  )}
                </td>
                <td className="row-arrow">
                  <Link aria-hidden="true" href={`/research-programs/${program.program_id}`} tabIndex={-1}>
                    →
                  </Link>
                </td>
              </tr>
            ))}
            {!programs.length && (
              <tr>
                <td colSpan={5}>
                  <p className="subtle">No programs match the current filters.</p>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function buildSuggestions(programs: Awaited<ReturnType<typeof listResearchPrograms>>) {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const p of programs) {
    for (const val of [p.program_name, ...p.tags, p.research_area, p.current_focus]) {
      if (val && !seen.has(val)) { seen.add(val); out.push(val); }
    }
  }
  return out;
}

function buildPeopleSuggestions(programs: Awaited<ReturnType<typeof listResearchPrograms>>) {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const p of programs) {
    for (const name of [p.owner_name, ...p.researcher_names]) {
      if (name && !seen.has(name)) { seen.add(name); out.push(name); }
    }
  }
  return out;
}

function statusBadgeClass(status: string) {
  const map: Record<string, string> = {
    active: "badge status-active",
    planning: "badge status-planning",
    paused: "badge status-paused",
    completed: "badge status-completed",
    archived: "badge status-archived",
  };
  return map[status] ?? "badge neutral";
}

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}
