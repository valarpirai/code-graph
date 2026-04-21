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
  const [reindexOpen, setReindexOpen] = useState(false);
  // Selected languages for next reindex — initialise from stored project setting
  const [selectedLangs, setSelectedLangs] = useState<Set<string>>(
    () => new Set(project.include_languages ?? [])
  );

  const github = isGitHub(project);
  const isActive = project.status === "indexing" || project.status === "cloning";

  const { data: branches } = useBranches(project.id, github && branchOpen);

  const allLangs = project.languages;
  const filterActive = selectedLangs.size > 0 && selectedLangs.size < allLangs.length;

  const toggleLang = (lang: string) => {
    setSelectedLangs((prev) => {
      const next = new Set(prev);
      next.has(lang) ? next.delete(lang) : next.add(lang);
      return next;
    });
  };

  const handleReindex = () => {
    setReindexOpen(false);
    reindex.mutate({
      id: project.id,
      includeLanguages: selectedLangs.size > 0 && selectedLangs.size < allLangs.length
        ? Array.from(selectedLangs)
        : [],
    });
  };

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

      {/* Re-index with language filter */}
      <div className="relative">
        <div className="flex items-center">
          <button
            onClick={handleReindex}
            disabled={reindex.isPending || isActive}
            className="btn-ghost text-xs px-3 py-1.5 rounded-r-none border-r border-surface-border"
          >
            {reindex.isPending ? "…" : filterActive ? `Re-index (${selectedLangs.size})` : "Re-index"}
          </button>
          {allLangs.length > 1 && (
            <button
              onClick={() => setReindexOpen((v) => !v)}
              disabled={isActive}
              className="btn-ghost text-xs px-2 py-1.5 rounded-l-none"
              title="Filter languages for re-index"
            >
              ▾
            </button>
          )}
        </div>

        {reindexOpen && (
          <div className="absolute right-0 top-full mt-1 z-20 bg-surface-elevated border border-surface-border rounded shadow-lg min-w-44 p-2">
            <div className="text-[10px] text-gray-500 uppercase tracking-widest mb-2 px-1">
              Index languages
            </div>
            {allLangs.map((lang) => (
              <label key={lang} className="flex items-center gap-2 px-1 py-1 cursor-pointer hover:bg-surface rounded">
                <input
                  type="checkbox"
                  checked={selectedLangs.size === 0 || selectedLangs.has(lang)}
                  onChange={() => {
                    // When all are selected and user unchecks one, init the set with all except that one
                    if (selectedLangs.size === 0) {
                      setSelectedLangs(new Set(allLangs.filter((l) => l !== lang)));
                    } else {
                      toggleLang(lang);
                    }
                  }}
                  className="accent-accent-blue"
                />
                <span className="text-xs text-gray-300">{lang}</span>
              </label>
            ))}
            <div className="mt-2 flex gap-1">
              <button
                onClick={() => setSelectedLangs(new Set())}
                className="flex-1 text-[10px] text-gray-500 hover:text-gray-300 py-1"
              >
                All
              </button>
              <button
                onClick={handleReindex}
                className="flex-1 btn-ghost text-[10px] py-1"
              >
                Apply & Re-index
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
