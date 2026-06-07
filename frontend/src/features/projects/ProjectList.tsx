import { Search } from "lucide-react";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { StatusBadge } from "../../components/StatusBadge";
import { WorkloadView } from "./WorkloadView";

const projectUuidPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function ProjectList() {
  const navigate = useNavigate();
  const [projectLookup, setProjectLookup] = useState("");
  const [validationError, setValidationError] = useState("");

  function openProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const projectUuid = projectLookup.trim().toLowerCase();

    if (!projectUuidPattern.test(projectUuid)) {
      setValidationError("Enter a valid project UUID before opening a project.");
      return;
    }

    setValidationError("");
    navigate(`/projects/${encodeURIComponent(projectUuid)}`);
  }

  return (
    <div className="page-stack project-page">
      <section className="workspace-header" aria-labelledby="projects-title">
        <div>
          <p className="section-kicker">Engineering project workspaces</p>
          <h1 id="projects-title">Projects</h1>
        </div>
        <StatusBadge tone="neutral">Direct Open</StatusBadge>
      </section>

      <section className="filter-panel" aria-label="Open project">
        <form className="search-form" onSubmit={openProject}>
          <label className="field-control field-control-wide">
            <span>Project UUID</span>
            <input
              aria-describedby={validationError ? "project-uuid-error" : undefined}
              aria-invalid={validationError ? "true" : undefined}
              aria-label="Project UUID"
              value={projectLookup}
              onChange={(event) => {
                setProjectLookup(event.target.value);
                if (validationError) {
                  setValidationError("");
                }
              }}
              placeholder="550e8400-e29b-41d4-a716-446655440000"
            />
          </label>
          <button className="button button-primary" type="submit">
            <Search aria-hidden="true" size={16} />
            Open
          </button>
        </form>
        {validationError && (
          <div className="admin-alert" id="project-uuid-error" role="alert">
            <strong>Project UUID required</strong>
            <span>{validationError}</span>
          </div>
        )}
      </section>

      <WorkloadView />
    </div>
  );
}
