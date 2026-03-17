import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { listWikiFiles, getWikiContent, generateWiki, searchWiki } from "../../../api/client";
import WikiSidebar from "./WikiSidebar";

interface Props {
  projectId: string;
}

export default function WikiView({ projectId }: Props) {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);
  const [searchQ, setSearchQ] = useState("");

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

  const searchMutation = useMutation({
    mutationFn: () => searchWiki(projectId, searchQ),
  });

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Sidebar */}
      <aside className="w-52 shrink-0 border-r border-surface-border overflow-y-auto flex flex-col">
        <div className="p-3 border-b border-surface-border flex flex-col gap-2">
          <button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="btn-primary w-full text-xs py-1.5"
          >
            {generateMutation.isPending ? "Generating…" : "Generate Wiki"}
          </button>
          {generateMutation.isError && (
            <p className="text-accent-red text-xs">
              {(generateMutation.error as Error).message}
            </p>
          )}
        </div>
        <WikiSidebar
          files={filesQuery.data?.files ?? []}
          selected={selected}
          onSelect={(p) => { setSelected(p); searchMutation.reset(); }}
        />
      </aside>

      {/* Content */}
      <main className="flex-1 overflow-y-auto p-8 flex flex-col gap-6">
        {/* Semantic Search */}
        <div className="card p-4 flex flex-col gap-3">
          <span className="text-xs text-gray-500 uppercase tracking-widest">
            Ask the Wiki
          </span>
          <div className="flex gap-2">
            <input
              type="text"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && searchQ.trim() && searchMutation.mutate()}
              placeholder="Ask anything about this codebase…"
              className="flex-1 bg-surface border border-surface-border rounded px-3 py-2
                         text-sm text-gray-200 focus:outline-none focus:border-accent-blue transition-colors"
            />
            <button
              onClick={() => searchMutation.mutate()}
              disabled={searchMutation.isPending || !searchQ.trim()}
              className="btn-primary text-sm px-4"
            >
              {searchMutation.isPending ? "…" : "Ask"}
            </button>
          </div>
          {searchMutation.isError && (
            <p className="text-accent-red text-xs">
              {(searchMutation.error as Error).message}
            </p>
          )}
          {searchMutation.data && (
            <div className="flex flex-col gap-2">
              <article className="prose prose-invert prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {searchMutation.data.answer}
                </ReactMarkdown>
              </article>
              {searchMutation.data.sources.length > 0 && (
                <p className="text-xs text-gray-500">
                  Sources:{" "}
                  {searchMutation.data.sources.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => { setSelected(s); searchMutation.reset(); }}
                      className="text-accent-blue hover:underline mr-2"
                    >
                      {s}
                    </button>
                  ))}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Selected page content */}
        {!selected && !searchMutation.data && (
          <p className="text-gray-600 text-sm">
            Select a wiki page from the sidebar, or ask a question above.
          </p>
        )}
        {selected && contentQuery.isLoading && (
          <p className="text-gray-500 text-sm animate-pulse">Loading…</p>
        )}
        {selected && contentQuery.data && (
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
