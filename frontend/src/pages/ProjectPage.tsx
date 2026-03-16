import { useState } from "react";
import { useParams, Navigate } from "react-router-dom";
import { useProject } from "../hooks/useProject";
import ProjectHeader from "../components/project/ProjectHeader";
import IndexingStatus from "../components/project/IndexingStatus";
import GraphView from "../components/project/GraphView/index";
import WikiView from "../components/project/WikiView/index";
import QueryPanel from "../components/project/QueryPanel/index";
import { useIndexingStatus } from "../hooks/useIndexingStatus";

type Tab = "graph" | "wiki" | "query";

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  if (!id) return <Navigate to="/" replace />;
  return <ProjectPageInner id={id} />;
}

function ProjectPageInner({ id }: { id: string }) {
  const { data: project, isLoading, isError } = useProject(id);
  const [tab, setTab] = useState<Tab>("graph");
  const [linkedNodeId, setLinkedNodeId] = useState<string | null>(null);
  const isIndexing = project?.status === "indexing" || project?.status === "cloning";
  const wsState = useIndexingStatus(id, isIndexing ?? false);

  if (isLoading) return <div className="flex-1 flex items-center justify-center text-gray-500 animate-pulse">Loading project…</div>;
  if (isError || !project) return <div className="flex-1 flex items-center justify-center text-accent-red text-sm">Project not found.</div>;

  const TABS: { key: Tab; label: string }[] = [
    { key: "graph", label: "Graph" },
    { key: "wiki", label: "Wiki" },
    { key: "query", label: "Query" },
  ];

  return (
    <div className="h-full flex flex-col">
      <ProjectHeader project={project} />
      {isIndexing && <IndexingStatus message={wsState.message} progress={wsState.progress} />}
      <div className="flex gap-0 border-b border-surface-border px-4 bg-surface-elevated">
        {TABS.map(({ key, label }) => (
          <button key={key} onClick={() => setTab(key)} className={`px-5 py-3 text-sm font-medium ${tab === key ? "tab-active" : "tab-inactive"}`}>{label}</button>
        ))}
      </div>
      <div className="flex-1 flex overflow-hidden">
        {tab === "graph" && <GraphView projectId={id} linkedNodeId={linkedNodeId} onNodeSelect={setLinkedNodeId} />}
        {tab === "wiki" && <WikiView projectId={id} />}
        {tab === "query" && <QueryPanel projectId={id} />}
      </div>
    </div>
  );
}
