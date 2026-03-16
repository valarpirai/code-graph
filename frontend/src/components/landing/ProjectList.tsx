import { useNavigate } from "react-router-dom";
import { useProjects, useDeleteProject } from "../../hooks/useProject";
import StatusBadge from "../shared/StatusBadge";
import type { Project } from "../../api/types";

export default function ProjectList() {
  const { data, isLoading, isError } = useProjects();
  const deleteMutation = useDeleteProject();
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div className="text-gray-500 text-sm text-center py-8 animate-pulse">
        Loading projects…
      </div>
    );
  }

  if (isError) {
    return (
      <p className="text-accent-red text-sm">Failed to load projects.</p>
    );
  }

  const projects = data ?? [];

  if (projects.length === 0) {
    return (
      <p className="text-gray-600 text-sm text-center py-8">
        No indexed projects yet.
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-2">
      {projects.map((p: Project) => (
        <li
          key={p.id}
          className="card flex items-center justify-between px-4 py-3
                     cursor-pointer hover:border-accent-blue transition-colors"
          onClick={() => navigate(`/projects/${p.id}`)}
        >
          <div className="flex flex-col gap-0.5 min-w-0">
            <span className="text-sm text-gray-200 font-semibold truncate">
              {p.name}
            </span>
            {p.source && (
              <span className="text-xs text-gray-600 truncate">
                {p.source}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 ml-4 shrink-0">
            <StatusBadge status={p.status} />
            <button
              aria-label="Delete project"
              onClick={(e) => {
                e.stopPropagation();
                if (confirm(`Delete "${p.name}"?`)) {
                  deleteMutation.mutate(p.id);
                }
              }}
              className="text-gray-600 hover:text-accent-red transition-colors text-xs"
            >
              ✕
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
