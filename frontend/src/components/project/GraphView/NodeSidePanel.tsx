import type { GraphNodeData, GraphResponse } from "../../../api/types";
import { NODE_COLORS } from "./cytoscapeConfig";

interface Props {
  node: GraphNodeData;
  graphData: GraphResponse;
  onClose: () => void;
  onBlastRadius: (nodeUri: string) => void;
  onExecutionFlow: (nodeUri: string) => void;
}

const PARENT_RELATIONS = new Set(["defines", "hasMethod", "containsFile", "containsClass"]);
const MAX_ANCESTRY_LEVELS = 5;
const MAX_CALL_LEVELS = 4;

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

interface CallNode {
  node: GraphNodeData;
  children: CallNode[];
}

function buildCallTree(nodeId: string, graphData: GraphResponse, depth: number, visited: Set<string>): CallNode[] {
  if (depth === 0) return [];
  const nodeMap = new Map(graphData.nodes.map((n) => [n.data.id, n.data]));
  const callees = graphData.edges
    .filter((e) => e.data.source === nodeId && e.data.relation === "calls")
    .map((e) => nodeMap.get(e.data.target))
    .filter((n): n is GraphNodeData => n != null && !visited.has(n.id));

  return callees.slice(0, 8).map((callee) => {
    const nextVisited = new Set(visited).add(callee.id);
    return { node: callee, children: buildCallTree(callee.id, graphData, depth - 1, nextVisited) };
  });
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

export default function NodeSidePanel({ node, graphData, onClose, onBlastRadius, onExecutionFlow }: Props) {
  const color = NODE_COLORS[node.node_type] ?? "#8b949e";
  const ancestors = computeAncestry(node.id, graphData);
  const moduleStats = node.node_type === "Module" ? computeModuleStats(node.id, graphData) : null;
  const callTree = node.node_type === "Function"
    ? buildCallTree(node.id, graphData, MAX_CALL_LEVELS, new Set([node.id]))
    : [];

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
          {node.value != null && <Property label="Value" value={node.value} mono />}
          {node.is_test && <Property label="Kind" value="test file" />}
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
                    <div className="flex flex-col min-w-0 pb-2">
                      <span className="text-xs text-gray-400 truncate">{ancestor.label}</span>
                      <span className="text-xs text-gray-600">{ancestor.node_type}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </Section>
        )}
        {/* Call tree */}
        {callTree.length > 0 && (
          <Section title="Calls (up to 4 levels)">
            <CallTreeNodes nodes={callTree} indent={0} />
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

function CallTreeNodes({ nodes, indent }: { nodes: CallNode[]; indent: number }) {
  return (
    <>
      {nodes.map((item) => {
        const c = NODE_COLORS[item.node.node_type] ?? "#8b949e";
        return (
          <div key={item.node.id}>
            <div className="flex items-center gap-1.5 py-0.5" style={{ paddingLeft: indent * 12 }}>
              {indent > 0 && <span className="text-gray-600 text-xs shrink-0">↳</span>}
              <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: c }} />
              <span className="text-xs text-gray-300 truncate">{item.node.label}</span>
            </div>
            {item.children.length > 0 && (
              <CallTreeNodes nodes={item.children} indent={indent + 1} />
            )}
          </div>
        );
      })}
    </>
  );
}
