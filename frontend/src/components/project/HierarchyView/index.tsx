import { useState, useMemo } from "react";
import { useGraph } from "../../../hooks/useGraph";
import type { GraphNodeData, NodeType } from "../../../api/types";

interface TreeNode { data: GraphNodeData; children: TreeNode[]; }

const HIERARCHY_ORDER: NodeType[] = ["Module", "File", "Class", "Function", "Variable"];

function buildTree(nodes: GraphNodeData[], edges: Array<{ data: { source: string; target: string; relation: string } }>): TreeNode[] {
  const nodeMap = new Map<string, TreeNode>(nodes.map((n) => [n.id, { data: n, children: [] }]));
  const childSet = new Set<string>();
  edges.forEach(({ data: e }) => {
    if (e.relation === "contains") {
      const parent = nodeMap.get(e.source);
      const child = nodeMap.get(e.target);
      if (parent && child) { parent.children.push(child); childSet.add(e.target); }
    }
  });
  return nodes.filter((n) => !childSet.has(n.id)).map((n) => nodeMap.get(n.id)!)
    .sort((a, b) => HIERARCHY_ORDER.indexOf(a.data.node_type) - HIERARCHY_ORDER.indexOf(b.data.node_type));
}

interface Props { projectId: string; onNodeSelect?: (nodeId: string) => void; }

export default function HierarchyView({ projectId, onNodeSelect }: Props) {
  const { data, isLoading } = useGraph(projectId);
  const tree = useMemo(() => {
    if (!data) return [];
    return buildTree(data.nodes.map((n) => n.data), data.edges);
  }, [data]);

  if (isLoading) return <div className="p-6 text-gray-500 text-sm animate-pulse">Building hierarchy…</div>;

  return (
    <div className="flex-1 overflow-y-auto p-4 text-sm">
      {tree.map((root) => <TreeItem key={root.data.id} node={root} depth={0} onSelect={onNodeSelect} />)}
    </div>
  );
}

function TreeItem({ node, depth, onSelect }: { node: TreeNode; depth: number; onSelect?: (id: string) => void }) {
  const [open, setOpen] = useState(depth < 2);
  const hasChildren = node.children.length > 0;
  return (
    <div>
      <div className="flex items-center gap-1.5 py-0.5 rounded px-1 cursor-pointer hover:bg-surface-elevated transition-colors group"
        style={{ paddingLeft: `${depth * 14 + 4}px` }}
        onClick={() => { if (hasChildren) setOpen((v) => !v); onSelect?.(node.data.id); }}>
        <span className="text-gray-600 w-3 shrink-0 text-center select-none">{hasChildren ? (open ? "▾" : "▸") : "·"}</span>
        <NodeTypeIcon type={node.data.node_type} />
        <span className="text-gray-300 truncate group-hover:text-gray-100">{node.data.label}</span>
        <span className="text-gray-600 text-xs ml-auto shrink-0">{node.data.node_type}</span>
      </div>
      {open && hasChildren && node.children.map((child) => <TreeItem key={child.data.id} node={child} depth={depth + 1} onSelect={onSelect} />)}
    </div>
  );
}

function NodeTypeIcon({ type }: { type: NodeType }) {
  const icons: Record<NodeType, string> = { Module: "◈", File: "◻", Class: "◆", Function: "ƒ", Variable: "·", ExternalSymbol: "⬡" };
  return <span className="text-xs w-3 shrink-0 text-center select-none opacity-60">{icons[type] ?? "·"}</span>;
}
