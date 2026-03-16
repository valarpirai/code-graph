import { useNavigate } from "react-router-dom";
import { useReindexProject } from "../../hooks/useProject";
import StatusBadge from "../shared/StatusBadge";
import type { Project } from "../../api/types";

interface Props {
  project: Project;
}

export default function ProjectHeader({ project }: Props) {
  const navigate = useNavigate();
  const reindex = useReindexProject();

  return (
    <header className="flex items-center gap-3 px-4 py-2.5 border-b border-surface-border bg-surface-elevated shrink-0">
      {/* Back */}
      <button
        onClick={() => navigate("/")}
        className="text-gray-500 hover:text-gray-200 transition-colors text-sm mr-1"
        aria-label="Back to projects"
      >
        ←
      </button>

      {/* Project name */}
      <h1 className="text-sm font-semibold text-gray-200 truncate flex-1 min-w-0">
        {project.name}
      </h1>

      {/* Language tags */}
      {project.languages.slice(0, 4).map((lang) => (
        <span
          key={lang}
          className="text-xs text-gray-500 border border-surface-border rounded px-1.5 py-0.5"
        >
          {lang}
        </span>
      ))}

      {/* Node/edge counts */}
      {project.node_count != null && (
        <span className="text-xs text-gray-600">
          {project.node_count.toLocaleString()} nodes
        </span>
      )}

      {/* Status */}
      <StatusBadge status={project.status} />

      {/* Re-index */}
      <button
        onClick={() => reindex.mutate(project.id)}
        disabled={
          reindex.isPending ||
          project.status === "indexing" ||
          project.status === "cloning"
        }
        className="btn-ghost text-xs px-3 py-1.5"
      >
        {reindex.isPending ? "…" : "Re-index"}
      </button>
    </header>
  );
}
