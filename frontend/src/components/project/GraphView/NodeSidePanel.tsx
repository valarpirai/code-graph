import type { GraphNodeData } from "../../../api/types";
import { NODE_COLORS } from "./cytoscapeConfig";

interface Props {
  node: GraphNodeData;
  onClose: () => void;
  onBlastRadius: (nodeUri: string) => void;
  onExecutionFlow: (nodeUri: string) => void;
}

export default function NodeSidePanel({ node, onClose, onBlastRadius, onExecutionFlow }: Props) {
  const color = NODE_COLORS[node.node_type] ?? "#8b949e";

  return (
    <div className="absolute top-0 right-0 h-full w-72 card border-l border-t-0 border-r-0 border-b-0 rounded-none flex flex-col z-10 overflow-y-auto">
      <div className="flex items-center justify-between p-4 border-b border-surface-border">
        <div className="flex items-center gap-2 min-w-0">
          <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
          <span className="text-sm font-semibold truncate">{node.label}</span>
        </div>
        <button onClick={onClose} className="text-gray-600 hover:text-gray-200 transition-colors text-sm ml-2" aria-label="Close panel">✕</button>
      </div>
      <div className="flex flex-col gap-3 p-4 flex-1">
        <Property label="Type" value={node.node_type} />
        {node.file_path && <Property label="File" value={node.file_path} mono />}
        {node.line != null && <Property label="Location" value={`line ${node.line}${node.col != null ? `, col ${node.col}` : ""}`} />}
        {node.language && <Property label="Language" value={node.language} />}
        {node.cluster_id && <Property label="Cluster" value={node.cluster_id} />}
      </div>
      <div className="p-4 flex flex-col gap-2 border-t border-surface-border">
        <button onClick={() => onBlastRadius(node.id)} className="btn-ghost w-full text-left">Blast Radius</button>
        {node.node_type === "Function" && (
          <button onClick={() => onExecutionFlow(node.id)} className="btn-ghost w-full text-left">Execution Flow</button>
        )}
      </div>
    </div>
  );
}

function Property({ label, value, mono }: { label: string; value: string | number; mono?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-gray-500 uppercase tracking-widest">{label}</span>
      <span className={`text-sm text-gray-200 break-all ${mono ? "font-mono" : ""}`}>{String(value)}</span>
    </div>
  );
}
