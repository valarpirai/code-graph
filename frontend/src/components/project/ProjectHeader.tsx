import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useReindexProject, usePullProject, useSwitchBranch, useBranches } from "../../hooks/useProject";
import StatusBadge from "../shared/StatusBadge";
import type { Project } from "../../api/types";

interface Props {
  project: Project;
}

function isGitHub(project: Project) {
  return project.source.startsWith("https://github.com") || project.source.startsWith("http://github.com");
}

export default function ProjectHeader({ project }: Props) {
  const navigate = useNavigate();
  const reindex = useReindexProject();
  const pull = usePullProject();
  const switchBranch = useSwitchBranch();
  const [branchOpen, setBranchOpen] = useState(false);

  const github = isGitHub(project);
  const isActive = project.status === "indexing" || project.status === "cloning";

  const { data: branches } = useBranches(project.id, github && branchOpen);

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

      {/* Stale indicator */}
      {project.is_stale && (
        <span className="text-xs text-yellow-400 border border-yellow-600 rounded px-1.5 py-0.5">
          Outdated — re-index to apply changes
        </span>
      )}

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

      {/* Branch selector (GitHub only) */}
      {github && (
        <div className="relative">
          <button
            onClick={() => setBranchOpen((v) => !v)}
            disabled={isActive}
            className="btn-ghost text-xs px-3 py-1.5 flex items-center gap-1"
          >
            <span>{project.branch ?? "default"}</span>
            <span className="text-gray-500">▾</span>
          </button>

          {branchOpen && (
            <div className="absolute right-0 top-full mt-1 z-20 bg-surface-elevated border border-surface-border rounded shadow-lg min-w-36 max-h-60 overflow-y-auto">
              {!branches ? (
                <div className="px-3 py-2 text-xs text-gray-500">Loading…</div>
              ) : branches.length === 0 ? (
                <div className="px-3 py-2 text-xs text-gray-500">No branches found</div>
              ) : (
                branches.map((b) => (
                  <button
                    key={b}
                    onClick={() => {
                      setBranchOpen(false);
                      if (b !== project.branch) {
                        switchBranch.mutate({ id: project.id, branch: b });
                      }
                    }}
                    className={`w-full text-left px-3 py-1.5 text-xs hover:bg-surface transition-colors ${
                      b === project.branch ? "text-accent-blue" : "text-gray-300"
                    }`}
                  >
                    {b}
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      )}

      {/* Pull latest (GitHub only) */}
      {github && (
        <button
          onClick={() => pull.mutate(project.id)}
          disabled={pull.isPending || isActive}
          className="btn-ghost text-xs px-3 py-1.5"
        >
          {pull.isPending ? "…" : "Pull"}
        </button>
      )}

      {/* Re-index */}
      <button
        onClick={() => reindex.mutate(project.id)}
        disabled={reindex.isPending || isActive}
        className="btn-ghost text-xs px-3 py-1.5"
      >
        {reindex.isPending ? "…" : "Re-index"}
      </button>
    </header>
  );
}
