import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createProjectFromGitHub } from "../../api/client";
import { projectKeys } from "../../hooks/useProject";

export default function GitHubInput() {
  const [url, setUrl] = useState("");
  const navigate = useNavigate();
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => createProjectFromGitHub({ github_url: url }),
    onSuccess: (project) => {
      qc.invalidateQueries({ queryKey: projectKeys.all });
      navigate(`/projects/${project.id}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    mutation.mutate();
  };

  const isValid =
    url.trim().startsWith("https://github.com/") ||
    url.trim().startsWith("http://github.com/");

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <label className="text-sm text-gray-400 uppercase tracking-widest">
        GitHub Repository
      </label>
      <div className="flex gap-2">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://github.com/owner/repo"
          className="flex-1 bg-surface border border-surface-border rounded px-3 py-2
                     text-sm text-gray-200 placeholder-gray-600
                     focus:outline-none focus:border-accent-blue transition-colors"
        />
        <button
          type="submit"
          disabled={!isValid || mutation.isPending}
          className="btn-primary min-w-[120px]"
        >
          {mutation.isPending ? "Indexing…" : "Index Repo"}
        </button>
      </div>
      {mutation.isError && (
        <p className="text-accent-red text-sm">
          {(mutation.error as Error).message}
        </p>
      )}
    </form>
  );
}
