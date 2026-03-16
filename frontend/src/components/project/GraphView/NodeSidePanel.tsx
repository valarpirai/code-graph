import type { GraphNodeData, GraphResponse } from "../../../api/types";
import { NODE_COLORS } from "./cytoscapeConfig";

interface Props {
  node: GraphNodeData;
  graphData: GraphResponse;
  onClose: () => void;
  onBlastRadius: (nodeUri: string) => void;
  onExecutionFlow: (nodeUri: string) => void;
  onSelectNode: (nodeId: string) => void;
}

const PARENT_RELATIONS = new Set(["defines", "hasMethod", "hasField", "containsFile", "containsClass"]);
const MAX_ANCESTRY_LEVELS = 5;

function computeAncestry(nodeId: string, graphData: GraphResponse): GraphNodeData[] {
  const nodeMap = new Map(graphData.nodes.map((n) => [n.data.id, n.data]));
  const ancestors: GraphNodeData[] = [];
  let currentId = nodeId;

  for (let i = 0; i < MAX_ANCESTRY_LEVELS; i++) {
    const parentEdge = graphData.edges.find(
      (e) => e.data.target === currentId && PARENT_RELATIONS.has(e.data.relation)
    );
    if (!parentEdge) break;
    const parent = nodeMap.get(parentEdge.data.source);
    if (!parent || parent.id === nodeId) break;
    ancestors.push(parent);
    currentId = parent.id;
  }
  return ancestors;
}

function computeCalledFrom(nodeId: string, graphData: GraphResponse): GraphNodeData[] {
  const nodeMap = new Map(graphData.nodes.map((n) => [n.data.id, n.data]));
  return graphData.edges
    .filter((e) => e.data.target === nodeId && e.data.relation === "calls")
    .map((e) => nodeMap.get(e.data.source))
    .filter((n): n is GraphNodeData => n != null);
}

function callerLabel(caller: GraphNodeData): string {
  const qname = caller.qualified_name ?? caller.label;
  const parts = qname.split(".");
  const short = parts.length >= 2 ? parts.slice(-2).join(".") : qname;
  return caller.line != null ? `${short}:L${caller.line}` : short;
}

function computeModuleStats(nodeId: string, graphData: GraphResponse) {
  const classCount = graphData.edges.filter(
    (e) => e.data.source === nodeId && e.data.relation === "containsClass"
  ).length;
  const fileCount = graphData.edges.filter(
    (e) => e.data.source === nodeId && e.data.relation === "containsFile"
  ).length;
  return { classCount, fileCount };
}

export default function NodeSidePanel({ node, graphData, onClose, onBlastRadius, onExecutionFlow, onSelectNode }: Props) {
  const color = NODE_COLORS[node.node_type] ?? "#8b949e";
  const ancestors = computeAncestry(node.id, graphData);
  const moduleStats = node.node_type === "Module" ? computeModuleStats(node.id, graphData) : null;
  const calledFrom = node.node_type === "Function" ? computeCalledFrom(node.id, graphData) : [];

  return (
    <div className="absolute top-0 right-0 h-full w-80 card border-l border-t-0 border-r-0 border-b-0 rounded-none flex flex-col z-10 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-surface-border shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
          <span className="text-sm font-semibold truncate">{node.label}</span>
        </div>
        <button
          onClick={onClose}
          className="text-gray-600 hover:text-gray-200 transition-colors text-sm ml-2"
          aria-label="Close panel"
        >
          ✕
        </button>
      </div>

      <div className="flex flex-col gap-5 p-4 flex-1">
        {/* Properties */}
        <Section title="Properties">
          <Property label="Type" value={node.class_kind ?? node.node_type} />
          {node.qualified_name && node.qualified_name !== node.label && (
            <Property label="Qualified Name" value={node.qualified_name} mono />
          )}
          {node.file_path && <Property label="File" value={node.file_path} mono />}
          {node.line != null && <Property label="Line" value={node.line} />}
          {node.language && <Property label="Language" value={node.language} />}
          {node.visibility && <Property label="Visibility" value={node.visibility} />}
          {node.is_exported != null && (
            <Property label="Exported" value={node.is_exported ? "yes" : "no"} />
          )}
          {node.entry_point_score != null && (
            <Property label="Entry Point Score" value={node.entry_point_score} />
          )}
          {node.framework_role && <Property label="Framework Role" value={node.framework_role} />}
          {node.var_kind && <Property label="Variable Kind" value={node.var_kind} />}
          {node.value != null && <Property label="Value" value={node.value} mono />}
          {node.is_test && <Property label="Kind" value="test file" />}
          {node.line_count != null && <Property label="Lines" value={node.line_count} />}
          {node.file_size != null && <Property label="Size" value={`${(node.file_size / 1024).toFixed(1)} KB`} />}
          {node.cluster_id && <Property label="Cluster" value={node.cluster_id} />}
          {moduleStats && <Property label="Classes" value={moduleStats.classCount} />}
          {moduleStats && <Property label="Files" value={moduleStats.fileCount} />}
        </Section>

        {/* Ancestry */}
        {ancestors.length > 0 && (
          <Section title={`Ancestry (${ancestors.length} level${ancestors.length > 1 ? "s" : ""})`}>
            <div className="flex flex-col gap-1">
              {ancestors.map((ancestor, i) => {
                const aColor = NODE_COLORS[ancestor.node_type] ?? "#8b949e";
                return (
                  <div key={ancestor.id} className="flex items-start gap-2">
                    <div className="flex flex-col items-center shrink-0 pt-1.5">
                      <span
                        className="w-2 h-2 rounded-full shrink-0"
                        style={{ backgroundColor: aColor }}
                      />
                      {i < ancestors.length - 1 && (
                        <span className="w-px flex-1 bg-surface-border mt-1" style={{ minHeight: 12 }} />
                      )}
                    </div>
                    <button
                      className="flex flex-col min-w-0 pb-2 text-left hover:opacity-80 transition-opacity cursor-pointer"
                      onClick={() => onSelectNode(ancestor.id)}
                    >
                      <span className="text-xs text-gray-400 truncate underline-offset-2 hover:underline">{ancestor.label}</span>
                      <span className="text-xs text-gray-600">{ancestor.node_type}</span>
                    </button>
                  </div>
                );
              })}
            </div>
          </Section>
        )}
        {/* Called From */}
        {calledFrom.length > 0 && (
          <Section title={`Called From (${calledFrom.length})`}>
            <div className="flex flex-col gap-1">
              {calledFrom.map((caller) => (
                <button
                  key={caller.id}
                  className="text-left text-xs text-gray-300 font-mono hover:text-white hover:underline underline-offset-2 transition-colors truncate"
                  onClick={() => onSelectNode(caller.id)}
                  title={[
                    caller.qualified_name ?? caller.label,
                    caller.file_path ? `File: ${caller.file_path}` : null,
                    caller.visibility ? `Visibility: ${caller.visibility}` : null,
                  ].filter(Boolean).join("\n")}
                >
                  {callerLabel(caller)}
                </button>
              ))}
            </div>
          </Section>
        )}
      </div>

      {/* Actions */}
      <div className="p-4 flex flex-col gap-2 border-t border-surface-border shrink-0">
        <button onClick={() => onBlastRadius(node.id)} className="btn-ghost w-full text-left text-xs">
          Blast Radius
        </button>
        {node.node_type === "Function" && (
          <button onClick={() => onExecutionFlow(node.id)} className="btn-ghost w-full text-left text-xs">
            Execution Flow
          </button>
        )}
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs text-gray-500 uppercase tracking-widest">{title}</span>
      <div className="flex flex-col gap-2">{children}</div>
    </div>
  );
}

function Property({ label, value, mono }: { label: string; value: string | number | boolean; mono?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-gray-600 uppercase tracking-widest">{label}</span>
      <span className={`text-sm text-gray-200 break-all ${mono ? "font-mono text-xs" : ""}`}>
        {String(value)}
      </span>
    </div>
  );
}

