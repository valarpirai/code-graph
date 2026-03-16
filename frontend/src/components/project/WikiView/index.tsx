import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { listWikiFiles, getWikiContent, generateWiki } from "../../../api/client";
import WikiSidebar from "./WikiSidebar";

interface Props {
  projectId: string;
}

export default function WikiView({ projectId }: Props) {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);

  const filesQuery = useQuery({
    queryKey: ["wiki-files", projectId],
    queryFn: () => listWikiFiles(projectId),
  });

  const contentQuery = useQuery({
    queryKey: ["wiki-content", projectId, selected],
    queryFn: () => getWikiContent(projectId, selected!),
    enabled: selected != null,
  });

  const generateMutation = useMutation({
    mutationFn: () => generateWiki(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["wiki-files", projectId] });
    },
  });

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Sidebar */}
      <aside className="w-52 shrink-0 border-r border-surface-border overflow-y-auto flex flex-col">
        <div className="p-3 border-b border-surface-border">
          <button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="btn-primary w-full text-xs py-1.5"
          >
            {generateMutation.isPending ? "Generating…" : "Generate Wiki"}
          </button>
          {generateMutation.isError && (
            <p className="text-accent-red text-xs mt-1">
              {(generateMutation.error as Error).message}
            </p>
          )}
        </div>
        <WikiSidebar
          files={filesQuery.data?.files ?? []}
          selected={selected}
          onSelect={setSelected}
        />
      </aside>

      {/* Content */}
      <main className="flex-1 overflow-y-auto p-8">
        {!selected && (
          <p className="text-gray-600 text-sm">
            Select a wiki page from the sidebar.
          </p>
        )}
        {contentQuery.isLoading && (
          <p className="text-gray-500 text-sm animate-pulse">Loading…</p>
        )}
        {contentQuery.data && (
          <article className="prose prose-invert prose-sm max-w-3xl prose-pre:bg-surface prose-pre:border prose-pre:border-surface-border">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {contentQuery.data.content}
            </ReactMarkdown>
          </article>
        )}
      </main>
    </div>
  );
}
